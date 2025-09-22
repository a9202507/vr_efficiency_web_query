#!/bin/bash

# Add the current user to /etc/passwd if it doesn't exist
# This is required for some applications that check user names
if ! whoami &> /dev/null; then
  if [ -w /etc/passwd ]; then
    echo "${USER_NAME:-default}:x:$(id -u):0:${USER_NAME:-default} user:${HOME}:/sbin/nologin" >> /etc/passwd
  fi
fi

# Create data directory if it doesn't exist
mkdir -p /app/data

# Initialize database if it doesn't exist
python -c "
import sys
sys.path.append('/app')
from app import init_db
init_db()
"

# Start the application
exec python app.py
