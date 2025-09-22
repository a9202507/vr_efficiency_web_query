# app2.py - VR實測效率查詢系統 v2.0
from flask import Flask, request, jsonify, render_template, send_file, session, make_response
from flask_socketio import SocketIO, emit, join_room
import sqlite3
import pandas as pd
import os
import shutil
from datetime import datetime
from functools import wraps
import io
import csv

app = Flask(__name__)
app.secret_key = 'vr-efficiency-system-v2-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

ADMIN_PASSWORD = "admin123"  # 生產環境請更改此密碼

# 多語言支援
LANGUAGES = {
    'zh': {
        'title': 'VR 實測效率查詢系統',
        'subtitle': '電壓調節器效率分析平台',
        'upload_data': '上傳數據',
        'search_analysis': '搜尋分析',
        'system_management': '系統管理',
        'admin_login': '管理者登入',
        'admin_logout': '管理者登出',
        'upload_title': '上傳效率測試數據',
        'search_title': '多條件搜尋',
        'user_name': '使用者名稱',
        'pcb_name': 'PCB 名稱',
        'powerstage_name': 'Power Stage 名稱',
        'phase_count': '相數',
        'frequency': '頻率 (kHz)',
        'inductor_value': '電感值 (nH)',
        'max_current': '最大電流 (A)',
        'remarks': '備註',
        'upload_file': '上傳檔案',
        'upload_success': '上傳成功！',
        'upload_failed': '上傳失敗',
        'search_records': '搜尋記錄',
        'no_records': '沒有找到記錄',
        'download_data': '下載數據',
        'backup_database': '備份資料庫',
        'restore_database': '還原資料庫',
        'delete_record': '刪除記錄',
        'table_management': '資料表管理',
        'version': '版本'
    },
    'en': {
        'title': 'VR Efficiency Query System',
        'subtitle': 'Voltage Regulator Efficiency Analysis Platform',
        'upload_data': 'Upload Data',
        'search_analysis': 'Search Analysis',
        'system_management': 'System Management',
        'admin_login': 'Admin Login',
        'admin_logout': 'Admin Logout',
        'upload_title': 'Upload Efficiency Test Data',
        'search_title': 'Multi-condition Search',
        'user_name': 'User Name',
        'pcb_name': 'PCB Name',
        'powerstage_name': 'Power Stage Name',
        'phase_count': 'Phase Count',
        'frequency': 'Frequency (kHz)',
        'inductor_value': 'Inductor Value (nH)',
        'max_current': 'Max Current (A)',
        'remarks': 'Remarks',
        'upload_file': 'Upload File',
        'upload_success': 'Upload Success!',
        'upload_failed': 'Upload Failed',
        'search_records': 'Search Records',
        'no_records': 'No records found',
        'download_data': 'Download Data',
        'backup_database': 'Backup Database',
        'restore_database': 'Restore Database',
        'delete_record': 'Delete Record',
        'table_management': 'Table Management',
        'version': 'Version'
    }
}

# 權限裝飾器
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return jsonify({'error': 'Admin permission required'}), 403
        return f(*args, **kwargs)
    return decorated_function

# 語言檢測
def get_language():
    return session.get('language', 'zh')

def get_translations():
    lang = get_language()
    return LANGUAGES.get(lang, LANGUAGES['zh'])

