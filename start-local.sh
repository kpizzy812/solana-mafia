#!/bin/bash

echo "🚀 Starting Solana Mafia development environment (local + Docker for services)..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

echo "📋 Starting Docker services (PostgreSQL + Redis)..."

# Start only database services
docker-compose -f docker-compose.dev.yml up -d postgres redis

echo "⏳ Waiting for services to be ready..."
sleep 5

# Check services status
echo "📊 Service Status:"
docker-compose -f docker-compose.dev.yml ps

echo ""
echo "✅ Database services started!"
echo ""
echo "🌐 Now you can:"
echo "  1. Start backend:  cd app/backend && python -m uvicorn app.main:app --reload"
echo "  2. Start frontend: cd app/frontend && npm run dev"
echo ""
echo "💾 Services running:"
echo "  - PostgreSQL: localhost:5432"
echo "  - Redis: localhost:6379"