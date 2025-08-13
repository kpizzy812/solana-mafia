#!/bin/bash

# ====================================================================================
# SOLANA MAFIA - COMPREHENSIVE CLI MANAGEMENT TOOL
# ====================================================================================
# Универсальный CLI для управления проектом Solana Mafia
# Поддерживает локальную разработку и production деплой на хостинг
# ====================================================================================

set -e

# === CONFIGURATION ===
REMOTE_HOST="193.233.254.135"
REMOTE_USER="root"
REMOTE_PASSWORD="XsA1ED4HSp37cKB"
REMOTE_DIR="/opt/solana-mafia"
SSH_KEY_FILE="$HOME/.ssh/id_rsa_solana_mafia"
SSH_ALIAS="solana-mafia"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# === UTILITY FUNCTIONS ===
log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

header() {
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN} $1${NC}"
    echo -e "${CYAN}========================================${NC}"
}

# Check if running in project directory
check_project_dir() {
    if [ ! -f "package.json" ] || [ ! -f "Anchor.toml" ]; then
        error "Этот скрипт должен запускаться из корневой директории проекта Solana Mafia"
        exit 1
    fi
}

# Check SSH connection method
check_ssh_method() {
    # Try SSH alias first (recommended)
    if ssh -o PasswordAuthentication=no -o StrictHostKeyChecking=no -o ConnectTimeout=5 "$SSH_ALIAS" "echo 'SSH alias works'" 2>/dev/null; then
        USE_SSH_KEY=true
        USE_SSH_ALIAS=true
        log "Используется SSH алиас '$SSH_ALIAS' для подключения"
        return 0
    fi
    
    # Try specific SSH key
    if [ -f "$SSH_KEY_FILE" ]; then
        if ssh -i "$SSH_KEY_FILE" -o PasswordAuthentication=no -o StrictHostKeyChecking=no -o ConnectTimeout=5 "$REMOTE_USER@$REMOTE_HOST" "echo 'SSH key works'" 2>/dev/null; then
            USE_SSH_KEY=true
            USE_SSH_ALIAS=false
            log "Используется SSH ключ '$SSH_KEY_FILE' для подключения"
            return 0
        fi
    fi
    
    # Try default SSH key
    if ssh -o PasswordAuthentication=no -o StrictHostKeyChecking=no -o ConnectTimeout=5 "$REMOTE_USER@$REMOTE_HOST" "echo 'SSH key works'" 2>/dev/null; then
        USE_SSH_KEY=true
        USE_SSH_ALIAS=false
        log "Используется SSH ключ по умолчанию для подключения"
        return 0
    fi
    
    # Fallback to password with sshpass
    if command -v sshpass &> /dev/null; then
        USE_SSH_KEY=false
        USE_SSH_ALIAS=false
        log "Используется пароль с sshpass для подключения"
        return 0
    fi
    
    # Neither method available
    error "Не найдены способы подключения к серверу."
    echo ""
    echo -e "${YELLOW}Доступные варианты:${NC}"
    echo "1. Настроить SSH ключ (рекомендуется):"
    echo "   ssh-keygen -t rsa -b 4096"
    echo "   ssh-copy-id $REMOTE_USER@$REMOTE_HOST"
    echo ""
    echo "2. Установить sshpass:"
    echo "   macOS: brew install hudochenkov/sshpass/sshpass"
    echo "   Ubuntu: sudo apt-get install sshpass"
    echo ""
    exit 1
}

# Execute command on remote server
remote_exec() {
    local cmd="$1"
    
    if [ "$USE_SSH_KEY" = true ]; then
        if [ "$USE_SSH_ALIAS" = true ]; then
            ssh -o StrictHostKeyChecking=no "$SSH_ALIAS" "$cmd"
        elif [ -f "$SSH_KEY_FILE" ]; then
            ssh -i "$SSH_KEY_FILE" -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_HOST" "$cmd"
        else
            ssh -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_HOST" "$cmd"
        fi
    else
        sshpass -p "$REMOTE_PASSWORD" ssh -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_HOST" "$cmd"
    fi
}