# 資料庫初始化
def init_db():
    conn = sqlite3.connect('data/vr_efficiency_v2.sqlite')
    cursor = conn.cursor()

    # information_table - 根據 README.md 設計
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS information_table (
            user_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT NOT NULL,
            pcb_name TEXT NOT NULL,
            powerstage_name TEXT NOT NULL,
            phase_count INTEGER NOT NULL,
            frequency INTEGER NOT NULL,
            inductor_value INTEGER NOT NULL,
            tlvr TEXT DEFAULT 'no',
            imax INTEGER NOT NULL,
            upload_date TEXT DEFAULT CURRENT_TIMESTAMP,
            notice TEXT,
            series_number INTEGER UNIQUE
        )
    ''')

    # efficiency_table - 根據 README.md 設計
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
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_frequency ON information_table(frequency)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON efficiency_table(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_vin ON efficiency_table(vin)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_vout ON efficiency_table(vout)')

    conn.commit()
    conn.close()

# 驗證範圍格式 (支援 11.2~13.2 格式)
def parse_range(range_str):
    if not range_str:
        return None, None
    
    # 支援多種分隔符號
    if '~' in range_str:
        parts = range_str.split('~')
    elif '-' in range_str:
        parts = range_str.split('-')
    elif ',' in range_str:
        parts = range_str.split(',')
    else:
        return None, None
    
    if len(parts) == 2:
        try:
            min_val = float(parts[0].strip())
            max_val = float(parts[1].strip())
            return min_val, max_val
        except ValueError:
            return None, None
    return None, None

@app.route('/')
def index():
    return render_template('index2.html', translations=get_translations(), language=get_language())

@app.route('/set-language/<lang>')
def set_language(lang):
    if lang in LANGUAGES:
        session['language'] = lang
    return jsonify({'success': True, 'language': lang})

@app.route('/admin/login', methods=['POST'])
def admin_login():
    password = request.json.get('password')
    if password == ADMIN_PASSWORD:
        session['is_admin'] = True
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Invalid password'}), 401

@app.route('/admin/logout', methods=['POST'])
def admin_logout():
    session.pop('is_admin', None)
    return jsonify({'success': True})

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Please select a file'}), 400

        # 支援 CSV 和 Excel 格式
        if file.filename.endswith('.csv'):
            file_content = file.read().decode('utf-8')
            df = pd.read_csv(io.StringIO(file_content))
        elif file.filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file)
        else:
            return jsonify({'error': 'Unsupported file format. Please upload CSV or Excel file.'}), 400

        # 驗證必要欄位
        required_columns = ['Istep', 'Vin', 'Iin', 'Vout', 'remote Vout sense', 'Iout', 'Efficiency', 'Efficiency_remote']
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            return jsonify({'error': f'Missing required columns: {", ".join(missing_columns)}'}), 400

        # 獲取表單數據
        info_data = {
            'user_name': request.form.get('user_name'),
            'pcb_name': request.form.get('pcb_name'),
            'powerstage_name': request.form.get('powerstage_name'),
            'phase_count': int(request.form.get('phase_count')),
            'frequency': int(request.form.get('frequency')),
            'inductor_value': int(request.form.get('inductor_value')),
            'tlvr': request.form.get('tlvr', 'no'),
            'imax': int(request.form.get('imax')),
            'upload_date': datetime.now().isoformat(),
            'notice': request.form.get('notice', '')
        }

        # 驗證必要欄位
        if not all([info_data['user_name'], info_data['pcb_name'], info_data['powerstage_name']]):
            return jsonify({'error': 'Please fill all required fields'}), 400

        conn = sqlite3.connect('data/vr_efficiency_v2.sqlite')
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
        series_number = None
        for _, row in df.iterrows():
            cursor.execute('''
                INSERT INTO efficiency_table 
                (istep, vin, iin, vout, remote_vout_sense, iout, efficiency, efficiency_remote, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (row['Istep'], row['Vin'], row['Iin'], row['Vout'],
                  row['remote Vout sense'], row['Iout'], row['Efficiency'], 
                  row['Efficiency_remote'], user_id))

            if series_number is None:
                series_number = cursor.lastrowid

        # 更新 information_table 的 series_number
        cursor.execute('UPDATE information_table SET series_number = ? WHERE user_ID = ?', 
                      (series_number, user_id))

        conn.commit()
        conn.close()

        # WebSocket 通知
        socketio.emit('new_data_uploaded', {
            'user_id': user_id,
            'pcb_name': info_data['pcb_name'],
            'user_name': info_data['user_name'],
            'powerstage_name': info_data['powerstage_name']
        })

        return jsonify({'success': True, 'user_id': user_id, 'series_number': series_number})

    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/api/search')
