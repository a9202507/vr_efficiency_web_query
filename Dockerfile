# This file is for local Docker builds only
# OpenShift will use S2I build process with the base Python image

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create necessary directories and set permissions for OpenShift arbitrary user ID
RUN mkdir -p /app/data /app/templates /app/static && \
    chgrp -R 0 /app && \
    chmod -R g=u /app && \
    chmod -R g+w /app/data

# Create a user that matches OpenShift's default UID range
RUN useradd -u 1001 -r -g 0 -m -d /app -s /sbin/nologin -c "Default user" default && \
    chown -R 1001:0 /app

# Switch to non-root user
USER 1001

# Expose port
EXPOSE 5000

# Start the application
CMD ["python", "app.py"]