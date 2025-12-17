import obd, time, pynmea2

# Подключение к адаптеру
conn = obd.OBD("/dev/rfcomm0", fast=False)

while True:
    rsp = conn.query(obd.commands.SPEED)
    if not rsp.is_null():
        kmh = rsp.value.to("km/h").magnitude
        knots = kmh * 0.539957

        # Формируем GPVTG (курс 0.0, скорость в узлах и км/ч)
        msg = pynmea2.VTG('GP','VTG',(
            '0.0','T','','M',
            f"{knots:.2f}",'N',
            f"{kmh:.2f}",'K'
        ))
        print(msg.render())
    else:
        print("Нет данных от адаптера")
    time.sleep(1)