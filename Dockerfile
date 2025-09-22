FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies with specific order to avoid conflicts
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir numpy==1.26.4 && \
    pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create necessary directories and set permissions for OpenShift arbitrary user ID
RUN mkdir -p /app/data /app/templates /app/static && \
    chgrp -R 0 /app && \
    chmod -R g=u /app && \
    chmod -R g+w /app/data

# Make sure entrypoint script has correct permissions
RUN if [ -f entrypoint.sh ]; then \
        chgrp 0 /app/entrypoint.sh && \
        chmod g=u /app/entrypoint.sh && \
        chmod +x /app/entrypoint.sh; \
    fi

# Create a user that matches OpenShift's default UID range
RUN useradd -u 1001 -r -g 0 -m -d /app -s /sbin/nologin -c "Default user" default && \
    chown -R 1001:0 /app

# Switch to non-root user
USER 1001

# Expose port
EXPOSE 5000

# Use either entrypoint script or direct python command
CMD ["python", "app.py"]