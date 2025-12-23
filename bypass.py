import time
import math
import threading
import serial
import pynmea2
import obd
import smbus
from flask import Flask, jsonify, Response

# =======================================
#   НАСТРОЙКИ
# =======================================

I2C_BUS = 2          # твой HMC5883L на i2c-2
I2C_ADDR = 0x1E

GPS_PORT = "/dev/ttyACM0"
GPS_BAUDRATE = 9600

UPDATE_INTERVAL = 0.5  # шаг обновления (с)

# Если хочешь ретранслировать СЫРОЙ GPS NMEA тоже:
FORWARD_RAW_GPS_NMEA = True

# =======================================
#   ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
# =======================================

points = []
lock = threading.Lock()

current_lat = None
current_lon = None
current_speed_kmh = 0.0
current_heading = 0.0

bus = smbus.SMBus(I2C_BUS)

# =======================================
#   КОМПАС HMC5883L
# =======================================

def init_compass():
    try:
        bus.write_byte_data(I2C_ADDR, 0x00, 0x70)  # 8 samples @ 15Hz
        bus.write_byte_data(I2C_ADDR, 0x01, 0x20)  # Gain = 1.3Ga
        bus.write_byte_data(I2C_ADDR, 0x02, 0x00)  # Continuous mode
        print("Компас HMC5883L инициализирован")
    except Exception as e:
        print("Ошибка инициализации компаса:", e)

def read_word(reg):
    high = bus.read_byte_data(I2C_ADDR, reg)
    low = bus.read_byte_data(I2C_ADDR, reg + 1)
    val = (high << 8) + low
    if val >= 0x8000:
        val = -((65535 - val) + 1)
    return val

def read_heading():
    try:
        x = read_word(0x03)
        z = read_word(0x05)
        y = read_word(0x07)

        heading_rad = math.atan2(y, x)
        heading_deg = math.degrees(heading_rad)
        if heading_deg < 0:
            heading_deg += 360
        return heading_deg
    except Exception as e:
        print("Ошибка чтения компаса:", e)
        return 0.0

# =======================================
#   OBD2 ПО BLUETOOTH
# =======================================

def connect_obd():
    print("Подключение к OBD по Bluetooth...")
    while True:
        conn = obd.OBD(fast=False)  # авто-поиск порта
        if conn.is_connected():
            print("OBD подключен:", conn.port_name())
            return conn
        print("OBD не найден, повтор через 5 секунд...")
        time.sleep(5)

def read_speed_kmh(conn):
    rsp = conn.query(obd.commands.SPEED)
    if rsp.is_null():
        return None
    return rsp.value.to("km/h").magnitude

# =======================================
#   NMEA VTG И ЧЕКСУММА
# =======================================

def nmea_checksum(sentence_body: str) -> str:
    csum = 0
    for c in sentence_body:
        csum ^= ord(c)
    return f"{csum:02X}"

def make_vtg(heading_deg: float, speed_kmh: float) -> str:
    knots = speed_kmh * 0.539957
    body = f"GPVTG,{heading_deg:.1f},T,,M,{knots:.2f},N,{speed_kmh:.2f},K"
    cs = nmea_checksum(body)
    return f"${body}*{cs}"

# =======================================
#   GPS (NMEA)
# =======================================

def gps_thread():
    global current_lat, current_lon
    while True:
        try:
            with serial.Serial(GPS_PORT, GPS_BAUDRATE, timeout=1) as ser:
                print(f"GPS подключен к {GPS_PORT}")
                while True:
                    line = ser.readline().decode(errors="ignore").strip()
                    if not line.startswith("$"):
                        continue

                    # По желанию: пробрасываем сырые GPS строки в stdout
                    if FORWARD_RAW_GPS_NMEA:
                        print(line, flush=True)

                    try:
                        msg = pynmea2.parse(line)
                    except pynmea2.nmea.ParseError:
                        continue

                    if isinstance(msg, pynmea2.RMC) or isinstance(msg, pynmea2.GGA):
                        if msg.latitude and msg.longitude:
                            with lock:
                                current_lat = msg.latitude
                                current_lon = msg.longitude
        except Exception as e:
            print("Ошибка GPS:", e)
            print("Повторное подключение к GPS через 5 секунд...")
            time.sleep(5)

