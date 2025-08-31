#!/bin/bash

echo "🚀 Starting Food App..."

# Stop and remove any existing containers
echo "Stopping existing containers..."
docker stop food-app-container 2>/dev/null || true
docker rm food-app-container 2>/dev/null || true

# Remove existing image to ensure fresh build
echo "Removing existing image..."
docker rmi food-app 2>/dev/null || true

# Build the image with no cache and pull latest base images using local Dockerfile
echo "Building fresh image (no cache)..."
docker build --no-cache --pull -f Dockerfile.local -t food-app .

# Check if build was successful
if [ $? -eq 0 ]; then
    echo "✅ Image built successfully!"
    
    # Run the container for local development (without Azure env file to use SQLite)
    echo "Starting container..."
    docker run -d -p 8000:8000 --name food-app-container food-app

    # Wait a moment for the container to start
    sleep 3

    # Check if container is running
    if docker ps | grep -q food-app-container; then
        echo "✅ Container is running!"
        echo "🌐 Open your browser and go to: http://localhost:8000"
        echo ""
        echo "Useful commands:"
        echo "  View logs: docker logs food-app-container"
        echo "  Stop container: docker stop food-app-container"
        echo "  Remove container: docker rm food-app-container"
        echo "  Rebuild fresh: ./run_local.sh"
    else
        echo "❌ Container failed to start. Check logs with: docker logs food-app-container"
    fi
else
    echo "❌ Image build failed. Please check the Dockerfile and try again."
fi 