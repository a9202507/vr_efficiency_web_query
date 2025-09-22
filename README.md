# VR 實測效率查詢系統

## 系統簡述

收集各式條件的實測效率，一般用戶可以透過前端上傳資料至後台資料庫，也可以透過條件找出特定資料，並且下載原始資料。管理者可以下載資料庫備份。

## 系統需求

### 前端

- JavaScript
- Chart.js
- 響應式網頁設計

### 後端

- Python 3.12 (OpenShift 基礎映像)
- Flask Framework 2.3.3
- Flask-SocketIO 5.3.6
- SQLite (內建)
- **注意：暫時移除 pandas/numpy 以避免編譯問題**

### 部署環境

- 支援本地部署
- 支援 Docker 容器化
- **支援 RedHat OpenShift 部署**（使用 S2I 建置流程）

## 已知問題解決

- **Python 3.12 distutils 問題**：移除需要編譯的套件（pandas, numpy）
- **Flask 版本問題**：使用 Flask==2.3.3（OpenShift 套件庫支援的版本）
- **OpenShift S2I 建置**：使用最簡化的套件依賴

## 資料庫設計 (SQLite)

### efficiency_table

| Column Name       | Data Type | Description                    |
| ----------------- | --------- | ------------------------------ |
| series_number\*   | INTEGER   | 主鍵，自動遞增                 |
| istep             | REAL      | 電流步階                       |
| vin               | REAL      | 輸入電壓                       |
| iin               | REAL      | 輸入電流                       |
| vout              | REAL      | 輸出電壓                       |
| remote_vout_sense | REAL      | 遠端輸出電壓感測               |
| iout              | REAL      | 輸出電流                       |
| efficiency        | REAL      | 效率                           |
| efficiency_remote | REAL      | 遠端效率                       |
| user_id           | INTEGER   | 外鍵，關聯到 information_table |

### information_table

| Column Name     | Data Type | Description    |
| --------------- | --------- | -------------- |
| user_ID\*       | INTEGER   | 主鍵，自動遞增 |
| user_name       | TEXT      | 使用者名稱     |
| pcb_name        | TEXT      | PCB 名稱       |
| powerstage_name | TEXT      | 功率級名稱     |
| phase_count     | INTEGER   | 相數           |
| frequency       | INTEGER   | 頻率 (kHz)     |
| inductor_value  | INTEGER   | 電感值 (nH)    |
| tlvr            | TEXT      | TLVR 規格      |
| imax            | INTEGER   | 最大電流 (A)   |
| upload_date     | TEXT      | 上傳日期       |
| notice          | TEXT      | 備註           |
| series_number   | INTEGER   | 系列編號       |

## 功能需求

### 一般用戶

- 多語言支援（正體中文/英文）
- 上傳 CSV/Excel 檔案到 efficiency_table
- 多條件搜尋效率資料
- 即時效率曲線圖表顯示
- 下載原始 CSV 數據

### 管理者功能

- 密碼登入取得管理權限
- 資料庫備份（自動加時間戳記）
- 資料庫還原功能
- 動態新增/刪除資料表欄位
- 記錄管理和刪除功能

## 效能需求

- 支援同時 10 位用戶線上操作
- WebSocket 即時通知
- 響應式網頁設計
- 友善錯誤訊息提示

## 部署方式

### 本地部署

```bash
pip install -r requirements.txt
python app.py
```

### Docker 部署 (本地)

```bash
docker build -t vr-efficiency-app .
docker run -p 5000:5000 vr-efficiency-app
```

### OpenShift 部署 (推薦)

```bash
# 方法 1: 使用 S2I 並自動創建路由
oc new-app python~https://github.com/your-repo/vr_efficiency_web_query.git --name=vr-efficiency-app
oc expose service/vr-efficiency-app

# 方法 2: 一次性部署並創建路由
oc new-app python~https://github.com/your-repo/vr_efficiency_web_query.git && \
oc expose service/vr-efficiency-web-query-git

# 方法 3: 使用 YAML 配置檔案部署（包含路由）
oc apply -f openshift-config.yaml

# 方法 4: 使用 Template 參數化部署（推薦）
oc process -f openshift-template.yaml \
  -p APP_NAME=vr-efficiency-app \
  -p GIT_URI=https://github.com/your-repo/vr_efficiency_web_query.git \
  -p GIT_REF=main \
  -p SECRET_KEY=your-custom-secret-key \
  -p ADMIN_PASSWORD=your-admin-password \
  | oc apply -f -

# 獲取應用程式 URL
oc get route
```

## 建置階段設定方法

### 1. S2I 環境設定檔案（自動生效）

在專案根目錄創建 `.s2i/environment` 檔案：
```bash
SECRET_KEY=vr-efficiency-default-secret-key
ADMIN_PASSWORD=admin123
FLASK_ENV=production
PORT=5000
```

### 2. OpenShift Template（參數化部署）

使用 Template 進行參數化部署：
```bash
# 部署 Template 到 OpenShift
oc apply -f openshift-template.yaml

# 使用 Template 創建應用程式
oc new-app --template=vr-efficiency-web-query-template \
  -p SECRET_KEY=your-secret-key \
  -p ADMIN_PASSWORD=your-admin-password \
  -p GIT_REF=main
```

### 3. 直接使用 YAML 配置

```bash
# 直接部署完整配置
oc apply -f openshift-config.yaml
```

### 4. Kustomize 配置（進階）

創建不同環境的配置覆蓋：
```bash
# 開發環境
oc apply -k overlays/development

# 生產環境  
oc apply -k overlays/production
```

## 上傳資料格式