# =======================================
#   СБОР ДАННЫХ (OBD + КОМПАС + GPS + NMEA)
# =======================================

def data_collector():
    global current_speed_kmh, current_heading

    init_compass()
    conn = connect_obd()

    while True:
        # Скорость
        kmh = read_speed_kmh(conn)
        if kmh is None:
            kmh = 0.0

        # Курс
        heading = read_heading()

        # Координаты
        with lock:
            lat = current_lat
            lon = current_lon

        # Формируем и выводим VTG (это и есть твой bypassgps NMEA-выход)
        vtg_sentence = make_vtg(heading, kmh)
        print(vtg_sentence, flush=True)

        # Для карты — добавляем точку, если есть координаты
        if lat is not None and lon is not None:
            point = {
                "lat": lat,
                "lon": lon,
                "speed": kmh,
                "heading": heading,
                "timestamp": time.time()
            }
            with lock:
                points.append(point)

        current_speed_kmh = kmh
        current_heading = heading

        time.sleep(UPDATE_INTERVAL)

# =======================================
#   ВЕБ-СЕРВЕР
# =======================================

app = Flask(__name__)

@app.route("/")
def index():
    html = """
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>BypassGPS трек</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<style>
  html, body, #map { height: 100%; margin: 0; padding: 0; }
  #info {
    position: absolute; top: 10px; left: 10px;
    background: rgba(255,255,255,0.9); padding: 8px; border-radius: 4px;
    font-family: sans-serif; font-size: 13px;
  }
</style>
</head>
<body>
<div id="map"></div>
<div id="info">
  <div>Скорость: <span id="speed">--</span> км/ч</div>
  <div>Курс: <span id="heading">--</span>°</div>
</div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
  var map = L.map('map').setView([55.75, 37.61], 12);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19
  }).addTo(map);

  var trackLayers = [];
  window._centered = false;

  function speedColor(speed) {
    if (speed < 20) return 'red';
    if (speed < 40) return 'yellow';
    if (speed < 60) return 'green';
    if (speed < 80) return 'blue';
    return 'purple';
  }

  function updateData() {
    fetch('/data')
      .then(r => r.json())
      .then(data => {
        trackLayers.forEach(l => map.removeLayer(l));
        trackLayers = [];

        if (data.points.length > 1) {
          for (let i = 0; i < data.points.length - 1; i++) {
            let p1 = data.points[i];
            let p2 = data.points[i+1];
            let color = speedColor(p2.speed);
            let line = L.polyline([[p1.lat, p1.lon], [p2.lat, p2.lon]], {color: color, weight: 4});
            line.addTo(map);
            trackLayers.push(line);
          }
          if (!window._centered) {
            let last = data.points[data.points.length - 1];
            map.setView([last.lat, last.lon], 15);
            window._centered = true;
          }
        }

        document.getElementById('speed').textContent = data.current_speed.toFixed(1);
        document.getElementById('heading').textContent = data.current_heading.toFixed(1);
      })
      .catch(err => console.error(err));
  }

  setInterval(updateData, 1000);
</script>
</body>
</html>
"""
    return Response(html, mimetype="text/html")

@app.route("/data")
def get_data():
    with lock:
        data = {
            "points": points[-1000:],
            "current_speed": current_speed_kmh,
            "current_heading": current_heading
        }
    return jsonify(data)

# =======================================
#   ЗАПУСК
# =======================================

def main():
    t_gps = threading.Thread(target=gps_thread, daemon=True)
    t_gps.start()

    t_data = threading.Thread(target=data_collector, daemon=True)
    t_data.start()

    print("Запуск веб-сервера на http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)

if __name__ == "__main__":
    main()