# Copy file to remote server
remote_copy() {
    local local_file="$1"
    local remote_file="$2"
    
    if [ "$USE_SSH_KEY" = true ]; then
        if [ "$USE_SSH_ALIAS" = true ]; then
            scp -o StrictHostKeyChecking=no "$local_file" "$SSH_ALIAS:$remote_file"
        elif [ -f "$SSH_KEY_FILE" ]; then
            scp -i "$SSH_KEY_FILE" -o StrictHostKeyChecking=no "$local_file" "$REMOTE_USER@$REMOTE_HOST:$remote_file"
        else
            scp -o StrictHostKeyChecking=no "$local_file" "$REMOTE_USER@$REMOTE_HOST:$remote_file"
        fi
    else
        sshpass -p "$REMOTE_PASSWORD" scp -o StrictHostKeyChecking=no "$local_file" "$REMOTE_USER@$REMOTE_HOST:$remote_file"
    fi
}

# Rsync files to remote server
remote_sync() {
    local local_dir="$1"
    local remote_dir="$2"
    local exclude_file="$3"
    
    if [ "$USE_SSH_KEY" = true ]; then
        if [ "$USE_SSH_ALIAS" = true ]; then
            rsync -avz --delete --exclude-from="$exclude_file" --progress "$local_dir" "$SSH_ALIAS:$remote_dir"
        elif [ -f "$SSH_KEY_FILE" ]; then
            rsync -avz --delete --exclude-from="$exclude_file" --progress -e "ssh -i $SSH_KEY_FILE" "$local_dir" "$REMOTE_USER@$REMOTE_HOST:$remote_dir"
        else
            rsync -avz --delete --exclude-from="$exclude_file" --progress "$local_dir" "$REMOTE_USER@$REMOTE_HOST:$remote_dir"
        fi
    else
        sshpass -p "$REMOTE_PASSWORD" rsync -avz --delete --exclude-from="$exclude_file" --progress "$local_dir" "$REMOTE_USER@$REMOTE_HOST:$remote_dir"
    fi
}

# === SYNC FUNCTIONS ===
sync_to_remote() {
    header "СИНХРОНИЗАЦИЯ С УДАЛЕННЫМ СЕРВЕРОМ"
    
    check_ssh_method
    
    log "Синхронизация файлов проекта на $REMOTE_HOST..."
    
    # Create remote directory if it doesn't exist
    remote_exec "mkdir -p $REMOTE_DIR"
    
    # Sync files using rsync with exclusions
    remote_sync "./" "$REMOTE_DIR/" ".rsyncignore"
    
    # Copy production environment file
    if [ -f ".env.prod" ]; then
        log "Копирование production environment файла..."
        remote_copy ".env.prod" "$REMOTE_DIR/.env.prod"
    else
        warn ".env.prod файл не найден. Создайте его из .env.prod.example"
    fi
    
    success "Синхронизация завершена успешно"
}

# === LOCAL DEVELOPMENT FUNCTIONS ===
dev_start() {
    header "ЗАПУСК ЛОКАЛЬНОЙ РАЗРАБОТКИ"
    
    log "Запуск контейнеров для разработки..."
    docker-compose -f docker-compose.dev.yml up -d --build
    
    log "Ожидание готовности сервисов..."
    sleep 10
    
    log "Статус сервисов:"
    docker-compose -f docker-compose.dev.yml ps
    
    success "Локальная разработка запущена"
    log "Frontend: http://localhost:3000"
    log "Backend API: http://localhost:8000/docs"
    log "WebSocket: ws://localhost:8001"
}

dev_stop() {
    header "ОСТАНОВКА ЛОКАЛЬНОЙ РАЗРАБОТКИ"
    
    log "Остановка контейнеров разработки..."
    docker-compose -f docker-compose.dev.yml down
    
    success "Локальная разработка остановлена"
}

dev_restart() {
    header "ПЕРЕЗАПУСК ЛОКАЛЬНОЙ РАЗРАБОТКИ"
    
    dev_stop
    sleep 2
    dev_start
}

dev_logs() {
    local service="$1"
    header "ЛОГИ ЛОКАЛЬНОЙ РАЗРАБОТКИ"
    
    if [ -n "$service" ]; then
        log "Просмотр логов сервиса: $service"
        docker-compose -f docker-compose.dev.yml logs -f "$service"
    else
        log "Просмотр логов всех сервисов"
        docker-compose -f docker-compose.dev.yml logs -f
    fi
}

