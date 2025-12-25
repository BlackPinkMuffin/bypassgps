import time
import math
import threading
import obd
import smbus
from flask import Flask, jsonify, Response

# =======================================
#   НАСТРОЙКИ
# =======================================

I2C_BUS = 2
I2C_ADDR = 0x1E

UPDATE_INTERVAL = 0.5

# Начальная точка карты (Воронеж)
MAP_LAT = 51.685704
MAP_LON = 39.258792

# =======================================
#   ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
# =======================================

points = []
lock = threading.Lock()

current_lat = MAP_LAT
current_lon = MAP_LON
current_speed_kmh = 0.0
current_heading = 0.0

bus = smbus.SMBus(I2C_BUS)

# =======================================
#   КОМПАС HMC5883L
# =======================================

def init_compass():
    try:
        bus.write_byte_data(I2C_ADDR, 0x00, 0x70)
        bus.write_byte_data(I2C_ADDR, 0x01, 0x20)
        bus.write_byte_data(I2C_ADDR, 0x02, 0x00)
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
    except:
        return 0.0

# =======================================
#   OBD2
# =======================================

def connect_obd():
    print("Подключение к OBD...")
    while True:
        conn = obd.OBD(fast=False)
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
#   NMEA VTG
# =======================================

def nmea_checksum(body):
    csum = 0
    for c in body:
        csum ^= ord(c)
    return f"{csum:02X}"

def make_vtg(heading, kmh):
    knots = kmh * 0.539957
    body = f"GPVTG,{heading:.1f},T,,M,{knots:.2f},N,{kmh:.2f},K"
    return f"${body}*{nmea_checksum(body)}"

# =======================================
#   СБОР ДАННЫХ
# =======================================

def data_collector():
    global current_speed_kmh, current_heading, current_lat, current_lon

    init_compass()
    conn = connect_obd()

    while True:
        kmh = read_speed_kmh(conn)
        if kmh is None:
            kmh = 0.0

        heading = read_heading()

        # Выводим NMEA VTG
        print(make_vtg(heading, kmh), flush=True)

        # Добавляем точку (движение имитируем по курсу)
        current_lat += math.cos(math.radians(heading)) * (kmh / 360000.0)
        current_lon += math.sin(math.radians(heading)) * (kmh / 360000.0)

        point = {
            "lat": current_lat,
            "lon": current_lon,
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
    html = f"""
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>BypassGPS трек</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<style>
  html, body, #map {{ height: 100%; margin: 0; padding: 0; }}
  #info {{
    position: absolute; top: 10px; left: 10px;
    background: rgba(255,255,255,0.9); padding: 8px; border-radius: 4px;
    font-family: sans-serif; font-size: 13px;
  }}
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
  var map = L.map('map').setView([{MAP_LAT}, {MAP_LON}], 15);

  L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
    maxZoom: 19
  }}).addTo(map);

  var trackLayers = [];

  function speedColor(speed) {{
    if (speed < 20) return 'red';
    if (speed < 40) return 'yellow';
    if (speed < 60) return 'green';
    if (speed < 80) return 'blue';
    return 'purple';
  }}

  function updateData() {{
    fetch('/data')
      .then(r => r.json())
      .then(data => {{
        trackLayers.forEach(l => map.removeLayer(l));
        trackLayers = [];

        if (data.points.length > 1) {{
          for (let i = 0; i < data.points.length - 1; i++) {{
            let p1 = data.points[i];
            let p2 = data.points[i+1];
            let color = speedColor(p2.speed);
            let line = L.polyline([[p1.lat, p1.lon], [p2.lat, p2.lon]], {{color: color, weight: 4}});
            line.addTo(map);
            trackLayers.push(line);
          }}
        }}

        document.getElementById('speed').textContent = data.current_speed.toFixed(1);
        document.getElementById('heading').textContent = data.current_heading.toFixed(1);
      }});
  }}

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
    t_data = threading.Thread(target=data_collector, daemon=True)
    t_data.start()

    print("Веб-сервер: http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)

if __name__ == "__main__":
    main()
