#!/bin/bash

echo "🚀 Starting Solana Mafia full stack application..."

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

echo "📋 Services to start:"
echo "  - PostgreSQL Database (port 5432)"
echo "  - Redis Cache (port 6379)"
echo "  - Backend API (port 8000)"
echo "  - Frontend App (port 3000)"
echo "  - WebSocket Server (port 8001)"
echo "  - Event Indexer Service"
echo "  - Earnings Scheduler Service"
echo "  - Telegram Bot Service"
echo "  - Nginx Reverse Proxy (port 80)"

echo ""
echo "🔧 Building and starting services..."

# Build and start services
docker-compose up --build -d

# Wait a bit for services to start
echo "⏳ Waiting for services to initialize..."
sleep 10

# Check service status
echo ""
echo "📊 Service Status:"
docker-compose ps

echo ""
echo "✅ Application started successfully!"
echo ""
echo "🌐 Access URLs:"
echo "  Frontend:  http://localhost (or http://localhost:3000)"
echo "  Backend:   http://localhost:8000"
echo "  API Docs:  http://localhost:8000/docs"
echo "  WebSocket: ws://localhost:8001"
echo ""
echo "📝 Useful commands:"
echo "  View logs:     docker-compose logs -f [service-name]"
echo "  Stop all:      docker-compose down"
echo "  Restart:       docker-compose restart [service-name]"
echo ""
echo "📱 To add Telegram Bot:"
echo "  1. Set TELEGRAM_BOT_TOKEN in .env"
echo "  2. Restart telegram-bot service: docker-compose restart telegram-bot"