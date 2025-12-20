from setuptools import setup
import subprocess
import sys
import time
import threading
import itertools
import shutil

# -----------------------------
#   АНИМАЦИЯ ПОНЯШКИ
# -----------------------------

running = True

pony_frames = [
    r"  (\_/) ",
    r"  ( •_•)",
    r" / >🦄  ",
    r"  (\_/) ",
    r"  ( •_•)",
    r"  <🦄 <\ ",
]

def pony_runner():
    global running
    while running:
        for frame in pony_frames:
            if not running:
                break
            print(f"\033[95m{frame}\033[0m", end="\r")
            time.sleep(0.15)


# -----------------------------
#   ПРОГРЕССБАР
# -----------------------------

def progress_bar(task, seconds=3):
    width = shutil.get_terminal_size().columns - 20
    print(f"\033[96m{task}\033[0m")
    for i in range(width):
        print("\033[92m█\033[0m", end="", flush=True)
        time.sleep(seconds / width)
    print()


# -----------------------------
#   ВЫПОЛНЕНИЕ КОМАНД
# -----------------------------

def run(cmd, desc):
    print(f"\n\033[94m[SETUP]\033[0m {desc}")
    print(f"\033[90m→ {cmd}\033[0m")

    try:
        subprocess.check_call(cmd, shell=True)
        print(f"\033[92m✔ Успешно: {desc}\033[0m")
    except subprocess.CalledProcessError:
        print(f"\033[91m✘ Ошибка: {desc}\033[0m")
        sys.exit(1)


# -----------------------------
#   СТАРТ АНИМАЦИИ
# -----------------------------

pony_thread = threading.Thread(target=pony_runner)
pony_thread.start()

# -----------------------------
#   УСТАНОВКА СИСТЕМНЫХ ПАКЕТОВ
# -----------------------------

progress_bar("Обновление списка пакетов...")
run("sudo apt update", "Обновление репозиториев")

progress_bar("Установка Bluetooth и I2C...")
run("sudo apt install -y bluetooth bluez bluez-tools python3-smbus i2c-tools",
    "Установка системных пакетов")

run("sudo systemctl enable bluetooth", "Включение Bluetooth")
run("sudo systemctl start bluetooth", "Запуск Bluetooth")

# -----------------------------
#   ОСТАНОВКА АНИМАЦИИ
# -----------------------------

running = False
pony_thread.join()
print("\033[92mПоняшка убежала дальше устанавливать магию...\033[0m\n")

# -----------------------------
#   PYTHON ЗАВИСИМОСТИ
# -----------------------------

setup(
    name="bypassgps-deps",
    version="0.5.0",
    install_requires=[
        "python-OBD",
        "pynmea2",
        "smbus2",
        "rich"
    ],
)
