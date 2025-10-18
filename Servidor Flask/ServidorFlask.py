from flask import Flask, render_template_string, jsonify
from flask_sqlalchemy import SQLAlchemy
import paho.mqtt.client as mqtt
import json
from datetime import datetime

# --- Configuración Flask + MySQL ---
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/estacion_iot'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Modelo de la tabla ---
class Lectura(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    temperatura = db.Column(db.Float)
    humedad = db.Column(db.Float)
    co2 = db.Column(db.Float)
    fecha = db.Column(db.DateTime, default=datetime.now)

# Crear tabla si no existe
with app.app_context():
    db.create_all()

# --- Variables globales ---
latest_data = {"temperature": "-", "humidity": "-", "co2": "-"}

# --- Configuración MQTT ---
broker = "broker.emqx.io"
port = 1883
topic_data = "iot/esp32/data"
client_id = "FlaskDashboard_MySQL"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Conectado al broker MQTT")
        client.subscribe(topic_data)
    else:
        print(f"❌ Error de conexión MQTT rc={rc}")

def on_message(client, userdata, msg):
    global latest_data
    try:
        payload = json.loads(msg.payload.decode())
        temp = payload.get("temperature", "-")
        hum = payload.get("humidity", "-")
        co2 = payload.get("co2", "-")

        latest_data["temperature"] = temp
        latest_data["humidity"] = hum
        latest_data["co2"] = co2

        # Guardar en MySQL si los datos son válidos
        if temp != "-" and hum != "-" and co2 != "-":
            lectura = Lectura(temperatura=temp, humedad=hum, co2=co2)
            with app.app_context():
                db.session.add(lectura)
                db.session.commit()
        print(f"Datos recibidos: {latest_data}")
    except Exception as e:
        print(f"⚠️ Error procesando datos MQTT: {e}")

def on_disconnect(client, userdata, rc):
    print(f"Desconectado del broker MQTT (rc={rc})")
    try:
        client.reconnect()
    except:
        print("Reconexión fallida, reintentando...")

# Inicializar MQTT
client = mqtt.Client(client_id)
client.on_connect = on_connect
client.on_message = on_message
client.on_disconnect = on_disconnect
client.connect(broker, port)
client.loop_start()

# --- Interfaz Web ---
HTML_PAGE = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Estación Meteorológica IoT</title>
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700&display=swap" rel="stylesheet">
<style>
    body {
        font-family: 'Montserrat', sans-serif;
        text-align: center;
        background-color: #87CEEB;
        color: #333;
        margin: 0;
        padding: 50px 20px;
    }
    h1 {
        font-size: 3em;
        margin-bottom: 30px;
        color: white;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    }
    .dashboard-container {
        display: flex;
        justify-content: center;
        flex-wrap: wrap;
        gap: 20px;
    }
    .card {
        background: rgba(255, 255, 255, 0.9);
        padding: 30px;
        border-radius: 15px;
        width: 250px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        display: flex;
        flex-direction: column;
        align-items: center;
    }
    .value {
        font-size: 3em;
        font-weight: 700;
        color: #007bff;
    }
    .label {
        font-size: 1.2em;
        margin-top: 10px;
        color: #555;
        font-weight: 400;
    }
</style>
</head>
<body>
<h1>Lecturas en Tiempo Real</h1>
<div class="dashboard-container">
    <div class="card">
        <div class="value" id="temp">{{ temperature }}°C</div>
        <div class="label">Temperatura</div>
    </div>
    <div class="card">
        <div class="value" id="hum">{{ humidity }}%</div>
        <div class="label">Humedad</div>
    </div>
    <div class="card">
        <div class="value" id="co2">{{ co2 }} ppm</div>
        <div class="label">CO₂ (Calidad del Aire)</div>
    </div>
</div>

<script>
setInterval(() => {
    fetch("/data")
        .then(res => res.json())
        .then(data => {
            document.getElementById("temp").innerText = data.temperature + "°C";
            document.getElementById("hum").innerText = data.humidity + "%";
            document.getElementById("co2").innerText = data.co2 + " ppm";
        })
        .catch(console.error);
}, 2000);
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_PAGE, 
                                  temperature=latest_data["temperature"], 
                                  humidity=latest_data["humidity"],
                                  co2=latest_data["co2"])

@app.route("/data")
def get_data():
    return jsonify(latest_data)

# --- Ejecutar Flask ---
if __name__ == "__main__":
    print("🌐 Servidor Flask corriendo en http://127.0.0.1:5000")
    app.run(debug=True, use_reloader=False)