# === PRODUCTION FUNCTIONS ===
prod_deploy() {
    header "ДЕПЛОЙ НА PRODUCTION СЕРВЕР"
    
    # Initialize SSH connection method
    check_ssh_method
    
    # First sync files
    sync_to_remote
    
    log "Деплой приложения на удаленном сервере..."
    
    # Deploy on remote server
    remote_exec "cd $REMOTE_DIR && docker-compose -f docker-compose.prod.yml down || true"
    remote_exec "cd $REMOTE_DIR && docker-compose -f docker-compose.prod.yml pull || true"
    remote_exec "cd $REMOTE_DIR && docker-compose -f docker-compose.prod.yml build --no-cache"
    remote_exec "cd $REMOTE_DIR && docker-compose -f docker-compose.prod.yml up -d"
    
    log "Ожидание готовности сервисов..."
    sleep 30
    
    log "Проверка статуса сервисов на удаленном сервере..."
    remote_exec "cd $REMOTE_DIR && docker-compose -f docker-compose.prod.yml ps"
    
    success "Production деплой завершен успешно"
    log "Приложение доступно по адресу: http://$REMOTE_HOST"
}

prod_start() {
    header "ЗАПУСК PRODUCTION СЕРВИСОВ"
    
    check_ssh_method
    log "Запуск production контейнеров на удаленном сервере..."
    remote_exec "cd $REMOTE_DIR && docker-compose -f docker-compose.prod.yml up -d"
    
    success "Production сервисы запущены"
}

prod_start_with_telegram() {
    header "ЗАПУСК PRODUCTION СЕРВИСОВ (С TELEGRAM BOT)"
    
    check_ssh_method
    log "Запуск production контейнеров включая Telegram бот..."
    remote_exec "cd $REMOTE_DIR && docker-compose -f docker-compose.prod.yml --profile telegram up -d"
    
    success "Production сервисы запущены с Telegram ботом"
}

prod_stop() {
    header "ОСТАНОВКА PRODUCTION СЕРВИСОВ"
    
    check_ssh_method
    log "Остановка production контейнеров на удаленном сервере..."
    remote_exec "cd $REMOTE_DIR && docker-compose -f docker-compose.prod.yml down"
    
    success "Production сервисы остановлены"
}

prod_restart() {
    header "ПЕРЕЗАПУСК PRODUCTION СЕРВИСОВ"
    
    prod_stop
    sleep 5
    prod_start
}

prod_rebuild() {
    header "ПЕРЕСБОРКА PRODUCTION КОНТЕЙНЕРОВ"
    
    check_ssh_method
    log "Остановка и удаление старых контейнеров..."
    remote_exec "cd $REMOTE_DIR && docker-compose -f docker-compose.prod.yml down"
    
    log "Пересборка всех образов..."
    remote_exec "cd $REMOTE_DIR && docker-compose -f docker-compose.prod.yml build --no-cache"
    
    log "Запуск обновленных контейнеров..."
    remote_exec "cd $REMOTE_DIR && docker-compose -f docker-compose.prod.yml up -d"
    
    success "Production контейнеры пересобраны и запущены"
}

prod_logs() {
    local service="$1"
    header "ПРОСМОТР PRODUCTION ЛОГОВ"
    
    check_ssh_method
    if [ -n "$service" ]; then
        log "Просмотр логов сервиса: $service"
        remote_exec "cd $REMOTE_DIR && docker-compose -f docker-compose.prod.yml logs --tail=100 -f $service"
    else
        log "Просмотр логов всех сервисов (последние 50 строк каждого)"
        remote_exec "cd $REMOTE_DIR && docker-compose -f docker-compose.prod.yml logs --tail=50"
    fi
}

