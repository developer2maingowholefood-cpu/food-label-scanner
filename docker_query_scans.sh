#!/bin/bash

# Script to query scans from inside the Docker container
echo "🔍 Querying scans from Docker container..."

# Run the query script inside the container
docker exec -it food-app-container python /app/query_scans.py

echo "✅ Query completed" 