def search_records():
    # 多條件搜尋，支援範圍查詢
    powerstage_name = request.args.get('powerstage_name')
    phase_count = request.args.get('phase_count')
    frequency = request.args.get('frequency')
    inductor_value = request.args.get('inductor_value')
    pcb_name = request.args.get('pcb_name')
    vin_range = request.args.get('vin_range')
    vout_range = request.args.get('vout_range')
    max_current_range = request.args.get('max_current_range')
    tlvr = request.args.get('tlvr')
    
    conn = sqlite3.connect('data/vr_efficiency_v2.sqlite')
    conn.row_factory = sqlite3.Row
    
    # 解析範圍參數
    vin_min, vin_max = parse_range(vin_range)
    vout_min, vout_max = parse_range(vout_range)
    imax_min, imax_max = parse_range(max_current_range)
    
    # 構建查詢
    if vin_min or vout_min:
        query = """
            SELECT DISTINCT i.* FROM information_table i
            JOIN efficiency_table e ON i.user_ID = e.user_id
            WHERE 1=1
        """
    else:
        query = "SELECT * FROM information_table WHERE 1=1"
    
    params = []
    
    # 基本條件
    if powerstage_name:
        table_prefix = "i." if (vin_min or vout_min) else ""
        query += f" AND {table_prefix}powerstage_name LIKE ?"
        params.append(f"%{powerstage_name}%")
    
    if phase_count:
        table_prefix = "i." if (vin_min or vout_min) else ""
        query += f" AND {table_prefix}phase_count = ?"
        params.append(int(phase_count))
    
    if frequency:
        table_prefix = "i." if (vin_min or vout_min) else ""
        query += f" AND {table_prefix}frequency = ?"
        params.append(int(frequency))
    
    if inductor_value:
        table_prefix = "i." if (vin_min or vout_min) else ""
        query += f" AND {table_prefix}inductor_value = ?"
        params.append(int(inductor_value))
    
    if pcb_name:
        table_prefix = "i." if (vin_min or vout_min) else ""
        query += f" AND {table_prefix}pcb_name LIKE ?"
        params.append(f"%{pcb_name}%")
    
    if tlvr:
        table_prefix = "i." if (vin_min or vout_min) else ""
        query += f" AND {table_prefix}tlvr = ?"
        params.append(tlvr)
    
    # 範圍條件
    if vin_min and vin_max:
        query += " AND e.vin BETWEEN ? AND ?"
        params.extend([vin_min, vin_max])
    
    if vout_min and vout_max:
        query += " AND e.vout BETWEEN ? AND ?"
        params.extend([vout_min, vout_max])
    
    if imax_min and imax_max:
        table_prefix = "i." if (vin_min or vout_min) else ""
        query += f" AND {table_prefix}imax BETWEEN ? AND ?"
        params.extend([imax_min, imax_max])
    
    query += " ORDER BY i.upload_date DESC" if (vin_min or vout_min) else " ORDER BY upload_date DESC"
    
    cursor = conn.execute(query, params)
    records = []
    
    for row in cursor.fetchall():
        record = dict(row)
        # 獲取效率數據
        eff_cursor = conn.execute('''
            SELECT iout, efficiency, efficiency_remote, vin, vout
            FROM efficiency_table 
            WHERE user_id = ? 
            ORDER BY iout
        ''', (row['user_ID'],))
        
        efficiency_data = []
        for eff_row in eff_cursor.fetchall():
            efficiency_data.append({
                'iout': eff_row[0],
                'efficiency': eff_row[1],
                'efficiency_remote': eff_row[2],
                'vin': eff_row[3],
                'vout': eff_row[4]
            })
        
        record['efficiency_data'] = efficiency_data
        records.append(record)
    
    conn.close()
    return jsonify(records)

@app.route('/api/powerstage-options')
def get_powerstage_options():
    try:
        conn = sqlite3.connect('data/vr_efficiency_v2.sqlite')
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT powerstage_name FROM information_table ORDER BY powerstage_name')
        options = [row[0] for row in cursor.fetchall()]
        conn.close()
        return jsonify(options)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/series-numbers')
