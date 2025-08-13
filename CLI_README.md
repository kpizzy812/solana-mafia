# Solana Mafia CLI - Руководство по использованию

Комплексный инструмент командной строки для управления проектом Solana Mafia в режиме разработки и production деплоя.

## 🚀 Быстрый старт

### Интерактивная панель управления (рекомендуется)

```bash
# Запуск красивой интерактивной панели с меню
./panel.sh
# или короткая команда:
./p

# Также можно запустить через основной CLI:
./sm panel
```

**🎨 Возможности панели:**
- Красивый TUI интерфейс с цветами и ASCII логотипом
- Навигация по меню с помощью цифр
- Автоматическое возвращение в меню после команд
- Статус-бар с проверкой сервисов в реальном времени
- Подтверждения для критичных операций
- Health Check системы
- Справка по использованию

### Установка зависимостей

**macOS:**
```bash
# Установка sshpass для удаленного доступа
brew install hudochenkov/sshpass/sshpass
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install sshpass rsync docker.io docker-compose
```

**CentOS/RHEL:**
```bash
sudo yum install sshpass rsync docker docker-compose
```

### Настройка окружения

1. **Скопируйте конфигурационные файлы:**
```bash
# Для локальной разработки
cp .env.example .env

# Для production (отредактируйте значения!)
cp .env.prod.example .env.prod
```

2. **Настройте production переменные в `.env.prod`:**
   - `POSTGRES_PASSWORD` - надежный пароль БД
   - `REDIS_PASSWORD` - пароль для Redis
   - `SECRET_KEY` - секретный ключ приложения
   - `SOLANA_RPC_URL` - mainnet RPC endpoint
   - `ADMIN_WALLETS` - адреса admin кошельков

## 📋 Способы использования

### 🎨 Интерактивная панель (рекомендуется для новичков)

```bash
./p                    # Короткий запуск панели
./panel.sh             # Полное имя панели
./sm panel             # Через основной CLI
```

**Преимущества панели:**
- Все команды в одном меню с описанием
- Статус сервисов в реальном времени
- Автоматические подтверждения критичных операций
- Возврат в меню после каждой команды
- Встроенная справка и Health Check

### ⚡ Быстрые CLI команды (для опытных пользователей)

```bash
./sm <команда>         # Основной CLI
# или
./solana-mafia-cli.sh <команда>
```

## 📋 Команды CLI

### Локальная разработка

```bash
# Запуск всех сервисов для разработки
./solana-mafia-cli.sh dev-start
# или коротко:
./sm dev-start

# Остановка сервисов разработки
./sm dev-stop

# Перезапуск сервисов
./sm dev-restart

# Просмотр логов всех сервисов
./sm dev-logs

# Просмотр логов конкретного сервиса
./sm dev-logs backend
./sm dev-logs frontend
./sm dev-logs postgres
./sm dev-logs redis
```

**После запуска доступны:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/docs  
- WebSocket: ws://localhost:8001

### Production деплой

```bash
# ОБЯЗАТЕЛЬНО! Первоначальная настройка удаленного сервера (Ubuntu 24)
./sm setup-remote

# Полный деплой (синхронизация + сборка + запуск)
./sm deploy

# Только синхронизация файлов
./sm sync

# Управление production сервисами
./sm prod-start             # Запуск основных сервисов
./sm prod-start-telegram    # Запуск с Telegram ботом
./sm prod-stop              # Остановка
./sm prod-restart           # Перезапуск
./sm prod-rebuild           # Пересборка и запуск

# Просмотр production логов
./sm prod-logs              # Все сервисы
./sm prod-logs backend      # Конкретный сервис
./sm prod-logs nginx        # Веб-сервер
```

**⚠️ ВАЖНО:** На хостинге развертывается только веб-приложение (backend + frontend + база данных). Смарт-контракты остаются в блокчейне и разрабатываются локально с помощью Anchor framework.

### Управление базой данных

```bash
# Выполнение миграций
./sm db-migrate dev         # Для разработки
./sm db-migrate prod        # Для production

# Создание новой миграции
./sm db-create-migration "add_new_feature"

# Очистка базы данных (ОСТОРОЖНО!)
./sm db-clean dev           # Разработка
./sm db-clean prod          # Production (требует подтверждения)

# Создание резервной копии
./sm backup-db dev          # Локальная БД
./sm backup-db prod         # Production БД
```

