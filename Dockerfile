FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create data directory and set permissions for OpenShift arbitrary user ID
RUN mkdir -p /app/data /app/templates /app/static && \
    chgrp -R 0 /app && \
    chmod -R g=u /app && \
    chmod -R g+w /app/data

# Create entrypoint script that handles arbitrary user ID
COPY entrypoint.sh /app/entrypoint.sh
RUN chgrp 0 /app/entrypoint.sh && \
    chmod g=u /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh

# Expose port
EXPOSE 5000

# Use entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]