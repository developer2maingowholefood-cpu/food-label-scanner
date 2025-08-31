#!/bin/bash

echo "🚀 Starting Food Label Scanner on Azure App Service..."

# Try multiple possible locations for our application files
# Azure Oryx extracts to /tmp/<random-id> - check for any /tmp/ subdirectory with src/
POSSIBLE_PATHS=(
    "/app" 
    "/tmp/8ddce2041e4db99"
    "/home/site/wwwroot"
)

# Also dynamically check for any /tmp/ subdirectory containing src/
for tmp_dir in /tmp/*/; do
    if [ -d "$tmp_dir" ] && [ -d "${tmp_dir}src" ] && [ -f "${tmp_dir}src/app.py" ]; then
        POSSIBLE_PATHS=("$tmp_dir" "${POSSIBLE_PATHS[@]}")
        break
    fi
done

APP_PATH=""
for path in "${POSSIBLE_PATHS[@]}"; do
    echo "🔍 Checking path: $path"
    if [ -d "$path" ]; then
        cd "$path"
        echo "Directory contents for $path:"
        ls -la
        
        if [ -d "src" ] && [ -f "src/app.py" ]; then
            echo "✅ Found src/app.py in $path"
            APP_PATH="$path"
            break
        else
            echo "❌ No src/app.py found in $path"
        fi
    else
        echo "❌ Path $path does not exist"
    fi
done

if [ -z "$APP_PATH" ]; then
    echo "❌ ERROR: Could not find src/app.py in any expected location!"
    echo "Searched paths: ${POSSIBLE_PATHS[*]}"
    exit 1
fi

# Change to the found application directory
cd "$APP_PATH"
echo "✅ Using application path: $APP_PATH"

# Set Python path
export PYTHONPATH="$APP_PATH/src:$PYTHONPATH"

echo "🌐 Starting web server with gunicorn..."

# Start the application with Azure App Service compatible settings
exec gunicorn --bind=0.0.0.0:8000 --timeout 600 --workers 1 src.app:app 