def get_series_numbers():
    try:
        conn = sqlite3.connect('data/vr_efficiency_v2.sqlite')
        cursor = conn.cursor()
        cursor.execute('SELECT series_number FROM information_table WHERE series_number IS NOT NULL ORDER BY series_number DESC')
        numbers = [row[0] for row in cursor.fetchall()]
        conn.close()
        return jsonify(numbers)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/csv/<int:series_number>')
def download_csv(series_number):
    try:
        conn = sqlite3.connect('data/vr_efficiency_v2.sqlite')
        cursor = conn.cursor()
        
        # 獲取基本資訊
        cursor.execute('''
            SELECT user_ID, pcb_name, powerstage_name, phase_count, frequency, 
                   inductor_value, imax, upload_date 
            FROM information_table WHERE series_number = ?
        ''', (series_number,))
        
        info = cursor.fetchone()
        if not info:
            return jsonify({'error': 'No data found'}), 404
        
        user_id = info[0]
        
        # 獲取效率數據
        cursor.execute('''
            SELECT istep as "Istep", vin as "Vin", iin as "Iin", vout as "Vout", 
                   remote_vout_sense as "remote Vout sense", iout as "Iout", 
                   efficiency as "Efficiency", efficiency_remote as "Efficiency_remote"
            FROM efficiency_table
            WHERE user_id = ? 
            ORDER BY iout
        ''', (user_id,))
        
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        if not rows:
            return jsonify({'error': 'No efficiency data found'}), 404
        
        # 生成檔名
        pcb_name, powerstage_name, phase_count, frequency, inductor_value, imax, upload_date = info[1:]
        
        # 獲取第一筆 vin/vout
        first_vin = rows[0][1] if rows else "NA"
        first_vout = rows[0][3] if rows else "NA"
        
        # 處理日期格式
        try:
            if upload_date:
                dt = datetime.fromisoformat(upload_date.replace('Z', '+00:00'))
                date_str = dt.strftime("%Y%m%d-%H%M")
            else:
                date_str = "unknown"
        except Exception:
            date_str = "unknown"
        
        filename = f"{pcb_name}_{first_vin}vin_{first_vout}vout_{powerstage_name}_{phase_count}ph_{frequency}khz_{inductor_value}nH_{imax}Amps_{date_str}.csv"
        
        # 生成 CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(columns)
        writer.writerows(rows)
        output.seek(0)
        
        response = make_response(output.getvalue())
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"
        response.headers["Content-type"] = "text/csv; charset=utf-8"
        
        conn.close()
        return response
        
    except Exception as e:
        return jsonify({'error': f'Download failed: {str(e)}'}), 500

@app.route('/api/multi-search')
def multi_search():
    series_numbers = request.args.get('series_numbers')
    if not series_numbers:
        return jsonify([])
    
    try:
        sn_list = [int(s.strip()) for s in series_numbers.split(',') if s.strip().isdigit()]
        
        conn = sqlite3.connect('data/vr_efficiency_v2.sqlite')
        records = []
        
        for sn in sn_list:
            cursor = conn.execute('''
                SELECT user_ID, pcb_name, powerstage_name, phase_count, frequency, 
                       inductor_value, upload_date 
                FROM information_table WHERE series_number = ?
            ''', (sn,))
            
            info_row = cursor.fetchone()
            if info_row:
                user_id = info_row[0]
                
                # 獲取效率數據
                eff_cursor = conn.execute('''
                    SELECT iout, efficiency, efficiency_remote, vin, vout
                    FROM efficiency_table
                    WHERE user_id = ?
                    ORDER BY iout
                ''', (user_id,))
                
                efficiency_data = []
                for eff_row in eff_cursor.fetchall():
                    efficiency_data.append({
                        'iout': eff_row[0],
                        'efficiency': eff_row[1],
                        'efficiency_remote': eff_row[2],
                        'vin': eff_row[3],
                        'vout': eff_row[4]
                    })
                
                records.append({
                    'user_id': user_id,
                    'pcb_name': info_row[1],
                    'powerstage_name': info_row[2],
                    'phase_count': info_row[3],
                    'frequency': info_row[4],
                    'inductor_value': info_row[5],
                    'upload_date': info_row[6],
                    'efficiency_data': efficiency_data,
                    'series_number': sn
                })
        
        conn.close()
        return jsonify(records)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 管理者功能