# === DATABASE FUNCTIONS ===
db_clean() {
    local env="${1:-dev}"
    header "ОЧИСТКА БАЗЫ ДАННЫХ ($env)"
    
    if [ "$env" = "prod" ]; then
        check_ssh_method
        warn "ВНИМАНИЕ! Это удалит все данные в production базе данных!"
        read -p "Вы уверены? (yes/no): " confirm
        if [ "$confirm" != "yes" ]; then
            log "Операция отменена"
            return
        fi
        
        log "Очистка production базы данных..."
        remote_exec "cd $REMOTE_DIR && docker-compose -f docker-compose.prod.yml exec -T postgres psql -U solana_mafia -d solana_mafia_db -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'"
        remote_exec "cd $REMOTE_DIR && docker-compose -f docker-compose.prod.yml exec -T backend python -m alembic upgrade head"
    else
        log "Очистка development базы данных..."
        docker-compose -f docker-compose.dev.yml exec -T postgres psql -U solana_mafia -d solana_mafia_db -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
        docker-compose -f docker-compose.dev.yml exec -T backend python -m alembic upgrade head
    fi
    
    success "База данных очищена и миграции применены"
}

db_migrate() {
    local env="${1:-dev}"
    local action="${2:-upgrade}"
    header "ВЫПОЛНЕНИЕ МИГРАЦИЙ БАЗЫ ДАННЫХ ($env)"
    
    if [ "$env" = "prod" ]; then
        check_ssh_method
        log "Выполнение миграций на production сервере..."
        remote_exec "cd $REMOTE_DIR && docker-compose -f docker-compose.prod.yml exec -T backend python -m alembic $action head"
    else
        log "Выполнение миграций для development..."
        docker-compose -f docker-compose.dev.yml exec backend python -m alembic $action head
    fi
    
    success "Миграции выполнены"
}

db_create_migration() {
    local name="$1"
    header "СОЗДАНИЕ НОВОЙ МИГРАЦИИ"
    
    if [ -z "$name" ]; then
        error "Укажите имя миграции: $0 db-create-migration <название>"
        exit 1
    fi
    
    log "Создание миграции: $name"
    docker-compose -f docker-compose.dev.yml exec backend python -m alembic revision --autogenerate -m "$name"
    
    success "Миграция создана"
}

# === STATUS FUNCTIONS ===
status() {
    header "СТАТУС СИСТЕМЫ"
    
    log "=== ЛОКАЛЬНЫЕ СЕРВИСЫ ==="
    if docker-compose -f docker-compose.dev.yml ps 2>/dev/null | grep -q "Up"; then
        docker-compose -f docker-compose.dev.yml ps
    else
        warn "Локальные сервисы не запущены"
    fi
    
    log ""
    log "=== PRODUCTION СЕРВИСЫ ==="
    check_ssh_method
    if remote_exec "cd $REMOTE_DIR && docker-compose -f docker-compose.prod.yml ps 2>/dev/null" | grep -q "Up"; then
        remote_exec "cd $REMOTE_DIR && docker-compose -f docker-compose.prod.yml ps"
    else
        warn "Production сервисы недоступны или не запущены"
    fi
}

# === MONITORING FUNCTIONS ===
monitor() {
    local env="${1:-prod}"
    header "МОНИТОРИНГ СИСТЕМЫ ($env)"
    
    if [ "$env" = "prod" ]; then
        check_ssh_method
        log "Статус сервисов:"
        remote_exec "cd $REMOTE_DIR && docker-compose -f docker-compose.prod.yml ps"
        
        echo ""
        log "Использование ресурсов:"
        remote_exec "docker stats --no-stream --format 'table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}'"
        
        echo ""
        log "Дисковое пространство:"
        remote_exec "df -h /"
    else
        log "Локальный мониторинг:"
        docker-compose -f docker-compose.dev.yml ps
        echo ""
        docker stats --no-stream --format 'table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}'
    fi
}

# === BACKUP FUNCTIONS ===
backup_db() {
    local env="${1:-prod}"
    local backup_file="backup_$(date +%Y%m%d_%H%M%S).sql"
    header "СОЗДАНИЕ РЕЗЕРВНОЙ КОПИИ БД ($env)"
    
    if [ "$env" = "prod" ]; then
        check_ssh_method
        log "Создание резервной копии production БД..."
        remote_exec "cd $REMOTE_DIR && docker-compose -f docker-compose.prod.yml exec -T postgres pg_dump -U solana_mafia solana_mafia_db > /tmp/$backup_file"
        
        if [ "$USE_SSH_KEY" = true ]; then
            scp "$REMOTE_USER@$REMOTE_HOST:/tmp/$backup_file" "./backups/"
        else
            sshpass -p "$REMOTE_PASSWORD" scp "$REMOTE_USER@$REMOTE_HOST:/tmp/$backup_file" "./backups/"
        fi
        
        remote_exec "rm /tmp/$backup_file"
    else
        log "Создание резервной копии development БД..."
        mkdir -p backups
        docker-compose -f docker-compose.dev.yml exec -T postgres pg_dump -U solana_mafia solana_mafia_db > "backups/$backup_file"
    fi
    
    success "Резервная копия создана: backups/$backup_file"
}

