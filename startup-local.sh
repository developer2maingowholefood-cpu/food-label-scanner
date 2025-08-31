#!/bin/bash

echo "🚀 Starting Food Label Scanner locally..."

# We're in /app directory in Docker container
cd /app

echo "✅ Using application path: /app"
echo "Directory contents:"
ls -la

# Verify our application files exist
if [ ! -f "src/app.py" ]; then
    echo "❌ ERROR: src/app.py not found!"
    exit 1
fi

# Set Python path
export PYTHONPATH="/app/src:$PYTHONPATH"

echo "🌐 Starting web server with gunicorn..."

# Start the application for local development
exec gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 1 --reload src.app:app