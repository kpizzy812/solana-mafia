#!/bin/bash

echo "⏹️  Stopping Solana Mafia application..."

# Stop all services
docker-compose down

echo "✅ All services stopped successfully!"
echo ""
echo "💡 To start again, run: ./start.sh"
echo "🗑️  To remove all data, run: docker-compose down -v"