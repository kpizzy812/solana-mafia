#!/bin/bash

echo "🚀 Starting Solana Mafia development environment..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ Root .env file not found. Please check .env in project root"
    exit 1
fi

echo "📋 Development services:"
echo "  - PostgreSQL Database (port 5432)"
echo "  - Redis Cache (port 6379)"
echo "  - Backend API (port 8000)"
echo "  - Frontend App (port 3000)"

echo ""
echo "🔧 Building and starting development services..."

# Build and start services
docker-compose -f docker-compose.dev.yml up --build

echo ""
echo "✅ Development environment started!"
echo ""
echo "🌐 Access URLs:"
echo "  Frontend:  http://localhost:3000"
echo "  Backend:   http://localhost:8000"
echo "  API Docs:  http://localhost:8000/docs"