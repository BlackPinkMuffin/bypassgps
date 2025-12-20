#!/bin/bash

# ============================================
#   ПОНЯШКА — АНИМАЦИЯ
# ============================================

running=true

pony_frames=(
"  (\_/) "
"  ( •_•)"
" / >🦄  "
"  (\_/) "
"  ( •_•)"
"  <🦄 <\ "
)

pony() {
    while $running; do
        for frame in "${pony_frames[@]}"; do
            $running || break
            echo -ne "\033[95m$frame\033[0m\r"
            sleep 0.15
        done
    done
}

# ============================================
#   ПРОГРЕССБАР
# ============================================

progress() {
    local msg="$1"
    local dur="$2"
    local width=40

    echo -e "\033[96m$msg\033[0m"
    for ((i=0; i<width; i++)); do
        echo -ne "\033[92m█\033[0m"
        sleep $(echo "$dur / $width" | bc -l)
    done
    echo
}

# ============================================
#   ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ
# ============================================

run() {
    echo -e "\n\033[94m[RUN]\033[0m $1"
    echo -e "\033[90m→ $2\033[0m"
    eval "$2"
    if [ $? -eq 0 ]; then
        echo -e "\033[92m✔ Успешно\033[0m"
    else
        echo -e "\033[91m✘ Ошибка\033[0m"
        exit 1
    fi
}

# ============================================
#   ПРОВЕРКИ ОБОРУДОВАНИЯ
# ============================================

check_hardware() {
    echo -e "\n\033[93m=== Проверка оборудования ===\033[0m"

    echo -n "I2C... "
    if i2cdetect -y 1 >/dev/null 2>&1; then
        echo -e "\033[92mOK\033[0m"
    else
        echo -e "\033[91mНЕ НАЙДЕН\033[0m"
    fi

    echo -n "Bluetooth... "
    if systemctl is-active bluetooth >/dev/null; then
        echo -e "\033[92mOK\033[0m"
    else
        echo -e "\033[91mНЕ АКТИВЕН\033[0m"
    fi

    echo -n "OBD адаптер... "
    if rfcomm -a 2>/dev/null | grep -q rfcomm0; then
        echo -e "\033[92mOK\033[0m"
    else
        echo -e "\033[91mНЕ ПОДКЛЮЧЕН\033[0m"
    fi
}

# ============================================
#   УСТАНОВКА СИСТЕМНЫХ ПАКЕТОВ
# ============================================

install_system() {
    progress "Обновление репозиториев..." 3
    run "apt update" "sudo apt update -y"

    progress "Установка системных пакетов..." 3
    run "Установка Bluetooth и I2C" \
        "sudo apt install -y bluetooth bluez bluez-tools python3-smbus i2c-tools python3-serial python3-numpy"
}

# ============================================
#   УСТАНОВКА PYTHON ЗАВИСИМОСТЕЙ
# ============================================

install_python() {
    progress "Установка python-OBD..." 2
    run "python-OBD" \
        "pip install git+https://github.com/brendan-w/python-OBD.git"

    progress "Установка остальных зависимостей..." 2
    run "pip install" \
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
echo "Выберите режим: "
read mode

# Запуск поняшки
pony &

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
    *)
        echo "Неверный выбор"
        ;;
esac

# Остановка поняшки
running=false
wait

echo -e "\n\033[92mУстановка завершена! Поняшка довольна 🦄\033[0m"