# === SETUP FUNCTIONS ===
setup_remote() {
    header "НАСТРОЙКА УДАЛЕННОГО СЕРВЕРА (Ubuntu 24)"
    
    # Initialize SSH connection method
    check_ssh_method
    
    log "Обновление системы..."
    remote_exec "apt-get update && apt-get upgrade -y"
    
    log "Установка базовых пакетов..."
    remote_exec "apt-get install -y curl wget git htop nano unzip rsync"
    
    log "Firewall отключен для простоты разработки..."
    
    log "Установка Docker..."
    remote_exec "curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh"
    remote_exec "systemctl enable docker"
    remote_exec "systemctl start docker"
    remote_exec "usermod -aG docker root"
    
    log "Установка Docker Compose v2..."
    remote_exec "curl -L \"https://github.com/docker/compose/releases/latest/download/docker-compose-\$(uname -s)-\$(uname -m)\" -o /usr/local/bin/docker-compose"
    remote_exec "chmod +x /usr/local/bin/docker-compose"
    remote_exec "ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose"
    
    log "Создание структуры директорий..."
    remote_exec "mkdir -p $REMOTE_DIR/{backups,logs,ssl,data/postgres,data/redis}"
    remote_exec "chown -R root:root $REMOTE_DIR"
    remote_exec "chmod -R 755 $REMOTE_DIR"
    
    log "Настройка логирования..."
    remote_exec "mkdir -p /var/log/solana-mafia"
    remote_exec "touch /var/log/solana-mafia/app.log"
    remote_exec "chmod 644 /var/log/solana-mafia/app.log"
    
    log "Настройка автоматической очистки Docker..."
    remote_exec "cat > /etc/cron.daily/docker-cleanup << 'EOF'
#!/bin/bash
# Clean up unused Docker images and containers
docker system prune -f
docker volume prune -f
EOF"
    remote_exec "chmod +x /etc/cron.daily/docker-cleanup"
    
    log "Настройка swap (если нет)..."
    remote_exec "if [ ! -f /swapfile ]; then
        fallocate -l 2G /swapfile
        chmod 600 /swapfile
        mkswap /swapfile
        swapon /swapfile
        echo '/swapfile none swap sw 0 0' >> /etc/fstab
    fi"
    
    log "Оптимизация системы для производительности..."
    remote_exec "echo 'vm.swappiness=10' >> /etc/sysctl.conf"
    remote_exec "echo 'net.core.rmem_max=16777216' >> /etc/sysctl.conf"
    remote_exec "echo 'net.core.wmem_max=16777216' >> /etc/sysctl.conf"
    remote_exec "sysctl -p"
    
    log "Создание systemd сервиса для автозапуска..."
    remote_exec "cat > /etc/systemd/system/solana-mafia.service << 'EOF'
[Unit]
Description=Solana Mafia Application
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$REMOTE_DIR
ExecStart=/usr/local/bin/docker-compose -f docker-compose.prod.yml up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose.prod.yml down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF"
    
    remote_exec "systemctl daemon-reload"
    remote_exec "systemctl enable solana-mafia.service"
    
    log "Проверка версий установленных компонентов..."
    remote_exec "docker --version"
    remote_exec "docker-compose --version"
    
    success "Сервер Ubuntu 24 полностью настроен для production!"
    log "Docker установлен, автозапуск настроен, firewall отключен"
    log "Теперь можно выполнить: ./sm deploy"
}

