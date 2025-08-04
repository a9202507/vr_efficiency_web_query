# app.py - VR實測效率查詢系統
from flask import Flask, request, jsonify, render_template, send_file, session, abort, redirect, url_for
from flask_socketio import SocketIO, emit
import sqlite3
import pandas as pd
import json
import os
import shutil
from datetime import datetime
from functools import wraps
import io
import csv

app = Flask(__name__)
app.secret_key = 'vr-efficiency-system-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

ADMIN_PASSWORD = "admin123"  # 生產環境請更改此密碼

# 權限裝飾器
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return jsonify({'error': '需要管理者權限'}), 403
        return f(*args, **kwargs)
    return decorated_function

# 資料庫初始化
def init_db():
    conn = sqlite3.connect('data/vr_efficiency.sqlite')
    cursor = conn.cursor()
    
    # information_table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS information_table (
            user_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT NOT NULL,
            pcb_name TEXT NOT NULL,
            powerstage_name TEXT NOT NULL,
            phase_count INTEGER NOT NULL,
            frequency INTEGER NOT NULL,
            inductor_value INTEGER NOT NULL,
            tlvr INTEGER,
            imax INTEGER NOT NULL,
            upload_date TEXT DEFAULT CURRENT_TIMESTAMP,
            notice TEXT
        )
    ''')
    
    # efficiency_table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS efficiency_table (
            series_number INTEGER PRIMARY KEY AUTOINCREMENT,
            istep REAL NOT NULL,
            vin REAL NOT NULL,
            iin REAL NOT NULL,
            vout REAL NOT NULL,
            remote_vout_sense REAL NOT NULL,
            iout REAL NOT NULL,
            efficiency REAL NOT NULL,
            efficiency_remote REAL NOT NULL,
            user_id INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES information_table(user_ID)
        )
    ''')
    
    # 建立索引以提升查詢效能
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_powerstage ON information_table(powerstage_name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_phase ON information_table(phase_count)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON efficiency_table(user_id)')
    
    conn.commit()
    conn.close()

# 動態取得資料表結構
def get_table_columns(table_name):
    conn = sqlite3.connect('data/vr_efficiency.sqlite')
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    conn.close()
    return columns

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin/login', methods=['POST'])
def admin_login():
    password = request.json.get('password')
    if password == ADMIN_PASSWORD:
        session['is_admin'] = True
        return jsonify({'success': True})
    else:
        return jsonify({'error': '密碼錯誤'}), 401

@app.route('/admin/logout', methods=['POST'])
def admin_logout():
    session.pop('is_admin', None)
    return jsonify({'success': True})

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': '沒有檔案'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '請選擇檔案'}), 400

    # 檢查檔案類型
    if file.filename.endswith('.csv'):
        file_content = file.read().decode('utf-8')
        df = pd.read_csv(io.StringIO(file_content))
    elif file.filename.endswith(('.xlsx', '.xls')):
        df = pd.read_excel(file)
    else:
        return jsonify({'error': '不支援的檔案格式，請上傳 CSV 或 Excel 檔案'}), 400

    # 獲取 information_table 資料
    info_data = {
        'user_name': request.form.get('user_name'),
        'pcb_name': request.form.get('pcb_name'),
        'powerstage_name': request.form.get('powerstage_name'),
        'phase_count': int(request.form.get('phase_count')),
        'frequency': int(request.form.get('frequency')),
        'inductor_value': int(request.form.get('inductor_value')),
        'tlvr': int(request.form.get('tlvr')) if request.form.get('tlvr') else None,
        'imax': int(request.form.get('imax')),
        'upload_date': datetime.now().isoformat(),
        'notice': request.form.get('notice', '')
    }

    try:
        # 驗證必要欄位
        required_columns = ['Istep', 'Vin', 'Iin', 'Vout', 'remote Vout sense', 'Iout', 'Efficiency', 'Efficiency_remote']
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            return jsonify({'error': f'缺少必要欄位: {", ".join(missing_columns)}'}), 400

        conn = sqlite3.connect('data/vr_efficiency.sqlite')
        cursor = conn.cursor()

        # 插入 information_table
        cursor.execute('''
            INSERT INTO information_table 
            (user_name, pcb_name, powerstage_name, phase_count, frequency, 
             inductor_value, tlvr, imax, upload_date, notice)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (info_data['user_name'], info_data['pcb_name'], info_data['powerstage_name'],
              info_data['phase_count'], info_data['frequency'], info_data['inductor_value'],
              info_data['tlvr'], info_data['imax'], info_data['upload_date'], info_data['notice']))

        user_id = cursor.lastrowid

        # 插入 efficiency_table
        for _, row in df.iterrows():
            cursor.execute('''
                INSERT INTO efficiency_table 
                (istep, vin, iin, vout, remote_vout_sense, iout, efficiency, efficiency_remote, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (row['Istep'], row['Vin'], row['Iin'], row['Vout'],
                  row['remote Vout sense'], row['Iout'], row['Efficiency'], 
                  row['Efficiency_remote'], user_id))

        conn.commit()
        conn.close()

        # 即時通知所有客戶端
        socketio.emit('new_data_uploaded', {
            'user_id': user_id,
            'pcb_name': info_data['pcb_name'],
            'user_name': info_data['user_name'],
            'powerstage_name': info_data['powerstage_name']
        })

        return jsonify({'success': True, 'user_id': user_id})

    except Exception as e:
        return jsonify({'error': f'處理檔案時發生錯誤: {str(e)}'}), 500

@app.route('/api/search')
def search_records():
    # 多條件搜尋
    powerstage_name = request.args.get('powerstage_name')
    phase_count = request.args.get('phase_count')
    frequency = request.args.get('frequency')
    inductor_value = request.args.get('inductor_value')
    pcb_name = request.args.get('pcb_name')
    
    conn = sqlite3.connect('data/vr_efficiency.sqlite')
    conn.row_factory = sqlite3.Row
    
    query = "SELECT * FROM information_table WHERE 1=1"
    params = []
    
    if powerstage_name:
        query += " AND powerstage_name LIKE ?"
        params.append(f"%{powerstage_name}%")
    if phase_count:
        query += " AND phase_count = ?"
        params.append(int(phase_count))
    if frequency:
        query += " AND frequency = ?"
        params.append(int(frequency))
    if inductor_value:
        query += " AND inductor_value = ?"
        params.append(int(inductor_value))
    if pcb_name:
        query += " AND pcb_name LIKE ?"
        params.append(f"%{pcb_name}%")
    
    query += " ORDER BY upload_date DESC"
    
    cursor = conn.execute(query, params)
    records = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(records)

@app.route('/api/efficiency-data/<int:user_id>')
def get_efficiency_data(user_id):
    conn = sqlite3.connect('data/vr_efficiency.sqlite')
    cursor = conn.execute('''
        SELECT e.*, i.pcb_name, i.powerstage_name, i.phase_count
        FROM efficiency_table e
        JOIN information_table i ON e.user_id = i.user_ID
        WHERE e.user_id = ?
        ORDER BY e.iout
    ''', (user_id,))
    
    data = []
    info = None
    for row in cursor.fetchall():
        if info is None:
            info = {
                'pcb_name': row[10],
                'powerstage_name': row[11], 
                'phase_count': row[12]
            }
        data.append({
            'istep': row[1],
            'vin': row[2],
            'iin': row[3],
            'vout': row[4],
            'remote_vout_sense': row[5],
            'iout': row[6],
            'efficiency': row[7],
            'efficiency_remote': row[8]
        })
    
    conn.close()
    return jsonify({'data': data, 'info': info})

@app.route('/download/csv/<int:user_id>')
def download_csv(user_id):
    conn = sqlite3.connect('data/vr_efficiency.sqlite')
    
    # 獲取資訊
    cursor = conn.execute('SELECT * FROM information_table WHERE user_ID = ?', (user_id,))
    info = cursor.fetchone()
    
    if not info:
        abort(404)
    
    # 獲取效率數據
    cursor = conn.execute('''
        SELECT istep, vin, iin, vout, remote_vout_sense, iout, efficiency, efficiency_remote
        FROM efficiency_table WHERE user_id = ? ORDER BY iout
    ''', (user_id,))
    
    efficiency_data = cursor.fetchall()
    conn.close()
    
    # 創建 CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # 寫入標頭
    writer.writerow(['Istep', 'Vin', 'Iin', 'Vout', 'remote Vout sense', 'Iout', 'Efficiency', 'Efficiency_remote'])
    
    # 寫入資料
    for row in efficiency_data:
        writer.writerow(row)
    
    # 準備下載
    csv_data = output.getvalue()
    output.close()
    
    filename = f"{info[2]}_{info[3]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return app.response_class(
        csv_data,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )

@app.route('/admin/backup')
@admin_required
def backup_database():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f'vr_efficiency_backup_{timestamp}.sqlite'
    
    # 複製資料庫檔案
    shutil.copy2('data/vr_efficiency.sqlite', f'data/{backup_filename}')
    
    return send_file(f'data/{backup_filename}', as_attachment=True, download_name=backup_filename)

@app.route('/admin/restore', methods=['POST'])
@admin_required
def restore_database():
    if 'file' not in request.files:
        return jsonify({'error': '沒有檔案'}), 400
    
    file = request.files['file']
    if not file.filename.endswith('.sqlite'):
        return jsonify({'error': '請選擇 SQLite 檔案'}), 400
    
    try:
        # 備份當前資料庫
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        shutil.copy2('data/vr_efficiency.sqlite', f'data/backup_before_restore_{timestamp}.sqlite')
        
        # 還原資料庫
        file.save('data/vr_efficiency.sqlite')
        
        return jsonify({'success': True, 'message': '資料庫還原成功'})
    except Exception as e:
        return jsonify({'error': f'還原失敗: {str(e)}'}), 500

@app.route('/admin/table-structure/<table_name>')
@admin_required
def get_table_structure(table_name):
    if table_name not in ['efficiency_table', 'information_table']:
        return jsonify({'error': '無效的資料表名稱'}), 400
    
    conn = sqlite3.connect('data/vr_efficiency.sqlite')
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    columns = []
    for row in cursor.fetchall():
        columns.append({
            'cid': row[0],
            'name': row[1],
            'type': row[2],
            'notnull': row[3],
            'dflt_value': row[4],
            'pk': row[5]
        })
    conn.close()
    
    return jsonify(columns)

@app.route('/admin/add-column', methods=['POST'])
@admin_required
def add_column():
    table_name = request.json.get('table_name')
    column_name = request.json.get('column_name')
    column_type = request.json.get('column_type', 'TEXT')
    
    if table_name not in ['efficiency_table', 'information_table']:
        return jsonify({'error': '無效的資料表名稱'}), 400
    
    try:
        conn = sqlite3.connect('data/vr_efficiency.sqlite')
        cursor = conn.cursor()
        cursor.execute(f'ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}')
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': f'欄位 {column_name} 新增成功'})
    except Exception as e:
        return jsonify({'error': f'新增欄位失敗: {str(e)}'}), 500

@app.route('/admin/remove-column', methods=['POST'])
@admin_required
def remove_column():
    table_name = request.json.get('table_name')
    column_name = request.json.get('column_name')
    
    if table_name not in ['efficiency_table', 'information_table']:
        return jsonify({'error': '無效的資料表名稱'}), 400
    
    try:
        conn = sqlite3.connect('data/vr_efficiency.sqlite')
        cursor = conn.cursor()
        
        # SQLite 不支援直接刪除欄位，需要重建資料表
        # 1. 獲取當前資料表結構
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall() if row[1] != column_name]
        
        # 2. 創建暫存資料表
        temp_table = f"{table_name}_temp"
        cursor.execute(f"SELECT sql FROM sqlite_master WHERE name='{table_name}'")
        create_sql = cursor.fetchone()[0]
        
        # 修改 CREATE 語句以移除欄位（簡化版本，實際可能需要更複雜的解析）
        new_create_sql = create_sql.replace(table_name, temp_table)
        
        # 3. 複製資料（排除指定欄位）
        columns_str = ', '.join(columns)
        cursor.execute(f"CREATE TABLE {temp_table} AS SELECT {columns_str} FROM {table_name}")
        
        # 4. 刪除原資料表並重命名
        cursor.execute(f"DROP TABLE {table_name}")
        cursor.execute(f"ALTER TABLE {temp_table} RENAME TO {table_name}")
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': f'欄位 {column_name} 刪除成功'})
    except Exception as e:
        return jsonify({'error': f'刪除欄位失敗: {str(e)}'}), 500