- **必要欄位**：Istep, Vin, Iin, Vout, remote Vout sense, Iout, Efficiency, Efficiency_remote
- **檔案格式**：CSV 檔案（暫不支援 Excel）
- **檔案編碼**：UTF-8
- **分隔符號**：逗號 (CSV)

## 環境變數

- `SECRET_KEY`: Flask 應用程式密鑰
- `ADMIN_PASSWORD`: 管理者密碼
- `PORT`: 應用程式端口 (預設: 5000)
- `FLASK_ENV`: 開發/生產環境設定

## OpenShift 環境變數設定

```bash
# 方法 1: 命令行設定環境變數
oc set env deployment/vr-efficiency-web-query SECRET_KEY=your-secret-key
oc set env deployment/vr-efficiency-web-query ADMIN_PASSWORD=your-admin-password

# 方法 2: 使用配置檔案部署（環境變數已包含）
oc apply -f openshift-config.yaml

# 檢查部署狀態
oc get pods
oc logs deployment/vr-efficiency-web-query
```

## 路由創建方式

OpenShift 路由可以通過多種方式創建：

### 1. 命令行創建（手動）

```bash
# 在應用程式部署後手動創建
oc expose service/vr-efficiency-web-query
```

### 2. 部署時自動創建

```bash
# 部署後立即創建路由
oc new-app python~https://github.com/your-repo/vr_efficiency_web_query.git && \
oc expose service/vr-efficiency-web-query-git
```

### 3. YAML 配置檔案（推薦）

```bash
# 使用包含路由定義的 YAML 檔案
oc apply -f openshift-config.yaml
```

### 4. OpenShift Web Console

- 在 OpenShift Web Console 中
- 進入 Networking → Routes
- 點擊 "Create Route"
- 選擇對應的 Service

### 5. 使用標籤和註釋自動創建

在 Service 中添加特定標籤，某些 OpenShift 配置可以自動創建路由。

## 檔案結構

```
vr_efficiency_web_query/
├── app.py                    # 主應用程式
├── Dockerfile                # Docker 容器定義
├── entrypoint.sh            # 容器入口腳本
├── requirements.txt         # Python 依賴
├── openshift-config.yaml    # OpenShift 基本部署配置
├── openshift-template.yaml  # OpenShift Template 參數化部署
├── README.md               # 專案說明
├── .s2i/
│   └── environment         # S2I 建置時環境變數
├── templates/              # HTML 模板
├── static/                 # 靜態資源
└── data/                   # 資料庫檔案目錄
```

## 故障排除

### 常見部署問題

1. **pandas import 錯誤（已移除但仍出現）**

   - 原因：OpenShift 使用舊版本代碼或緩存
   - 解決步驟：

     ```bash
     # 確認 Git 版本已推送
     git add .
     git commit -m "Remove pandas dependency"
     git push origin main

     # 強制重新建置
     oc delete bc/vr-efficiency-web-query-git
     oc new-build python~https://github.com/your-repo/vr_efficiency_web_query.git

     # 或者清除建置緩存
     oc start-build vr-efficiency-web-query-git --from-repo=. --wait
     ```

2. **Werkzeug 生產環境錯誤**

   - 錯誤：`RuntimeError: The Werkzeug web server is not designed to run in production`
   - 原因：Flask-SocketIO 在生產環境中限制使用 Werkzeug
   - 解決：應用程式已自動檢測 OpenShift 環境並使用適當設定

3. **建置緩存問題**

   - 原因：OpenShift 使用緩存的層
   - 解決：
     ```bash
     # 刪除現有的建置配置和重新創建
     oc delete all -l app=vr-efficiency-web-query-git
     oc new-app python~https://github.com/your-repo/vr_efficiency_web_query.git
     ```

4. **無法訪問應用程式**

   - 問題：應用程式啟動成功但無法通過 IP 訪問
   - 原因：容器內部 IP 無法從外部直接訪問
   - 解決步驟：

     ```bash
     # 1. 檢查服務狀態
     oc get svc
     oc get pods

     # 2. 創建路由（如果不存在）
     oc expose service/vr-efficiency-web-query-git

     # 3. 獲取外部訪問 URL
     oc get route vr-efficiency-web-query-git -o jsonpath='{.spec.host}'

     # 4. 檢查路由詳細信息
     oc describe route vr-efficiency-web-query-git
     ```

5. **應用程式無回應**
   - 檢查 Pod 狀態和日誌：
     ```bash
     oc get pods -l app=vr-efficiency-web-query-git
     oc logs -f deployment/vr-efficiency-web-query-git
     oc describe pod <pod-name>
     ```

### 部署檢查清單

在 OpenShift 部署前，請確認：

- [ ] requirements.txt 中沒有 pandas, numpy, openpyxl
- [ ] app.py 中沒有 `import pandas as pd`
- [ ] Git repository 已推送最新代碼
- [ ] 使用正確的 Git branch (main/master/development)
- [ ] 應用程式能自動檢測 OpenShift 環境
- [ ] 已創建 OpenShift 路由提供外部訪問

### 訪問應用程式

部署成功後，通過以下步驟訪問應用程式：

1. **獲取應用程式 URL**：

   ```bash
   oc get route vr-efficiency-web-query-git
   ```

2. **訪問應用程式**：
   使用上述命令顯示的 HOST 欄位 URL，例如：

   ```
   https://vr-efficiency-web-query-git-your-project.apps.cluster.domain.com
   ```

3. **檢查應用程式狀態**：

   ```bash
   # 檢查 Pod 運行狀態
   oc get pods

   # 查看應用程式日誌
   oc logs -f deployment/vr-efficiency-web-query-git
   ```