# === HELP FUNCTION ===
show_help() {
    echo -e "${CYAN}SOLANA MAFIA CLI - Инструмент управления проектом${NC}"
    echo ""
    echo -e "${YELLOW}ЛОКАЛЬНАЯ РАЗРАБОТКА:${NC}"
    echo "  dev-start              Запустить локальную разработку"
    echo "  dev-stop               Остановить локальную разработку"
    echo "  dev-restart            Перезапустить локальную разработку"
    echo "  dev-logs [service]     Просмотр логов (опционально для конкретного сервиса)"
    echo ""
    echo -e "${YELLOW}PRODUCTION ДЕПЛОЙ:${NC}"
    echo "  sync                   Синхронизировать файлы с сервером"
    echo "  deploy                 Полный деплой на production (sync + build + start)"
    echo "  prod-start             Запустить production сервисы"
    echo "  prod-start-telegram    Запустить production сервисы + Telegram бот"
    echo "  prod-stop              Остановить production сервисы"
    echo "  prod-restart           Перезапустить production сервисы"
    echo "  prod-rebuild           Пересобрать и запустить production контейнеры"
    echo "  prod-logs [service]    Просмотр production логов"
    echo ""
    echo -e "${YELLOW}УПРАВЛЕНИЕ БАЗОЙ ДАННЫХ:${NC}"
    echo "  db-clean [dev|prod]              Очистить базу данных"
    echo "  db-migrate [dev|prod] [upgrade]  Выполнить миграции"
    echo "  db-create-migration <name>       Создать новую миграцию"
    echo ""
    echo -e "${YELLOW}МОНИТОРИНГ И СТАТУС:${NC}"
    echo "  status                 Показать статус всех сервисов"
    echo "  monitor [dev|prod]     Мониторинг ресурсов"
    echo "  backup-db [dev|prod]   Создать резервную копию БД"
    echo ""
    echo -e "${YELLOW}НАСТРОЙКА:${NC}"
    echo "  setup-remote           Настроить удаленный сервер"
    echo "  panel                  Запустить интерактивную панель управления"
    echo "  help                   Показать эту справку"
    echo ""
    echo -e "${YELLOW}ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ:${NC}"
    echo "  $0 panel                        # Интерактивная панель (рекомендуется)"
    echo "  $0 dev-start                    # Запуск локальной разработки"
    echo "  $0 deploy                       # Полный деплой на production"
    echo "  $0 prod-logs backend            # Просмотр логов backend сервиса"
    echo "  $0 db-clean prod                # Очистка production БД"
    echo "  $0 monitor prod                 # Мониторинг production"
}

# === MAIN COMMAND HANDLER ===
main() {
    case "${1:-help}" in
        # Local development
        "dev-start")
            check_project_dir
            dev_start
            ;;
        "dev-stop")
            check_project_dir
            dev_stop
            ;;
        "dev-restart")
            check_project_dir
            dev_restart
            ;;
        "dev-logs")
            check_project_dir
            dev_logs "$2"
            ;;
            
        # Production deployment
        "sync")
            check_project_dir
            sync_to_remote
            ;;
        "deploy")
            check_project_dir
            prod_deploy
            ;;
        "prod-start")
            prod_start
            ;;
        "prod-start-telegram")
            prod_start_with_telegram
            ;;
        "prod-stop")
            prod_stop
            ;;
        "prod-restart")
            prod_restart
            ;;
        "prod-rebuild")
            prod_rebuild
            ;;
        "prod-logs")
            prod_logs "$2"
            ;;
            
        # Database management
        "db-clean")
            check_project_dir
            db_clean "$2"
            ;;
        "db-migrate")
            check_project_dir
            db_migrate "$2" "$3"
            ;;
        "db-create-migration")
            check_project_dir
            db_create_migration "$2"
            ;;
            
        # Status and monitoring
        "status")
            status
            ;;
        "monitor")
            monitor "$2"
            ;;
        "backup-db")
            check_project_dir
            backup_db "$2"
            ;;
            
        # Setup
        "setup-remote")
            setup_remote
            ;;
            
        # Interactive panel
        "panel"|"-i"|"--interactive")
            if [ -f "./panel.sh" ]; then
                exec ./panel.sh
            else
                error "Интерактивная панель не найдена (panel.sh)"
                exit 1
            fi
            ;;
            
        # Help
        "help"|"-h"|"--help")
            show_help
            ;;
            
        *)
            error "Неизвестная команда: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"