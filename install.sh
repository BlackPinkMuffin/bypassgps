#!/bin/bash

# ============================================
#   ЦВЕТА
# ============================================

GREEN="\033[92m"
RED="\033[91m"
YELLOW="\033[93m"
BLUE="\033[94m"
CYAN="\033[96m"
GRAY="\033[90m"
RESET="\033[0m"

# ============================================
#   ЛОГИ ДЛЯ ИТОГОВОЙ ТАБЛИЦЫ
# ============================================

declare -A RESULTS

log_result() {
    local key="$1"
    local value="$2"
    RESULTS["$key"]="$value"
}

print_results_table() {
    if [ ${#RESULTS[@]} -eq 0 ]; then
        return
    fi

    echo -e "\n${YELLOW}=== Итоги установки ===${RESET}"
    printf '┌%-30s┬%-20s┐\n' \
        "$(printf '──────────────────────────────')" \
        "$(printf '────────────────────')"
    printf '│ %-28s │ %-18s │\n' "Действие" "Результат"
    printf '├%-30s┼%-20s┤\n' \
        "$(printf '──────────────────────────────')" \
        "$(printf '────────────────────')"

    for key in "${!RESULTS[@]}"; do
        printf '│ %-28s │ %-18s │\n' "$key" "${RESULTS[$key]}"
    done

    printf '└%-30s┴%-20s┘\n' \
        "$(printf '──────────────────────────────')" \
        "$(printf '────────────────────')"
}

# ============================================
#   СПИННЕР (АНИМАЦИЯ)
# ============================================

spinner() {
    local msg="$1"
    local pid="$2"
    local delay=0.1
    local spin='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'

    while kill -0 "$pid" 2>/dev/null; do
        for i in $(seq 0 9); do
            printf "\r${CYAN}${spin:$i:1} %s...${RESET}" "$msg"
            sleep "$delay"
        done
    done

    printf "\r${GREEN}✔ %s завершено${RESET}\n" "$msg"
}

# ============================================
#   ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ RUN
# ============================================

run() {
    local title="$1"
    local cmd="$2"

    echo -e "\n${BLUE}[RUN]${RESET} $title"
    echo -e "${GRAY}→ $cmd${RESET}"

    bash -c "$cmd" &
    local pid=$!
    spinner "$title" "$pid"
    wait "$pid"
    local status=$?

    if [ $status -eq 0 ]; then
        log_result "$title" "Успешно"
    else
        log_result "$title" "Ошибка ($status)"
        echo -e "${RED}Команда завершилась с ошибкой. Остановка.${RESET}"
        print_results_table
        exit 1
    fi
}

# ============================================
#   ПОИСК i2cdetect
# ============================================

find_i2cdetect() {
    if command -v i2cdetect >/dev/null 2>&1; then
        echo "i2cdetect"
    elif [ -x /usr/sbin/i2cdetect ]; then
        echo "/usr/sbin/i2cdetect"
    else
        echo ""
    fi
}

# ============================================
#   ПРОВЕРКА ОБОРУДОВАНИЯ
# ============================================

check_hardware() {
    echo -e "\n${YELLOW}=== Проверка оборудования ===${RESET}"

    local I2CDETECT_CMD
    I2CDETECT_CMD=$(find_i2cdetect)

    # ---- I2C и компас ----
    local I2C_BUSES=()
    if [ -n "$I2CDETECT_CMD" ]; then
        I2C_BUSES=($(ls /dev/i2c-* 2>/dev/null | sed 's/[^0-9]//g'))
    fi

    local buses_str="нет"
    local compass_status="НЕ ОБНАРУЖЕН"
    local compass_bus="-"

    if [ ${#I2C_BUSES[@]} -eq 0 ] || [ -z "$I2CDETECT_CMD" ]; then
        echo -e "I2C шины... ${RED}НЕ НАЙДЕНЫ${RESET}"
    else
        buses_str=$(printf '%s ' "${I2C_BUSES[@]}")
        echo -e "I2C шины... ${GREEN}${buses_str}${RESET}"

        # ищем компас (адрес 0x1E) по всем шинам
        for bus in "${I2C_BUSES[@]}"; do
            if $I2CDETECT_CMD -y "$bus" 2>/dev/null | grep -q "1e"; then
                compass_status="Найден"
                compass_bus="$bus"
                break
            fi
        done
    fi

    # ---- Bluetooth ----
    local bt_status="НЕ АКТИВЕН"
    if command -v systemctl >/dev/null 2>&1 && systemctl is-active bluetooth >/dev/null 2>&1; then
        bt_status="OK (systemd)"
    elif command -v bluetoothctl >/dev/null 2>&1 && bluetoothctl show >/dev/null 2>&1; then
        bt_status="OK (bluetoothctl)"
    elif [ -d /sys/class/bluetooth ]; then
        bt_status="НАЙДЕН (sysfs)"
    fi

    # ---- OBD ----
    local obd_status="НЕ ПОДКЛЮЧЕН"
    local obd_candidates=(/dev/rfcomm* /dev/ttyUSB* /dev/ttyAMA* /dev/ttyS*)
    for dev in "${obd_candidates[@]}"; do
        if [ -e "$dev" ]; then
            obd_status="НАЙДЕН ($dev)"
            break
        fi
    done

    # ---- Таблица статусов ----
    printf '\n┌%-23s┬%-26s┐\n' \
        "$(printf '───────────────────────')" \
        "$(printf '──────────────────────────')"
    printf '│ %-21s │ %-24s │\n' "Компонент" "Статус"
    printf '├%-23s┼%-26s┤\n' \
        "$(printf '───────────────────────')" \
        "$(printf '──────────────────────────')"

    printf '│ %-21s │ %-24s │\n' "I2C шины" "$buses_str"
    printf '│ %-21s │ %-24s │\n' "Компас 0x1E" "$compass_status (bus $compass_bus)"
    printf '│ %-21s │ %-24s │\n' "Bluetooth" "$bt_status"
    printf '│ %-21s │ %-24s │\n' "OBD адаптер" "$obd_status"

    printf '└%-23s┴%-26s┘\n\n' \
        "$(printf '───────────────────────')" \
        "$(printf '──────────────────────────')"
}

# ============================================
#   УСТАНОВКА СИСТЕМНЫХ ПАКЕТОВ
# ============================================

install_system() {
    run "Обновление репозиториев" "sudo apt update -y"
    run "Установка системных пакетов" \
        "sudo apt install -y bluetooth bluez bluez-tools python3-smbus i2c-tools python3-serial python3-numpy"
}

# ============================================
#   УСТАНОВКА PYTHON ЗАВИСИМОСТЕЙ
# ============================================

install_python() {
    run "Установка python-OBD" \
        "pip install --break-system-packages git+https://github.com/brendan-w/python-OBD.git"

    run "Установка Python зависимостей" \
        "pip install --break-system-packages pynmea2 smbus2 rich"
}

# ============================================
#   МЕНЮ
# ============================================

clear
echo -e "${CYAN}=== BypassGPS Installer ===${RESET}"
echo "1) Установка"
echo "2) Проверка оборудования"
echo -n "Выберите режим: "
read mode

case "$mode" in
    1)
        install_system
        install_python
        check_hardware
        ;;
    2)
        check_hardware
        ;;
    *)
        echo -e "${RED}Неверный выбор${RESET}"
        ;;
esac

print_results_table

# ============================================
#   КНОПКА ВЫХОДА
# ============================================

echo -e "\n${GREEN}Готово! Скрипт завершил работу.${RESET}"
echo -e "${CYAN}Нажмите Enter, чтобы вернуться в bypassgps...${RESET}"
read

cd ~/bypassgps 2>/dev/null || true
clear
echo -e "${GREEN}Вы вернулись в bypassgps.${RESET}"