### Мониторинг и статус

```bash
# Общий статус всех сервисов
./sm status

# Мониторинг ресурсов
./sm monitor dev            # Локальные сервисы
./sm monitor prod           # Production сервисы

# Справка по командам
./sm help
```

## 🏗️ Архитектура системы

### Подготовка хостинга

CLI автоматически настраивает сервер Ubuntu 24 через команду `setup-remote`:

**Что устанавливается:**
- Docker и Docker Compose v2
- UFW Firewall с настройками портов (22, 80, 443, 8000, 8001)
- Fail2ban для защиты от брute-force атак
- Swap файл (2GB) для стабильности работы
- Автоматическая очистка Docker образов (cron)
- Systemd сервис для автозапуска приложения
- Оптимизация сетевых параметров

**Структура директорий:**
- `/opt/solana-mafia/` - основной код приложения
- `/opt/solana-mafia/backups/` - резервные копии БД
- `/opt/solana-mafia/logs/` - логи приложения
- `/opt/solana-mafia/ssl/` - SSL сертификаты (для будущего домена)
- `/var/log/solana-mafia/` - системные логи

### Сервисы проекта

**Development (docker-compose.dev.yml):**
- `postgres` - База данных PostgreSQL
- `redis` - Кеш Redis  
- `backend` - FastAPI API сервер
- `frontend` - Next.js фронтенд

**Production (docker-compose.prod.yml):**
- `postgres` - База данных PostgreSQL
- `redis` - Кеш Redis
- `backend` - FastAPI API сервер (4 workers)
- `frontend` - Next.js фронтенд (optimized build)
- `indexer` - Сервис индексации blockchain событий
- `scheduler` - Планировщик автоматических выплат
- `websocket` - WebSocket сервер для real-time обновлений
- `telegram-bot` - Telegram бот сервис (опционально)
- `nginx` - Реверс-прокси и load balancer

### Конфигурация сервера

**Server details:**
- IP: 193.233.254.135
- User: root
- Директория проекта: `/opt/solana-mafia`

**Nginx routing:**
- `/` → Frontend (Next.js)
- `/api/` → Backend API
- `/ws/` → WebSocket server

## 🔧 Продвинутое использование

### Синхронизация файлов

CLI использует `rsync` с файлом исключений `.rsyncignore`. Исключаются:
- `node_modules/`, `target/`, `.git/`
- Логи и временные файлы
- Development скрипты и тесты
- Build артефакты

### Environment файлы

**Development (.env):**
- Использует localhost endpoints
- Отладочные настройки включены
- Простые пароли для dev БД

**Production (.env.prod):**
- Production-ready конфигурация
- Надежные пароли и секреты
- Mainnet RPC endpoints
- Оптимизированные настройки производительности

### Логи и мониторинг

```bash
# Просмотр логов с фильтрацией
./sm prod-logs backend | grep ERROR
./sm prod-logs nginx | tail -100

# Мониторинг в реальном времени
./sm prod-logs        # Следит за всеми логами
./sm monitor prod     # Показывает использование ресурсов
```

### Резервное копирование

```bash
# Автоматическое именование бэкапов с датой
./sm backup-db prod
# Создаст: backups/backup_20241201_143022.sql

# Восстановление из бэкапа (вручную)
docker-compose -f docker-compose.prod.yml exec -T postgres psql -U solana_mafia -d solana_mafia_db < backups/backup_20241201_143022.sql
```

## ⚠️ Важные замечания

### Безопасность

1. **Никогда не коммитьте .env.prod файлы в Git**
2. **Используйте надежные пароли в production**
3. **Регулярно создавайте резервные копии БД**
4. **Мониторьте логи на предмет ошибок и атак**

### Production деплой

1. **Рекомендуемый способ (через панель):**
```bash
./p                  # Запуск интерактивной панели
# В меню выберите:
# 5 → Настроить удаленный сервер (один раз)
# 6 → Полный деплой на production
```

