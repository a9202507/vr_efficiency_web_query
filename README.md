# VR實測效率查詢系統

## 系統簡述
收集各式條件的實測效率，一般用戶可以透過前端上傳資料至後台資料庫，也可以透過條件找出特定資料，並且下載原始資料。管理者可以下載資料庫備份。

## 系統需求
### 前端
* JavaScript
* Chart.js
* 響應式網頁設計

### 後端
* Python 3.12
* Flask Framework 2.3.7
* Flask-SocketIO 5.3.6
* SQLite (內建)
* Pandas 2.2.2
* Numpy 1.26.4

### 部署環境
* 支援本地部署
* 支援 Docker 容器化
* **支援 RedHat OpenShift 部署**（已針對任意用戶 ID 進行優化）

## 已知問題解決
* **Numpy/Pandas 相容性問題**：已鎖定 numpy==1.26.4 和 pandas==2.2.2 版本
* **OpenShift 權限問題**：已配置適當的檔案權限和用戶 ID 範圍
* **套件安裝順序**：先安裝 numpy 再安裝其他依賴套件

## 資料庫設計 (SQLite)

### efficiency_table
| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| series_number* | INTEGER | 主鍵，自動遞增 |
| istep | REAL | 電流步階 |
| vin | REAL | 輸入電壓 |
| iin | REAL | 輸入電流 |
| vout | REAL | 輸出電壓 |
| remote_vout_sense | REAL | 遠端輸出電壓感測 |
| iout | REAL | 輸出電流 |
| efficiency | REAL | 效率 |
| efficiency_remote | REAL | 遠端效率 |
| user_id | INTEGER | 外鍵，關聯到 information_table |

### information_table
| Column Name | Data Type | Description |
|-------------|-----------|-------------|
| user_ID* | INTEGER | 主鍵，自動遞增 |
| user_name | TEXT | 使用者名稱 |
| pcb_name | TEXT | PCB 名稱 |
| powerstage_name | TEXT | 功率級名稱 |
| phase_count | INTEGER | 相數 |
| frequency | INTEGER | 頻率 (kHz) |
| inductor_value | INTEGER | 電感值 (nH) |
| tlvr | TEXT | TLVR 規格 |
| imax | INTEGER | 最大電流 (A) |
| upload_date | TEXT | 上傳日期 |
| notice | TEXT | 備註 |
| series_number | INTEGER | 系列編號 |

## 功能需求

### 一般用戶
* 多語言支援（正體中文/英文）
* 上傳 CSV/Excel 檔案到 efficiency_table
* 多條件搜尋效率資料
* 即時效率曲線圖表顯示
* 下載原始 CSV 數據

### 管理者功能
* 密碼登入取得管理權限
* 資料庫備份（自動加時間戳記）
* 資料庫還原功能
* 動態新增/刪除資料表欄位
* 記錄管理和刪除功能

## 效能需求
* 支援同時 10 位用戶線上操作
* WebSocket 即時通知
* 響應式網頁設計
* 友善錯誤訊息提示

## 部署方式

### 本地部署
```bash
pip install -r requirements.txt
python app.py
```

### Docker 部署
```bash
docker build -t vr-efficiency-app .
docker run -p 5000:5000 vr-efficiency-app
```

### OpenShift 部署
```bash
# 使用 Dockerfile 建立映像
oc new-build --dockerfile=- --name=vr-efficiency-app < Dockerfile

# 或從 Git repository 部署
oc new-app https://github.com/your-repo/vr_efficiency_web_query
```

## 上傳資料格式
* **必要欄位**：Istep, Vin, Iin, Vout, remote Vout sense, Iout, Efficiency, Efficiency_remote
* **檔案格式**：CSV 或 Excel (.xlsx, .xls)
* **檔案編碼**：UTF-8
* **分隔符號**：逗號 (CSV)

## 環境變數
* `SECRET_KEY`: Flask 應用程式密鑰
* `ADMIN_PASSWORD`: 管理者密碼
* `PORT`: 應用程式端口 (預設: 5000)
* `FLASK_ENV`: 開發/生產環境設定

## 檔案結構
```
vr_efficiency_web_query/
├── app.py              # 主應用程式
├── Dockerfile          # Docker 容器定義
├── entrypoint.sh       # 容器入口腳本
├── requirements.txt    # Python 依賴
├── README.md          # 專案說明
├── templates/         # HTML 模板
├── static/           # 靜態資源
└── data/            # 資料庫檔案目錄
```

## 故障排除

### 常見部署問題
1. **numpy.dtype size changed 錯誤**
   - 原因：pandas 和 numpy 版本不相容
   - 解決：使用指定版本的 requirements.txt

2. **權限問題 (OpenShift)**
   - 原因：容器使用任意用戶 ID
   - 解決：已在 Dockerfile 中設定正確的群組權限

3. **套件安裝失敗**
   - 原因：缺少編譯工具
   - 解決：已在 Dockerfile 中安裝 gcc, g++, build-essential