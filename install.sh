#!/bin/bash

# ============================================
#   КРАСИВАЯ АНИМАЦИЯ (СПИННЕР)
# ============================================

spinner() {
    local pid=$!
    local delay=0.1
    local spin='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    while kill -0 $pid 2>/dev/null; do
        for i in $(seq 0 9); do
            printf "\r\033[96m${spin:$i:1} $1...\033[0m"
            sleep $delay
        done
    done
    printf "\r\033[92m✔ $1 завершено\033[0m\n"
}

# ============================================
#   ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ
# ============================================

run() {
    echo -e "\n\033[94m[RUN]\033[0m $1"
    echo -e "\033[90m→ $2\033[0m"
    bash -c "$2" &
    spinner "$1"
}

# ============================================
#   ПРОВЕРКА ОБОРУДОВАНИЯ
# ============================================

check_hardware() {
    echo -e "\n\033[93m=== Проверка оборудования ===\033[0m"

    echo -n "I2C... "
    if i2cdetect -y 1 >/dev/null 2>&1; then
        echo -e "\033[92mOK\033[0m"
    else
        echo -e "\033[91mНЕ НАЙДЕН\033[0m"
    fi

    echo -n "Bluetooth служба... "
    if systemctl is-active bluetooth >/dev/null; then
        echo -e "\033[92mOK\033[0m"
    else
        echo -e "\033[91mНЕ АКТИВНА\033[0m"
    fi

    echo -n "OBD адаптер... "
    if rfcomm -a 2>/dev/null | grep -q rfcomm0; then
        echo -e "\033[92mOK\033[0m"
    else
        echo -e "\033[91mНЕ ПОДКЛЮЧЕН\033[0m"
    fi

    echo -n "Компас (I2C адрес 0x1E)... "
    if i2cdetect -y 1 | grep -q "1e"; then
        echo -e "\033[92mOK\033[0m"
    else
        echo -e "\033[91mНЕ ОБНАРУЖЕН\033[0m"
    fi
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
        "pip install git+https://github.com/brendan-w/python-OBD.git"

    run "Установка Python зависимостей" \
        "pip install pynmea2 smbus2 rich"
}

# ============================================
#   МЕНЮ
# ============================================

clear
echo -e "\033[96m=== BypassGPS Installer ===\033[0m"
echo "1) Полная установка + проверка оборудования"
echo "2) Установка без проверки оборудования"
echo "3) Обновление зависимостей"
echo "4) Проверка оборудования"
echo -n "Выберите режим: "
read mode

case $mode in
    1)
        install_system
        install_python
        check_hardware
        ;;
    2)
        install_system
        install_python
        ;;
    3)
        install_python
        ;;
    4)
        check_hardware
        ;;
    *)
        echo "Неверный выбор"
        ;;
esac

# ============================================
#   КНОПКА ВЫХОДА
# ============================================

echo -e "\n\033[92mГотово! Установка завершена.\033[0m"
echo -e "\033[96mНажмите Enter, чтобы вернуться в bypassgps...\033[0m"
read

cd ~/bypassgps 2>/dev/null
clear
echo -e "\033[92mВы вернулись в bypassgps.\033[0m"
