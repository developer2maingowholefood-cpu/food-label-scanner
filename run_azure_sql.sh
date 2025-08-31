#!/bin/bash

echo "🌐 Starting Food App with Azure SQL Database..."

# Stop any existing containers
echo "Stopping existing containers..."
docker stop food-app-container 2>/dev/null || true
docker rm food-app-container 2>/dev/null || true

# Run the container with Azure SQL configuration
echo "Starting container with Azure SQL Database..."
docker run -d -p 8000:8000 --env-file azure-production.env --name food-app-container food-app

# Wait a moment for the container to start
sleep 5

# Check if container is running
if docker ps | grep -q food-app-container; then
    echo "✅ Container is running with Azure SQL Database!"
    echo "🌐 Open your browser and go to: http://localhost:8000"
    echo ""
    echo "Useful commands:"
    echo "  View logs: docker logs food-app-container -f"
    echo "  Stop container: docker stop food-app-container"
    echo "  Remove container: docker rm food-app-container"
    echo ""
    echo "📊 Database: Azure SQL Database (production ready)"
    echo "🔗 Connection: foodapp-db.database.windows.net"
else
    echo "❌ Container failed to start. Check logs with: docker logs food-app-container"
fi 