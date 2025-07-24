#!/bin/bash

# Deploy script for Kleinanzeigen API on Raspberry Pi
# Make sure to run this script on your Raspberry Pi

set -e

echo "🚀 Starting deployment of Kleinanzeigen API on Raspberry Pi..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "Run: curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    echo "Run: sudo apt-get install docker-compose-plugin"
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Stop and remove existing containers
echo "🛑 Stopping existing containers..."
docker-compose down --remove-orphans || true

# Build and start the application
echo "🔨 Building and starting the application..."
docker-compose up --build -d

# Wait for the application to start
echo "⏳ Waiting for the application to start..."
sleep 10

# Check if the application is running
if curl -f http://localhost:8000/ > /dev/null 2>&1; then
    echo "✅ Application is running successfully!"
    echo "🌐 API is available at: http://localhost:8000"
    echo "📖 API documentation at: http://localhost:8000/docs"
else
    echo "❌ Application failed to start. Check logs with: docker-compose logs"
    exit 1
fi

echo "🎉 Deployment completed successfully!"
echo ""
echo "Useful commands:"
echo "  View logs: docker-compose logs -f"
echo "  Stop app: docker-compose down"
echo "  Restart app: docker-compose restart"
echo "  Update app: ./deploy.sh" 