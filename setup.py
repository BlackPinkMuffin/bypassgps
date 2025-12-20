from setuptools import setup
import subprocess
import sys

def run(cmd, desc):
    print(f"\033[96m[SETUP]\033[0m {desc}...")
    try:
        subprocess.check_call(cmd, shell=True)
        print(f"\033[92m[OK]\033[0m {desc}")
    except subprocess.CalledProcessError:
        print(f"\033[91m[ERROR]\033[0m {desc}")
        sys.exit(1)

# ---- УСТАНОВКА СИСТЕМНЫХ ПАКЕТОВ ----
print("\033[95m=== Установка системных зависимостей ===\033[0m")

run("sudo apt update", "Обновление репозиториев")
run("sudo apt install -y bluetooth bluez bluez-tools python3-smbus i2c-tools", 
    "Установка Bluetooth и I2C пакетов")

# ---- ВКЛЮЧЕНИЕ СЛУЖБ ----
run("sudo systemctl enable bluetooth", "Включение службы Bluetooth")
run("sudo systemctl start bluetooth", "Запуск Bluetooth")

# ---- PYTHON ЗАВИСИМОСТИ ----
print("\033[95m=== Установка Python зависимостей ===\033[0m")

setup(
    name="bypassgps-deps",
    version="0.3.0",
    description="Dependency installer for bypassgps project",
    install_requires=[
        "python-OBD>=0.7.0",
        "pynmea2>=1.18.0",
        "smbus2>=0.4.3",
        "rich>=13.0.0",
        "pybluez>=0.23"
    ],
)