@app.route('/api/multi-search')
def multi_search():
    """多條件搜尋並返回效率數據"""
    powerstage_name = request.args.get('powerstage_name')
    phase_count = request.args.get('phase_count')
    
    conn = sqlite3.connect('data/vr_efficiency.sqlite')
    
    # 搜尋符合條件的記錄
    query = '''
        SELECT i.user_ID, i.pcb_name, i.powerstage_name, i.phase_count, i.frequency,
               i.inductor_value, i.upload_date
        FROM information_table i
        WHERE 1=1
    '''
    params = []
    
    if powerstage_name:
        query += " AND i.powerstage_name LIKE ?"
        params.append(f"%{powerstage_name}%")
    if phase_count:
        query += " AND i.phase_count = ?"
        params.append(int(phase_count))
    
    cursor = conn.execute(query, params)
    records = []
    
    for row in cursor.fetchall():
        user_id = row[0]
        
        # 獲取對應的效率數據
        eff_cursor = conn.execute('''
            SELECT iout, efficiency, efficiency_remote 
            FROM efficiency_table 
            WHERE user_id = ? 
            ORDER BY iout
        ''', (user_id,))
        
        efficiency_data = []
        for eff_row in eff_cursor.fetchall():
            efficiency_data.append({
                'iout': eff_row[0],
                'efficiency': eff_row[1],
                'efficiency_remote': eff_row[2]
            })
        
        records.append({
            'user_id': user_id,
            'pcb_name': row[1],
            'powerstage_name': row[2],
            'phase_count': row[3],
            'frequency': row[4],
            'inductor_value': row[5],
            'upload_date': row[6],
            'efficiency_data': efficiency_data
        })
    
    conn.close()
    return jsonify(records)

# WebSocket 事件處理
@socketio.on('connect')
def handle_connect():
    print(f'客戶端已連接: {request.sid}')

@socketio.on('disconnect')
def handle_disconnect():
    print(f'客戶端已斷線: {request.sid}')

@socketio.on('join_room')
def handle_join_room(data):
    room = data.get('room', 'general')
    join_room(room)
    emit('joined_room', {'room': room})

if __name__ == '__main__':
    # 確保目錄存在
    if not os.path.exists('data'):
        os.makedirs('data')
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    init_db()
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)