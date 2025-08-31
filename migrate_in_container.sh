#!/bin/bash

echo "🐳 Running Azure SQL Migration inside Docker Container..."

# Stop any existing containers
echo "Stopping existing containers..."
docker stop food-app-container 2>/dev/null || true
docker rm food-app-container 2>/dev/null || true

# Copy the migration script to the container
echo "Setting up migration environment..."
docker run -d -p 8000:8000 --env-file azure-production.env --name food-app-container food-app

# Wait for container to start
sleep 3

# Copy migration script to container
docker cp migrate_to_azure_sql.py food-app-container:/app/

# Run migration inside container
echo "🚀 Starting migration inside container..."
docker exec food-app-container python3 /app/migrate_to_azure_sql.py

# Check migration result
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Migration completed successfully!"
    echo "🌐 Your app is now using Azure SQL Database"
    echo "📊 You can access the app at: http://localhost:8000"
else
    echo ""
    echo "❌ Migration failed. Check the logs above for details."
    echo "🔧 You can still use SQLite with: ./run_local.sh"
fi 