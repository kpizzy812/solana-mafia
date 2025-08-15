# 🌐 КОНФИГУРАЦИЯ САЙТА

## Быстрая смена IP/домена

**Для смены IP адреса или домена отредактируй в 2 файлах:**

### 1. В файле `.env.prod`:
```bash
SITE_DOMAIN=193.233.254.135                                 # ← Для backend
CORS_ORIGINS=http://193.233.254.135:3000,http://193.233.254.135  # ← CORS
```

### 2. В файле `docker-compose.prod.yml` (секция frontend args):
```yaml
- NEXT_PUBLIC_API_URL=http://193.233.254.135      # ← Frontend API (БЕЗ /api/v1!)
- NEXT_PUBLIC_WS_URL=ws://193.233.254.135:8001/ws # ← Frontend WebSocket
```

### Примеры замены:

**Для домена:**
```bash
SITE_DOMAIN=solanmafia.com
CORS_ORIGINS=http://solanmafia.com:3000,http://solanmafia.com
# В docker-compose.prod.yml:
- NEXT_PUBLIC_API_URL=http://solanmafia.com      # БЕЗ /api/v1!
- NEXT_PUBLIC_WS_URL=ws://solanmafia.com:8001/ws
```

**Для HTTPS домена:**
```bash
SITE_DOMAIN=solanmafia.com  
CORS_ORIGINS=https://solanmafia.com:3000,https://solanmafia.com
# В docker-compose.prod.yml:
- NEXT_PUBLIC_API_URL=https://solanmafia.com     # БЕЗ /api/v1!
- NEXT_PUBLIC_WS_URL=wss://solanmafia.com:8001/ws
```

## После изменения

1. Синхронизируй:
```bash
./solana-mafia-cli.sh sync
```

2. Пересобери frontend:
```bash
./solana-mafia-cli.sh prod-rebuild
```

Или только frontend:
```bash
ssh solana-mafia "cd /opt/solana-mafia && docker-compose -f docker-compose.prod.yml build --no-cache frontend && docker-compose -f docker-compose.prod.yml up -d frontend"
```

## Что автоматически изменится:

✅ API URL: `http://{SITE_URL}/api/v1`  
✅ WebSocket URL: `ws://{SITE_URL}:8001/ws`  
✅ CORS origins: `http://{SITE_URL}:3000, http://{SITE_URL}`  
✅ Все ссылки в приложении  

## SSL/HTTPS

Для домена с SSL сертификатом:

1. Измени `SITE_URL` на домен
2. В `nginx.prod.conf` раскомментируй SSL секцию
3. Добавь сертификаты в `./ssl/` директорию
4. В docker-compose.prod.yml верни `"443:443"` порт

---

**Все централизовано! Одна строка = полная смена конфигурации 🎯**