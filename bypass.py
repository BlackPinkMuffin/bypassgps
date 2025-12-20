import time
import math
import obd
import pynmea2
import smbus


# ============================
#   НАСТРОЙКИ КОМПАСА GY-271
# ============================

I2C_BUS = 1          # I2C-1 на BeagleBone
I2C_ADDR = 0x0D      # Адрес QMC5883L (GY-271)

bus = smbus.SMBus(I2C_BUS)

# Инициализация QMC5883L
def init_compass():
    try:
        # Режим: 200Hz, 2G, Continuous
        bus.write_byte_data(I2C_ADDR, 0x0B, 0x01)
        bus.write_byte_data(I2C_ADDR, 0x09, 0x1D)
        print("Компас GY-271 инициализирован")
    except Exception as e:
        print("Ошибка инициализации компаса:", e)


def read_heading():
    try:
        data = bus.read_i2c_block_data(I2C_ADDR, 0x00, 6)

        x = data[1] << 8 | data[0]
        y = data[3] << 8 | data[2]
        z = data[5] << 8 | data[4]

        # Преобразование в signed
        if x > 32767: x -= 65536
        if y > 32767: y -= 65536

        heading_rad = math.atan2(y, x)
        heading_deg = math.degrees(heading_rad)

        if heading_deg < 0:
            heading_deg += 360

        return heading_deg

    except Exception as e:
        print("Ошибка чтения компаса:", e)
        return 0.0


# ============================
#   OBD2
# ============================

def read_speed_kmh(conn):
    rsp = conn.query(obd.commands.SPEED)
    if rsp.is_null():
        return None
    return rsp.value.to("km/h").magnitude


# ============================
#   ОСНОВНОЙ ЦИКЛ
# ============================

def main():
    print("Инициализация компаса...")
    init_compass()

    print("Подключение к OBD2...")
    conn = obd.OBD("/dev/rfcomm0", fast=False)

    print("Старт bypassgps...")

    while True:
        kmh = read_speed_kmh(conn)

        if kmh is None:
            print("Нет данных от адаптера")
            time.sleep(1)
            continue

        knots = kmh * 0.539957
        heading = read_heading()

        # Формируем NMEA VTG
        msg = pynmea2.VTG('GP', 'VTG', (
            f"{heading:.1f}", 'T', '', 'M',
            f"{knots:.2f}", 'N',
            f"{kmh:.2f}", 'K'
        ))

        print(msg.render())

        time.sleep(0.3)


if __name__ == "__main__":
    main()
