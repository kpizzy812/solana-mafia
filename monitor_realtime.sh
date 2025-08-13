#!/bin/bash
echo "🎯 Запуск real-time мониторинга для новой транзакции..."
echo "Время старта: $(date)"
echo "=========================================="

# Мониторинг логов индексера для real-time событий
docker compose logs -f indexer 2>&1 | grep -E "(logsNotification|BusinessCreated|handle_logs|Processing real-time|Found.*events)" &
PID1=$!

# Мониторинг логов WebSocket сервиса  
docker compose logs -f websocket 2>&1 | grep -E "(notification|websocket|client|Business)" &
PID2=$!

# Мониторинг логов основного бэкенда
docker compose logs -f backend 2>&1 | grep -E "(Business|transaction|event)" &
PID3=$!

echo "Мониторинг запущен. PIDs: $PID1, $PID2, $PID3"
echo "Для остановки: kill $PID1 $PID2 $PID3"

# Ждем прерывания
trap "kill $PID1 $PID2 $PID3 2>/dev/null; echo 'Мониторинг остановлен'; exit" INT TERM

wait