#!/bin/bash

# ====================================================================================
# SOLANA MAFIA - НАСТРОЙКА SSH КЛЮЧА
# ====================================================================================
# Автоматическая настройка SSH ключа для безопасного подключения к серверу
# ====================================================================================

set -e

# === CONFIGURATION ===
REMOTE_HOST="193.233.254.135"
REMOTE_USER="root"
SSH_KEY_PATH="$HOME/.ssh/id_rsa_solana_mafia"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE} $1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

generate_ssh_key() {
    header "СОЗДАНИЕ SSH КЛЮЧА"
    
    if [ -f "$SSH_KEY_PATH" ]; then
        warn "SSH ключ уже существует: $SSH_KEY_PATH"
        echo "Хотите создать новый? (y/N): "
        read -r response
        case "$response" in
            [yY]|[yY][eE][sS]|да|Да|ДА) 
                log "Создаем новый SSH ключ..."
                rm -f "$SSH_KEY_PATH" "$SSH_KEY_PATH.pub"
                ;;
            *) 
                log "Используем существующий ключ"
                return 0
                ;;
        esac
    fi
    
    log "Генерация SSH ключа для Solana Mafia..."
    ssh-keygen -t rsa -b 4096 -f "$SSH_KEY_PATH" -N "" -C "solana-mafia-$(date +%Y%m%d)"
    
    if [ -f "$SSH_KEY_PATH" ]; then
        log "SSH ключ создан успешно: $SSH_KEY_PATH"
    else
        error "Не удалось создать SSH ключ"
        exit 1
    fi
}

copy_key_to_server() {
    header "КОПИРОВАНИЕ КЛЮЧА НА СЕРВЕР"
    
    if [ ! -f "$SSH_KEY_PATH.pub" ]; then
        error "Публичный ключ не найден: $SSH_KEY_PATH.pub"
        exit 1
    fi
    
    log "Копирование публичного ключа на сервер $REMOTE_HOST..."
    
    # Try with ssh-copy-id first
    if command -v ssh-copy-id &> /dev/null; then
        log "Используем ssh-copy-id (потребуется пароль сервера)..."
        ssh-copy-id -i "$SSH_KEY_PATH.pub" "$REMOTE_USER@$REMOTE_HOST"
    else
        # Manual method
        log "Ручное копирование ключа (потребуется пароль сервера)..."
        cat "$SSH_KEY_PATH.pub" | ssh "$REMOTE_USER@$REMOTE_HOST" "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && chmod 700 ~/.ssh"
    fi
}

configure_ssh_client() {
    header "НАСТРОЙКА SSH КЛИЕНТА"
    
    local ssh_config="$HOME/.ssh/config"
    
    # Create SSH config entry
    if ! grep -q "Host solana-mafia" "$ssh_config" 2>/dev/null; then
        log "Добавление конфигурации в $ssh_config..."
        
        cat >> "$ssh_config" << EOF

# Solana Mafia Server
Host solana-mafia
    HostName $REMOTE_HOST
    User $REMOTE_USER
    IdentityFile $SSH_KEY_PATH
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
EOF
        
        chmod 600 "$ssh_config"
        log "SSH конфигурация добавлена"
    else
        log "SSH конфигурация уже существует"
    fi
}

test_ssh_connection() {
    header "ТЕСТИРОВАНИЕ SSH ПОДКЛЮЧЕНИЯ"
    
    log "Проверка подключения без пароля..."
    
    if ssh -i "$SSH_KEY_PATH" -o PasswordAuthentication=no -o ConnectTimeout=10 "$REMOTE_USER@$REMOTE_HOST" "echo 'SSH подключение работает!'" 2>/dev/null; then
        echo -e "${GREEN}✅ SSH ключ настроен успешно!${NC}"
        echo ""
        echo -e "${YELLOW}Теперь можно использовать:${NC}"
        echo "  ssh solana-mafia"
        echo "  ./panel.sh (будет использовать SSH ключ автоматически)"
        echo ""
        return 0
    else
        error "SSH подключение не работает"
        echo ""
        echo -e "${YELLOW}Возможные проблемы:${NC}"
        echo "1. Ключ не скопирован на сервер"
        echo "2. Неправильные разрешения на сервере"
        echo "3. SSH сервер не принимает ключи"
        echo ""
        echo -e "${YELLOW}Попробуйте:${NC}"
        echo "ssh -vvv -i $SSH_KEY_PATH $REMOTE_USER@$REMOTE_HOST"
        exit 1
    fi
}

main() {
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║                      НАСТРОЙКА SSH КЛЮЧА ДЛЯ SOLANA MAFIA                   ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    log "Сервер: $REMOTE_HOST"
    log "Пользователь: $REMOTE_USER"
    log "SSH ключ: $SSH_KEY_PATH"
    echo ""
    
    # Check if we already have a working SSH key
    if ssh -i "$SSH_KEY_PATH" -o PasswordAuthentication=no -o ConnectTimeout=5 "$REMOTE_USER@$REMOTE_HOST" "echo 'test'" &>/dev/null; then
        echo -e "${GREEN}✅ SSH ключ уже настроен и работает!${NC}"
        echo ""
        echo -e "${YELLOW}Можете использовать:${NC}"
        echo "  ./panel.sh"
        echo "  ssh solana-mafia"
        exit 0
    fi
    
    # Generate SSH key
    generate_ssh_key
    
    # Copy key to server
    copy_key_to_server
    
    # Configure SSH client
    configure_ssh_client
    
    # Test connection
    test_ssh_connection
    
    echo -e "${GREEN}🎉 SSH ключ успешно настроен!${NC}"
    echo ""
    echo -e "${YELLOW}Следующие шаги:${NC}"
    echo "1. Запустите: ${BLUE}./panel.sh${NC}"
    echo "2. Выберите: ${BLUE}5 → Настройка удаленного сервера${NC}"
    echo "3. CLI автоматически использует SSH ключ вместо пароля"
}

main "$@"