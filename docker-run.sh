#!/bin/bash

# Script to build and run the datasette Docker container

echo "🐳 Building AHL Datasette Docker image..."
docker build -t ahl-datasette:latest .

echo "🚀 Starting container..."
docker-compose up -d

echo "⏳ Waiting for datasette to start..."
sleep 10

echo "🔍 Checking if datasette is running..."
if curl -f http://localhost:8001/ > /dev/null 2>&1; then
    echo "✅ Datasette is running at http://localhost:8001/"
    echo "📊 You can access the metadata queries at http://localhost:8001/-/metadata"
else
    echo "❌ Datasette failed to start. Check logs with: docker-compose logs datasette"
fi