2. **Через CLI команды:**
```bash
./sm setup-remote    # ОБЯЗАТЕЛЬНО! Настройка Ubuntu 24 сервера
# Отредактируйте .env.prod с правильными настройками
./sm deploy          # Полный деплой
```

3. **Обновление после изменений:**
```bash
./sm sync            # Быстрая синхронизация
./sm prod-restart    # Если нужен только перезапуск
./sm prod-rebuild    # Если изменились Dockerfile'ы
```

4. **Дополнительные опции:**
```bash
# Запуск с Telegram ботом (если настроен TELEGRAM_BOT_TOKEN в .env.prod)
./sm prod-start-telegram

# Проверка автозапуска при перезагрузке сервера
sudo systemctl status solana-mafia
```

5. **Проверка работоспособности:**
```bash
./sm status          # Проверить все сервисы
./sm monitor prod    # Мониторинг ресурсов
curl -f http://193.233.254.135/api/health  # Проверка API
```

### Устранение неполадок

**Если сервисы не запускаются:**
```bash
./sm prod-logs       # Проверить логи ошибок
./sm status          # Проверить статус
./sm prod-rebuild    # Пересобрать при проблемах с образами
```

**Если база данных недоступна:**
```bash
./sm prod-logs postgres
./sm db-migrate prod  # Применить миграции заново
```

**Проблемы с синхронизацией:**
- Проверьте доступность сервера: `ping 193.233.254.135`
- Проверьте sshpass: `sshpass -V`
- Убедитесь что файлы .rsyncignore корректны

## 📚 Дополнительные ресурсы

- [CLAUDE.md](./CLAUDE.md) - Подробная документация проекта
- [docker-compose.yml](./docker-compose.yml) - Полная production конфигурация
- [docker-compose.dev.yml](./docker-compose.dev.yml) - Development конфигурация
- [nginx.prod.conf](./nginx.prod.conf) - Production Nginx конфигурация

## 🆘 Поддержка

При возникновении проблем:

1. Проверьте логи: `./sm prod-logs` или `./sm dev-logs`
2. Проверьте статус: `./sm status`  
3. Убедитесь что все environment переменные настроены
4. Для production: проверьте доступность удаленного сервера

**Полезные команды для диагностики:**
```bash
# Проверка Docker
docker ps -a
docker-compose ps

# Проверка сети
curl -f http://localhost:8000/health    # Dev
curl -f http://193.233.254.135/api/health  # Prod

# Проверка логов
./sm prod-logs | grep -i error
./sm monitor prod
```

## 🎨 Интерактивная панель - подробнее

### Запуск панели

```bash
./p                # Самый короткий способ
./panel.sh         # Полное имя
./sm panel         # Через основной CLI
```

### Структура меню

**🏠 Локальная разработка (пункты 1-4):**
- Запуск/остановка/перезапуск dev окружения
- Просмотр логов с выбором конкретного сервиса

**🌐 Production деплой (пункты 5-8):**
- Настройка сервера (выполняется один раз)
- Полный деплой и управление сервисами
- Отдельная панель production с детальным управлением

**🗄️ Управление БД (пункты 9-12):**
- Миграции, резервные копии, создание миграций
- Отдельная панель БД с разделением dev/production

**📊 Мониторинг (пункты 13-16):**
- Статус сервисов, мониторинг ресурсов
- Health Check с детальной диагностикой
- Просмотр логов production с выбором сервиса

### Особенности интерфейса

**Цветовая схема:**
- 🟢 Зеленый - локальная разработка
- 🟣 Фиолетовый - production операции  
- 🟡 Желтый - база данных
- 🔵 Синий - мониторинг
- 🔴 Красный - критичные операции

**Безопасность:**
- Подтверждения для опасных операций (очистка БД, pересборка)
- Двойное подтверждение для production БД
- Автоматическая проверка требований перед запуском

**Удобство:**
- Статус-бар показывает состояние локальных и production сервисов
- Автовозврат в меню после выполнения команды
- Встроенная справка (пункт h)
- Health Check с детальной диагностикой (пункт 16)

**Навигация:**
- Используйте цифры для выбора пунктов меню
- `0` - возврат в предыдущее меню или выход
- `h` - справка в главном меню
- `Ctrl+C` - экстренный выход