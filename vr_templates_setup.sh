#!/bin/bash
# setup.sh - VR效率查詢系統安裝腳本

echo "🚀 VR實測效率查詢系統 - 安裝腳本"
echo "=================================="

# 創建專案目錄結構
echo "📁 創建目錄結構..."
mkdir -p vr-efficiency-system
cd vr-efficiency-system

mkdir -p templates
mkdir -p data
mkdir -p uploads

# 創建 templates/index.html (將前端 HTML 內容複製到此文件)
echo "📄 創建模板檔案..."
cat > templates/index.html << 'EOF'
<!-- 這裡應該放置完整的前端 HTML 內容 -->
<!-- 請將前端 HTML artifact 的內容複製到這個檔案 -->
EOF

echo "⚠️  請手動將前端 HTML 內容複製到 templates/index.html"

# 創建 app.py (將後端 Python 內容複製到此文件)  
echo "📄 創建應用檔案..."
cat > app.py << 'EOF'
# 請將後端 Python artifact 的內容複製到這個檔案
EOF

echo "⚠️  請手動將後端 Python 內容複製到 app.py"

# 創建 requirements.txt
echo "📄 創建需求檔案..."
cat > requirements.txt << 'EOF'
Flask==3.0.0
Flask-SocketIO==5.3.6
pandas==2.1.4
python-socketio==5.10.0
eventlet==0.33.3
gunicorn==21.2.0
EOF

# 創建 Dockerfile
echo "📄 創建 Dockerfile..."
cat > Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# 複製需求檔案
COPY requirements.txt .

# 安裝 Python 依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式碼
COPY app.py .
COPY templates/ ./templates/

# 創建必要目錄
RUN mkdir -p data uploads templates

# 設置權限
RUN chmod +x app.py

# 建立非 root 使用者
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# 暴露端口
EXPOSE 5000

# 健康檢查
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# 啟動命令
CMD ["python", "app.py"]
EOF

# 創建 docker-compose.yml
echo "📄 創建 Docker Compose 檔案..."
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  vr-efficiency-system:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - vr_data:/app/data
      - ./uploads:/app/uploads
    environment:
      - FLASK_ENV=production
      - SECRET_KEY=vr-efficiency-system-secret-2024
      - ADMIN_PASSWORD=VR_Admin_2024!
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - vr_network

volumes:
  vr_data: