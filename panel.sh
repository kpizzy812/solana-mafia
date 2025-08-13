#!/bin/bash

# ====================================================================================
# SOLANA MAFIA - ИНТЕРАКТИВНАЯ ПАНЕЛЬ УПРАВЛЕНИЯ
# ====================================================================================
# Красивый TUI интерфейс для управления проектом
# ====================================================================================

set -e

# === CONFIGURATION ===
CLI_SCRIPT="./solana-mafia-cli.sh"
REMOTE_HOST="193.233.254.135"

# === COLORS AND FORMATTING ===
# Basic colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
GRAY='\033[0;90m'
NC='\033[0m' # No Color

# Advanced colors
BRIGHT_GREEN='\033[1;32m'
BRIGHT_RED='\033[1;31m'
BRIGHT_BLUE='\033[1;34m'
BRIGHT_CYAN='\033[1;36m'
BRIGHT_YELLOW='\033[1;33m'

# Background colors
BG_BLACK='\033[40m'
BG_RED='\033[41m'
BG_GREEN='\033[42m'
BG_BLUE='\033[44m'

# === UTILITY FUNCTIONS ===
clear_screen() {
    clear
}

print_header() {
    echo -e "${BRIGHT_CYAN}
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║   ███████╗ ██████╗ ██╗      █████╗ ███╗   ██╗ █████╗     ███╗   ███╗ █████╗ ║
║   ██╔════╝██╔═══██╗██║     ██╔══██╗████╗  ██║██╔══██╗    ████╗ ████║██╔══██╗║
║   ███████╗██║   ██║██║     ███████║██╔██╗ ██║███████║    ██╔████╔██║███████║║
║   ╚════██║██║   ██║██║     ██╔══██║██║╚██╗██║██╔══██║    ██║╚██╔╝██║██╔══██║║
║   ███████║╚██████╔╝███████╗██║  ██║██║ ╚████║██║  ██║    ██║ ╚═╝ ██║██║  ██║║
║   ╚══════╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝    ╚═╝     ╚═╝╚═╝  ╚═╝║
║                                                                              ║
║                      ${WHITE}🎰 SOLANA MAFIA CONTROL PANEL 🎰${BRIGHT_CYAN}                      ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
}

print_separator() {
    echo -e "${GRAY}────────────────────────────────────────────────────────────────────────────${NC}"
}

print_status_bar() {
    echo -e "${BG_BLUE}${WHITE} STATUS BAR ${NC}"
    
    # Check local services
    local_status="❌"
    if docker-compose -f docker-compose.dev.yml ps 2>/dev/null | grep -q "Up"; then
        local_status="✅"
    fi
    
    # Check remote services  
    remote_status="❓"
    if timeout 5 bash -c "</dev/tcp/$REMOTE_HOST/80" 2>/dev/null; then
        remote_status="✅"
    else
        remote_status="❌"
    fi
    
    echo -e "${CYAN}🏠 Local Dev:${NC} $local_status   ${PURPLE}🌐 Production:${NC} $remote_status   ${YELLOW}📡 Server:${NC} $REMOTE_HOST"
    print_separator
}

wait_for_key() {
    echo ""
    echo -e "${GRAY}Нажмите любую клавишу для продолжения...${NC}"
    read -n 1 -s
}

confirm_action() {
    local message="$1"
    echo -e "${YELLOW}⚠️  $message${NC}"
    echo -e "${WHITE}Вы уверены? (y/N):${NC}"
    read -r response
    case "$response" in
        [yY]|[yY][eE][sS]|да|Да|ДА) return 0 ;;
        *) return 1 ;;
    esac
}

execute_command() {
    local cmd="$1"
    local description="$2"
    
    echo -e "\n${BG_GREEN}${WHITE} ВЫПОЛНЯЕТСЯ: $description ${NC}\n"
    
    if $CLI_SCRIPT $cmd; then
        echo -e "\n${BRIGHT_GREEN}✅ Команда выполнена успешно!${NC}"
    else
        echo -e "\n${BRIGHT_RED}❌ Ошибка при выполнении команды!${NC}"
    fi
    
    wait_for_key
}

# === MENU FUNCTIONS ===
show_main_menu() {
    clear_screen
    print_header
    print_status_bar
    
    echo -e "${WHITE}╔═══════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${WHITE}║                              ГЛАВНОЕ МЕНЮ                                ║${NC}"
    echo -e "${WHITE}╠═══════════════════════════════════════════════════════════════════════════╣${NC}"
    echo -e "${WHITE}║                                                                           ║${NC}"
    echo -e "${WHITE}║  ${BRIGHT_GREEN}🏠 ЛОКАЛЬНАЯ РАЗРАБОТКА${WHITE}                                                  ║${NC}"
    echo -e "${WHITE}║  ${GREEN}1.${NC} Запустить dev окружение          ${GREEN}2.${NC} Остановить dev окружение        ${WHITE}║${NC}"
    echo -e "${WHITE}║  ${GREEN}3.${NC} Перезапустить dev сервисы        ${GREEN}4.${NC} Просмотр логов (dev)            ${WHITE}║${NC}"
    echo -e "${WHITE}║                                                                           ║${NC}"
    echo -e "${WHITE}║  ${BRIGHT_PURPLE}🌐 PRODUCTION ДЕПЛОЙ${WHITE}                                                     ║${NC}"
    echo -e "${WHITE}║  ${PURPLE}5.${NC} Настроить удаленный сервер       ${PURPLE}6.${NC} Полный деплой на production     ${WHITE}║${NC}"
    echo -e "${WHITE}║  ${PURPLE}7.${NC} Синхронизация файлов             ${PURPLE}8.${NC} Production панель управления    ${WHITE}║${NC}"
    echo -e "${WHITE}║                                                                           ║${NC}"
    echo -e "${WHITE}║  ${BRIGHT_YELLOW}🗄️  УПРАВЛЕНИЕ БАЗОЙ ДАННЫХ${WHITE}                                             ║${NC}"
    echo -e "${WHITE}║  ${YELLOW}9.${NC} Миграции БД                     ${YELLOW}10.${NC} Создать резервную копию        ${WHITE}║${NC}"
    echo -e "${WHITE}║  ${YELLOW}11.${NC} Создать миграцию                ${YELLOW}12.${NC} База данных панель             ${WHITE}║${NC}"
    echo -e "${WHITE}║                                                                           ║${NC}"
    echo -e "${WHITE}║  ${BRIGHT_BLUE}📊 МОНИТОРИНГ И СТАТУС${WHITE}                                                   ║${NC}"
    echo -e "${WHITE}║  ${BLUE}13.${NC} Статус всех сервисов             ${BLUE}14.${NC} Мониторинг ресурсов            ${WHITE}║${NC}"
    echo -e "${WHITE}║  ${BLUE}15.${NC} Просмотр логов (production)      ${BLUE}16.${NC} Health Check                   ${WHITE}║${NC}"
    echo -e "${WHITE}║                                                                           ║${NC}"
    echo -e "${WHITE}║  ${RED}0.${NC} Выход из панели                   ${CYAN}h.${NC} Справка                       ${WHITE}║${NC}"
    echo -e "${WHITE}║                                                                           ║${NC}"
    echo -e "${WHITE}╚═══════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${WHITE}Выберите опцию [0-16, h]:${NC} "
}

show_production_menu() {
    clear_screen
    print_header
    print_status_bar
    
    echo -e "${WHITE}╔═══════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${WHITE}║                         PRODUCTION УПРАВЛЕНИЕ                            ║${NC}"
    echo -e "${WHITE}╠═══════════════════════════════════════════════════════════════════════════╣${NC}"
    echo -e "${WHITE}║                                                                           ║${NC}"
    echo -e "${WHITE}║  ${BRIGHT_PURPLE}🚀 УПРАВЛЕНИЕ СЕРВИСАМИ${WHITE}                                                  ║${NC}"
    echo -e "${WHITE}║  ${PURPLE}1.${NC} Запустить production сервисы     ${PURPLE}2.${NC} Запуск с Telegram ботом        ${WHITE}║${NC}"
    echo -e "${WHITE}║  ${PURPLE}3.${NC} Остановить production            ${PURPLE}4.${NC} Перезапустить сервисы          ${WHITE}║${NC}"
    echo -e "${WHITE}║  ${PURPLE}5.${NC} Пересобрать контейнеры           ${PURPLE}6.${NC} Синхронизация файлов           ${WHITE}║${NC}"
    echo -e "${WHITE}║                                                                           ║${NC}"
    echo -e "${WHITE}║  ${BRIGHT_YELLOW}📋 ЛОГИ И МОНИТОРИНГ${WHITE}                                                     ║${NC}"
    echo -e "${WHITE}║  ${YELLOW}7.${NC} Все логи                        ${YELLOW}8.${NC} Логи backend                   ${WHITE}║${NC}"
    echo -e "${WHITE}║  ${YELLOW}9.${NC} Логи nginx                       ${YELLOW}10.${NC} Логи indexer                  ${WHITE}║${NC}"
    echo -e "${WHITE}║  ${YELLOW}11.${NC} Мониторинг ресурсов             ${YELLOW}12.${NC} Статус сервисов               ${WHITE}║${NC}"
    echo -e "${WHITE}║                                                                           ║${NC}"
    echo -e "${WHITE}║  ${RED}0.${NC} Назад в главное меню                                                    ${WHITE}║${NC}"
    echo -e "${WHITE}║                                                                           ║${NC}"
    echo -e "${WHITE}╚═══════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${WHITE}Выберите опцию [0-12]:${NC} "
}

show_database_menu() {
    clear_screen
    print_header
    print_status_bar
    
    echo -e "${WHITE}╔═══════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${WHITE}║                        УПРАВЛЕНИЕ БАЗОЙ ДАННЫХ                           ║${NC}"
    echo -e "${WHITE}╠═══════════════════════════════════════════════════════════════════════════╣${NC}"
    echo -e "${WHITE}║                                                                           ║${NC}"
    echo -e "${WHITE}║  ${BRIGHT_GREEN}🏠 DEVELOPMENT БД${WHITE}                                                        ║${NC}"
    echo -e "${WHITE}║  ${GREEN}1.${NC} Миграции (dev)                   ${GREEN}2.${NC} Очистка БД (dev)              ${WHITE}║${NC}"
    echo -e "${WHITE}║  ${GREEN}3.${NC} Резервная копия (dev)            ${GREEN}4.${NC} Создать миграцию              ${WHITE}║${NC}"
    echo -e "${WHITE}║                                                                           ║${NC}"
    echo -e "${WHITE}║  ${BRIGHT_RED}🌐 PRODUCTION БД${WHITE}                                                         ║${NC}"
    echo -e "${WHITE}║  ${RED}5.${NC} Миграции (prod)                  ${RED}6.${NC} Очистка БД (prod) ⚠️           ${WHITE}║${NC}"
    echo -e "${WHITE}║  ${RED}7.${NC} Резервная копия (prod)           ${RED}8.${NC} Проверка соединения           ${WHITE}║${NC}"
    echo -e "${WHITE}║                                                                           ║${NC}"
    echo -e "${WHITE}║  ${BRIGHT_YELLOW}📊 ИНФОРМАЦИЯ${WHITE}                                                            ║${NC}"
    echo -e "${WHITE}║  ${YELLOW}9.${NC} Статус БД                       ${YELLOW}10.${NC} Размер БД                     ${WHITE}║${NC}"
    echo -e "${WHITE}║                                                                           ║${NC}"
    echo -e "${WHITE}║  ${CYAN}0.${NC} Назад в главное меню                                                    ${WHITE}║${NC}"
    echo -e "${WHITE}║                                                                           ║${NC}"
    echo -e "${WHITE}╚═══════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${WHITE}Выберите опцию [0-10]:${NC} "
}

health_check() {
    clear_screen
    print_header
    echo -e "${BG_BLUE}${WHITE} HEALTH CHECK - ПРОВЕРКА СОСТОЯНИЯ СИСТЕМЫ ${NC}\n"
    
    # Local services check
    echo -e "${BRIGHT_CYAN}🏠 ЛОКАЛЬНЫЕ СЕРВИСЫ:${NC}"
    if docker-compose -f docker-compose.dev.yml ps 2>/dev/null | grep -q "Up"; then
        echo -e "  ✅ Docker Compose: ${GREEN}Запущены${NC}"
        docker-compose -f docker-compose.dev.yml ps | head -10
    else
        echo -e "  ❌ Docker Compose: ${RED}Остановлены${NC}"
    fi
    
    echo -e "\n${BRIGHT_PURPLE}🌐 PRODUCTION СЕРВИСЫ:${NC}"
    
    # Test HTTP connection
    if timeout 10 curl -f "http://$REMOTE_HOST" >/dev/null 2>&1; then
        echo -e "  ✅ HTTP Server: ${GREEN}Доступен${NC}"
    else
        echo -e "  ❌ HTTP Server: ${RED}Недоступен${NC}"
    fi
    
    # Test API connection
    if timeout 10 curl -f "http://$REMOTE_HOST/api/health" >/dev/null 2>&1; then
        echo -e "  ✅ API Health: ${GREEN}OK${NC}"
    else
        echo -e "  ⚠️  API Health: ${YELLOW}Недоступен или не настроен${NC}"
    fi
    
    # Test SSH connection
    echo -e "\n${BRIGHT_YELLOW}🔗 SSH СОЕДИНЕНИЕ:${NC}"
    if timeout 5 bash -c "</dev/tcp/$REMOTE_HOST/22" 2>/dev/null; then
        echo -e "  ✅ SSH Port: ${GREEN}Открыт${NC}"
    else
        echo -e "  ❌ SSH Port: ${RED}Недоступен${NC}"
    fi
    
    # System info
    echo -e "\n${BRIGHT_BLUE}💻 СИСТЕМНАЯ ИНФОРМАЦИЯ:${NC}"
    echo -e "  📅 Дата: $(date)"
    echo -e "  🏠 Локальный IP: $(hostname -I | awk '{print $1}')"
    echo -e "  🌐 Production IP: $REMOTE_HOST"
    
    wait_for_key
}

show_help() {
    clear_screen
    print_header
    
    echo -e "${BG_CYAN}${WHITE} СПРАВКА ПО ИСПОЛЬЗОВАНИЮ ПАНЕЛИ ${NC}\n"
    
    echo -e "${BRIGHT_WHITE}🚀 БЫСТРЫЙ СТАРТ:${NC}"
    echo -e "  1. Для локальной разработки: ${GREEN}Опция 1${NC} → Запуск dev окружения"
    echo -e "  2. Для production деплоя: ${PURPLE}Опция 5${NC} → Настройка сервера → ${PURPLE}Опция 6${NC} → Полный деплой"
    echo -e ""
    
    echo -e "${BRIGHT_WHITE}🏠 ЛОКАЛЬНАЯ РАЗРАБОТКА:${NC}"
    echo -e "  • Запускает все сервисы в Docker для разработки"
    echo -e "  • Frontend: ${CYAN}http://localhost:3000${NC}"
    echo -e "  • Backend API: ${CYAN}http://localhost:8000/docs${NC}"
    echo -e "  • WebSocket: ${CYAN}ws://localhost:8001${NC}"
    echo -e ""
    
    echo -e "${BRIGHT_WHITE}🌐 PRODUCTION:${NC}"
    echo -e "  • Настройка сервера устанавливает Docker, firewall, автозапуск"
    echo -e "  • Деплой синхронизирует код, собирает образы, запускает сервисы"
    echo -e "  • Production URL: ${PURPLE}http://$REMOTE_HOST${NC}"
    echo -e ""
    
    echo -e "${BRIGHT_WHITE}🗄️ БАЗА ДАННЫХ:${NC}"
    echo -e "  • Миграции применяют изменения схемы БД"
    echo -e "  • Резервные копии создаются автоматически с датой"
    echo -e "  • Очистка БД требует подтверждения"
    echo -e ""
    
    echo -e "${BRIGHT_WHITE}📊 МОНИТОРИНГ:${NC}"
    echo -e "  • Статус показывает состояние всех сервисов"
    echo -e "  • Мониторинг отображает использование CPU/памяти"
    echo -e "  • Логи доступны для каждого сервиса отдельно"
    echo -e ""
    
    echo -e "${BRIGHT_WHITE}⚠️ ВАЖНЫЕ ЗАМЕЧАНИЯ:${NC}"
    echo -e "  • ${RED}Всегда делайте резервные копии БД перед очисткой${NC}"
    echo -e "  • ${YELLOW}Настройка сервера выполняется только один раз${NC}"
    echo -e "  • ${GREEN}Локальные и production окружения независимы${NC}"
    
    wait_for_key
}

# === MAIN MENU HANDLERS ===
handle_main_menu() {
    local choice
    read -r choice
    
    case $choice in
        1) execute_command "dev-start" "Запуск локального dev окружения" ;;
        2) execute_command "dev-stop" "Остановка локального dev окружения" ;;
        3) execute_command "dev-restart" "Перезапуск локальных сервисов" ;;
        4) 
            echo -e "\n${CYAN}Выберите сервис для просмотра логов:${NC}"
            echo "1) Все сервисы  2) Backend  3) Frontend  4) Postgres  5) Redis"
            echo -n "Выбор [1-5]: "
            read -r log_choice
            case $log_choice in
                1) execute_command "dev-logs" "Просмотр всех dev логов" ;;
                2) execute_command "dev-logs backend" "Просмотр логов backend" ;;
                3) execute_command "dev-logs frontend" "Просмотр логов frontend" ;;
                4) execute_command "dev-logs postgres" "Просмотр логов postgres" ;;
                5) execute_command "dev-logs redis" "Просмотр логов redis" ;;
                *) echo -e "${RED}Неверный выбор${NC}"; wait_for_key ;;
            esac
            ;;
        5) 
            if confirm_action "Настроить удаленный сервер Ubuntu 24? Это установит Docker, firewall и другие компоненты."; then
                execute_command "setup-remote" "Настройка удаленного сервера"
            fi
            ;;
        6) 
            if confirm_action "Выполнить полный production деплой? Это синхронизирует файлы, соберет образы и запустит сервисы."; then
                execute_command "deploy" "Полный production деплой"
            fi
            ;;
        7) execute_command "sync" "Синхронизация файлов с сервером" ;;
        8) production_menu_loop ;;
        9) execute_command "db-migrate dev" "Применение миграций БД (dev)" ;;
        10) execute_command "backup-db dev" "Создание резервной копии БД (dev)" ;;
        11) 
            echo -n "Введите название миграции: "
            read -r migration_name
            if [ -n "$migration_name" ]; then
                execute_command "db-create-migration \"$migration_name\"" "Создание миграции: $migration_name"
            else
                echo -e "${RED}Название миграции не может быть пустым${NC}"
                wait_for_key
            fi
            ;;
        12) database_menu_loop ;;
        13) execute_command "status" "Статус всех сервисов" ;;
        14) 
            echo -e "\n${CYAN}Выберите окружение для мониторинга:${NC}"
            echo "1) Development  2) Production"
            echo -n "Выбор [1-2]: "
            read -r monitor_choice
            case $monitor_choice in
                1) execute_command "monitor dev" "Мониторинг development" ;;
                2) execute_command "monitor prod" "Мониторинг production" ;;
                *) echo -e "${RED}Неверный выбор${NC}"; wait_for_key ;;
            esac
            ;;
        15) 
            echo -e "\n${CYAN}Выберите сервис для просмотра production логов:${NC}"
            echo "1) Все  2) Backend  3) Frontend  4) Nginx  5) Indexer  6) Scheduler  7) WebSocket"
            echo -n "Выбор [1-7]: "
            read -r prod_log_choice
            case $prod_log_choice in
                1) execute_command "prod-logs" "Просмотр всех production логов" ;;
                2) execute_command "prod-logs backend" "Просмотр production логов backend" ;;
                3) execute_command "prod-logs frontend" "Просмотр production логов frontend" ;;
                4) execute_command "prod-logs nginx" "Просмотр production логов nginx" ;;
                5) execute_command "prod-logs indexer" "Просмотр production логов indexer" ;;
                6) execute_command "prod-logs scheduler" "Просмотр production логов scheduler" ;;
                7) execute_command "prod-logs websocket" "Просмотр production логов websocket" ;;
                *) echo -e "${RED}Неверный выбор${NC}"; wait_for_key ;;
            esac
            ;;
        16) health_check ;;
        h|H) show_help ;;
        0) exit 0 ;;
        *) 
            echo -e "${RED}Неверный выбор. Попробуйте еще раз.${NC}"
            wait_for_key
            ;;
    esac
}

# === PRODUCTION MENU HANDLERS ===
handle_production_menu() {
    local choice
    read -r choice
    
    case $choice in
        1) execute_command "prod-start" "Запуск production сервисов" ;;
        2) execute_command "prod-start-telegram" "Запуск production с Telegram ботом" ;;
        3) execute_command "prod-stop" "Остановка production сервисов" ;;
        4) execute_command "prod-restart" "Перезапуск production сервисов" ;;
        5) 
            if confirm_action "Пересобрать все production контейнеры? Это займет время."; then
                execute_command "prod-rebuild" "Пересборка production контейнеров"
            fi
            ;;
        6) execute_command "sync" "Синхронизация файлов" ;;
        7) execute_command "prod-logs" "Просмотр всех production логов" ;;
        8) execute_command "prod-logs backend" "Просмотр логов backend" ;;
        9) execute_command "prod-logs nginx" "Просмотр логов nginx" ;;
        10) execute_command "prod-logs indexer" "Просмотр логов indexer" ;;
        11) execute_command "monitor prod" "Мониторинг production ресурсов" ;;
        12) execute_command "status" "Статус production сервисов" ;;
        0) return ;;
        *) 
            echo -e "${RED}Неверный выбор. Попробуйте еще раз.${NC}"
            wait_for_key
            ;;
    esac
}

# === DATABASE MENU HANDLERS ===
handle_database_menu() {
    local choice
    read -r choice
    
    case $choice in
        1) execute_command "db-migrate dev" "Миграции БД (development)" ;;
        2) 
            if confirm_action "Очистить development базу данных? ВСЕ ДАННЫЕ БУДУТ УДАЛЕНЫ!"; then
                execute_command "db-clean dev" "Очистка development БД"
            fi
            ;;
        3) execute_command "backup-db dev" "Резервная копия development БД" ;;
        4) 
            echo -n "Введите название миграции: "
            read -r migration_name
            if [ -n "$migration_name" ]; then
                execute_command "db-create-migration \"$migration_name\"" "Создание миграции: $migration_name"
            else
                echo -e "${RED}Название миграции не может быть пустым${NC}"
                wait_for_key
            fi
            ;;
        5) execute_command "db-migrate prod" "Миграции БД (production)" ;;
        6) 
            if confirm_action "ВНИМАНИЕ! Очистить PRODUCTION базу данных? ВСЕ ДАННЫЕ БУДУТ УДАЛЕНЫ НАВСЕГДА!"; then
                if confirm_action "ЭТО ДЕЙСТВИЕ НЕОБРАТИМО! Вы АБСОЛЮТНО уверены?"; then
                    execute_command "db-clean prod" "Очистка production БД"
                fi
            fi
            ;;
        7) execute_command "backup-db prod" "Резервная копия production БД" ;;
        8) 
            echo -e "\n${CYAN}Проверка соединения с БД...${NC}"
            if timeout 10 bash -c "</dev/tcp/$REMOTE_HOST/5432" 2>/dev/null; then
                echo -e "${GREEN}✅ Соединение с production БД доступно${NC}"
            else
                echo -e "${RED}❌ Соединение с production БД недоступно${NC}"
            fi
            wait_for_key
            ;;
        9) execute_command "status" "Статус баз данных" ;;
        10) 
            echo -e "\n${CYAN}Проверка размера БД...${NC}"
            # This would need additional implementation in the main CLI
            echo -e "${YELLOW}⚠️ Функция в разработке${NC}"
            wait_for_key
            ;;
        0) return ;;
        *) 
            echo -e "${RED}Неверный выбор. Попробуйте еще раз.${NC}"
            wait_for_key
            ;;
    esac
}

# === MENU LOOPS ===
main_menu_loop() {
    while true; do
        show_main_menu
        handle_main_menu
    done
}

production_menu_loop() {
    while true; do
        show_production_menu
        handle_production_menu
    done
}

database_menu_loop() {
    while true; do
        show_database_menu
        handle_database_menu
    done
}

# === STARTUP CHECKS ===
check_requirements() {
    if [ ! -f "$CLI_SCRIPT" ]; then
        echo -e "${RED}❌ Не найден основной CLI скрипт: $CLI_SCRIPT${NC}"
        echo -e "${YELLOW}Убедитесь, что вы запускаете панель из корневой директории проекта${NC}"
        exit 1
    fi
    
    if [ ! -x "$CLI_SCRIPT" ]; then
        echo -e "${YELLOW}⚠️ Делаем CLI скрипт исполняемым...${NC}"
        chmod +x "$CLI_SCRIPT"
    fi
    
    if [ ! -f "package.json" ] || [ ! -f "Anchor.toml" ]; then
        echo -e "${RED}❌ Панель должна запускаться из корневой директории проекта Solana Mafia${NC}"
        exit 1
    fi
}

# === MAIN FUNCTION ===
main() {
    # Check requirements
    check_requirements
    
    # Handle command line arguments
    if [ $# -gt 0 ]; then
        case "$1" in
            --help|-h)
                show_help
                exit 0
                ;;
            --status|-s)
                health_check
                exit 0
                ;;
        esac
    fi
    
    # Start main menu loop
    main_menu_loop
}

# === SIGNAL HANDLERS ===
trap 'echo -e "\n${YELLOW}Выход из панели...${NC}"; exit 0' INT TERM

# Run main function
main "$@"