@app.route('/admin/backup')
@admin_required
def backup_database():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f'vr_efficiency_v2_backup_{timestamp}.sqlite'
    
    shutil.copy2('data/vr_efficiency_v2.sqlite', f'data/{backup_filename}')
    
    return send_file(f'data/{backup_filename}', as_attachment=True, download_name=backup_filename)

@app.route('/admin/restore', methods=['POST'])
@admin_required
def restore_database():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if not file.filename.endswith('.sqlite'):
        return jsonify({'error': 'Please select SQLite file'}), 400
    
    try:
        # 備份當前資料庫
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        shutil.copy2('data/vr_efficiency_v2.sqlite', f'data/backup_before_restore_{timestamp}.sqlite')
        
        # 還原資料庫
        file.save('data/vr_efficiency_v2.sqlite')
        
        return jsonify({'success': True, 'message': 'Database restored successfully'})
    except Exception as e:
        return jsonify({'error': f'Restore failed: {str(e)}'}), 500

@app.route('/admin/delete-record/<int:series_number>', methods=['DELETE'])
@admin_required
def delete_record(series_number):
    try:
        conn = sqlite3.connect('data/vr_efficiency_v2.sqlite')
        cursor = conn.cursor()
        
        # 獲取 user_id
        cursor.execute('SELECT user_ID FROM information_table WHERE series_number = ?', (series_number,))
        result = cursor.fetchone()
        if not result:
            return jsonify({'error': 'Record not found'}), 404
        
        user_id = result[0]
        
        # 刪除效率數據
        cursor.execute('DELETE FROM efficiency_table WHERE user_id = ?', (user_id,))
        
        # 刪除基本資訊
        cursor.execute('DELETE FROM information_table WHERE user_ID = ?', (user_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Record deleted successfully'})
    except Exception as e:
        return jsonify({'error': f'Delete failed: {str(e)}'}), 500

@app.route('/admin/update-information/<int:user_id>', methods=['POST'])
@admin_required
def update_information(user_id):
    try:
        update_data = request.json
        if not update_data:
            return jsonify({'error': 'No data provided'}), 400
        
        # 允許更新的欄位
        allowed_fields = [
            'user_name', 'pcb_name', 'powerstage_name', 'phase_count', 
            'frequency', 'inductor_value', 'tlvr', 'imax', 'notice'
        ]
        
        update_fields = {k: v for k, v in update_data.items() if k in allowed_fields}
        if not update_fields:
            return jsonify({'error': 'No valid fields to update'}), 400
        
        set_clause = ', '.join([f"{k} = ?" for k in update_fields.keys()])
        values = list(update_fields.values()) + [user_id]
        
        conn = sqlite3.connect('data/vr_efficiency_v2.sqlite')
        cursor = conn.cursor()
        cursor.execute(f'UPDATE information_table SET {set_clause} WHERE user_ID = ?', values)
        
        if cursor.rowcount == 0:
            return jsonify({'error': 'Record not found'}), 404
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Record updated successfully'})
    except Exception as e:
        return jsonify({'error': f'Update failed: {str(e)}'}), 500

# WebSocket 事件處理
@socketio.on('connect')
def handle_connect():
    print(f'Client connected: {request.sid}')

@socketio.on('disconnect')
def handle_disconnect():
    print(f'Client disconnected: {request.sid}')

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
    port = int(os.environ.get('PORT', 5001))  # 使用不同端口避免衝突
    debug = os.environ.get('FLASK_ENV', 'production') == 'development'
    socketio.run(app, debug=debug, host='0.0.0.0', port=port)