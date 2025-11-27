from flask import Flask, render_template_string, jsonify, request
from flask_sqlalchemy import SQLAlchemy
import paho.mqtt.client as mqtt
import json
from datetime import datetime
import time

from pmdarima import auto_arima

# -------------------------------------------------
# Configuración Flask + MySQL
# -------------------------------------------------
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/estacion_iot'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Lectura(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    temperatura = db.Column(db.Float)
    humedad = db.Column(db.Float)
    co2 = db.Column(db.Float)
    fecha = db.Column(db.DateTime, default=datetime.now)

with app.app_context():
    db.create_all()

# Para mostrar algo mientras tanto
latest_data = {"temperature": "-", "humidity": "-", "co2": "-"}
last_update_time = 0

# -------------------------------------------------
# MQTT
# -------------------------------------------------
broker = "broker.emqx.io"
port = 1883
topic_data = "iot/esp32/data"
topic_control = "iot/esp32/control"
client_id = "FlaskDashboard_MySQL"

def to_float_safe(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Conectado al broker MQTT")
        client.subscribe(topic_data)
    else:
        print(f"❌ Error de conexión MQTT rc={rc}")

def on_message(client, userdata, msg):
    """
    Cada vez que llega un mensaje MQTT:
      - se procesa el JSON,
      - se actualiza latest_data,
      - y se GUARDA una fila nueva en la tabla Lectura.
    """
    global latest_data, last_update_time
    try:
        payload = json.loads(msg.payload.decode())
        temp = to_float_safe(payload.get("temperature"))
        hum  = to_float_safe(payload.get("humidity"))
        co2  = to_float_safe(payload.get("co2"))

        latest_data["temperature"] = temp if temp is not None else "-"
        latest_data["humidity"]    = hum  if hum  is not None else "-"
        latest_data["co2"]         = co2  if co2  is not None else "-"

        print(f"📥 MQTT recibido: {payload}")
        print(f"📥 Procesado -> temp={temp}, hum={hum}, co2={co2}")

        # 👉 Aquí es donde se GUARDA en la BD
        if temp is not None and hum is not None and co2 is not None:
            with app.app_context():
                lectura = Lectura(temperatura=temp, humedad=hum, co2=co2)
                db.session.add(lectura)
                db.session.commit()
                print("💾 Lectura guardada en la BD:", lectura.id)

        last_update_time = time.time() * 1000

    except Exception as e:
        print(f"⚠️ Error procesando datos MQTT: {e}")

client = mqtt.Client(client_id)
client.on_connect = on_connect
client.on_message = on_message
client.connect(broker, port)
client.loop_start()

# -------------------------------------------------
# Modelo de predicción (auto-ARIMA)
# -------------------------------------------------
def autoarima_forecast(series, nombre=""):
    valid = [float(v) for v in series if v is not None]

    if len(valid) < 5:
        print(f"⚠️ [{nombre}] Muy pocos datos válidos para auto-ARIMA (n={len(valid)}).")
        return None

    if all(v == valid[0] for v in valid):
        print(f"ℹ️ [{nombre}] Serie casi constante, predicción = {valid[-1]}")
        return float(valid[-1])

    try:
        model = auto_arima(
            valid,
            seasonal=False,
            stepwise=True,
            error_action="ignore",
            suppress_warnings=True,
            max_p=5,
            max_q=5
        )
        fc = model.predict(n_periods=1)[0]
        print(f"✅ [{nombre}] auto-ARIMA OK, predicción = {fc}")
        return float(fc)
    except Exception as e:
        print(f"⚠️ [{nombre}] Error en auto_arima: {e}")
        return None

def calcular_pronostico():
    # Tomamos hasta 80 lecturas recientes, en orden cronológico
    lecturas = (
        Lectura.query
        .order_by(Lectura.fecha.desc())
        .limit(80)
        .all()
    )
    lecturas = list(reversed(lecturas))

    if not lecturas:
        print("⚠️ No hay lecturas en la BD todavía.")
        return {"temperature": None, "humidity": None, "co2": None}

    temps = [l.temperatura for l in lecturas if l.temperatura is not None]
    hums  = [l.humedad    for l in lecturas if l.humedad    is not None]
    co2s_raw = [l.co2     for l in lecturas if l.co2        is not None]
    co2s = [v for v in co2s_raw if v is not None and v > 0]

    print("📊 Muestras BD ->")
    print(f"   Temps (n={len(temps)}): {temps[-5:] if temps else '[]'}")
    print(f"   Hums  (n={len(hums)}): {hums[-5:] if hums else '[]'}")
    print(f"   CO2   (n_raw={len(co2s_raw)}, n_filtrado={len(co2s)}): {co2s[-5:] if co2s else '[]'}")

    pred_temp = autoarima_forecast(temps, nombre="Temperatura") if temps else None
    pred_hum  = autoarima_forecast(hums,  nombre="Humedad")     if hums  else None
    pred_co2  = autoarima_forecast(co2s,  nombre="CO2")         if co2s else None

    print("🔮 Pronósticos finales ->",
          "Temp:", pred_temp, "| Hum:", pred_hum, "| CO2:", pred_co2)

    return {
        "temperature": pred_temp,
        "humidity": pred_hum,
        "co2": pred_co2
    }

# -------------------------------------------------
# HTML (igual que antes, resumido aquí)
# -------------------------------------------------
HTML_PAGE = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Dashboard IoT Climático</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
/* (todo el CSS que ya teníamos, lo dejo igual que tu versión anterior) */
*{box-sizing:border-box;margin:0;padding:0;}
body{
  font-family: system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  background:#f3f4f6;
  color:#111827;
}
.wrapper{
  min-height:100vh;
  display:flex;
  justify-content:center;
  padding:20px;
}
.dashboard{
  width:100%;
  max-width:1280px;
  background:#ffffff;
  border-radius:18px;
  padding:18px 20px 26px;
  box-shadow:0 15px 35px rgba(15,23,42,0.15);
  border:1px solid #e5e7eb;
}
.header{
  display:flex;
  justify-content:space-between;
  align-items:center;
  margin-bottom:14px;
}
.header-left h1{
  font-size:1.5rem;
  font-weight:600;
}
.header-left p{
  font-size:0.9rem;
  color:#6b7280;
}
.badge{
  display:flex;
  align-items:center;
  gap:6px;
  padding:5px 11px;
  border-radius:999px;
  background:#dcfce7;
  color:#166534;
  font-size:0.78rem;
}
.badge-dot{
  width:8px;height:8px;border-radius:50%;background:#22c55e;
  box-shadow:0 0 8px rgba(34,197,94,0.7);
}
.section-title{
  font-size:0.8rem;
  text-transform:uppercase;
  letter-spacing:0.14em;
  color:#9ca3af;
  margin:6px 0 4px;
}
.top-row{
  display:flex;
  gap:16px;
  align-items:flex-start;
  margin-top:4px;
}
.left-column{
  flex:1.1;
}
.right-column{
  flex:1.2;
}
.card-row{
  display:flex;
  gap:10px;
  margin-bottom:6px;
}
.card{
  flex:1;
  min-width:0;
  background:#f9fafb;
  border-radius:12px;
  padding:8px 10px;
  border:1px solid #e5e7eb;
}
.card h2{
  font-size:0.78rem;
  text-transform:uppercase;
  letter-spacing:0.12em;
  color:#6b7280;
}
.card-value{
  margin-top:4px;
  font-size:1.5rem;
  font-weight:600;
  color:#111827;
}
.card-sub{
  margin-top:2px;
  font-size:0.78rem;
  color:#9ca3af;
}
.card-forecast{
  background:#e0f2fe;
  border-color:#bae6fd;
}
.card-forecast .card-value{
  color:#0f172a;
}
.charts-grid{
  display:grid;
  grid-template-columns:repeat(3,minmax(0,1fr));
  gap:12px;
  margin-top:10px;
}
.chart-panel{
  background:#f9fafb;
  border-radius:12px;
  padding:8px 10px;
  border:1px solid #e5e7eb;
}
.chart-title{
  font-size:0.85rem;
  font-weight:500;
  color:#111827;
}
.chart-subtitle{
  font-size:0.75rem;
  color:#9ca3af;
  margin-bottom:4px;
}
canvas{
  width:100%;
  height:150px !important;
}
.forecast-grid{
  display:grid;
  grid-template-columns:repeat(3,minmax(0,1fr));
  gap:12px;
  margin-top:12px;
}
.forecast-panel{
  background:#ffffff;
  border-radius:14px;
  padding:8px 10px;
  border:1px solid #fecaca;
  box-shadow:0 0 0 1px #fee2e2;
}
.forecast-panel.temp{
  border-color:#fb923c;
  box-shadow:0 0 0 1px #fed7aa;
}
.forecast-panel.hum{
  border-color:#22c55e;
  box-shadow:0 0 0 1px #bbf7d0;
}
.forecast-panel.co2{
  border-color:#6366f1;
  box-shadow:0 0 0 1px #c7d2fe;
}
.forecast-header{
  display:flex;
  justify-content:space-between;
  align-items:center;
}
.forecast-label{
  font-size:0.8rem;
  font-weight:500;
}
.forecast-chip{
  font-size:0.7rem;
  padding:2px 8px;
  border-radius:999px;
  background:#fee2e2;
  color:#b91c1c;
}
.forecast-main-value{
  margin-top:4px;
  font-size:1.4rem;
  font-weight:600;
}
.forecast-note{
  font-size:0.72rem;
  color:#6b7280;
  margin-top:2px;
}
.control-bar{
  margin-top:14px;
  display:flex;
  justify-content:flex-end;
  gap:8px;
  align-items:center;
  font-size:0.8rem;
  color:#6b7280;
}
input[type="number"]{
  padding:5px 8px;
  border-radius:999px;
  border:1px solid #d1d5db;
  background:#ffffff;
  color:#111827;
  width:80px;
  font-size:0.8rem;
}
button{
  padding:5px 12px;
  border-radius:999px;
  border:none;
  background:#2563eb;
  color:white;
  font-size:0.8rem;
  cursor:pointer;
}
button:hover{
  filter:brightness(1.05);
}
#statusMsg{
  font-size:0.75rem;
  color:#4b5563;
}
@media(max-width:1000px){
  .top-row{
    flex-direction:column;
  }
  .charts-grid,
  .forecast-grid{
    grid-template-columns:1fr;
  }
}
</style>
</head>
<body>
<div class="wrapper">
  <div class="dashboard">
    <div class="header">
      <div class="header-left">
        <h1>Estación IoT – Clima y Calidad del Aire</h1>
        <p>Lecturas en tiempo real y pronóstico auto-ARIMA desde la base de datos</p>
      </div>
      <div class="badge">
        <span class="badge-dot"></span>
        <span>MQTT conectado</span>
      </div>
    </div>

    <div class="top-row">
      <div class="left-column">
        <div class="section-title">Lecturas actuales (última fila BD)</div>
        <div class="card-row">
          <div class="card">
            <h2>Temperatura</h2>
            <div class="card-value" id="temp">{{ temperature }}°C</div>
            <div class="card-sub">Última medición</div>
          </div>
          <div class="card">
            <h2>Humedad relativa</h2>
            <div class="card-value" id="hum">{{ humidity }}%</div>
            <div class="card-sub">Condición ambiente</div>
          </div>
          <div class="card">
            <h2>CO₂ estimado</h2>
            <div class="card-value" id="co2">{{ co2 }} ppm</div>
            <div class="card-sub">Calidad del aire</div>
          </div>
        </div>

        <div class="section-title">Pronóstico próximo intervalo (auto-ARIMA)</div>
        <div class="card-row">
          <div class="card card-forecast">
            <h2>Temp. pronosticada</h2>
            <div class="card-value" id="tempForecast">--</div>
            <div class="card-sub">Siguiente intervalo</div>
          </div>
          <div class="card card-forecast">
            <h2>Humedad pronosticada</h2>
            <div class="card-value" id="humForecast">--</div>
            <div class="card-sub">Siguiente intervalo</div>
          </div>
          <div class="card card-forecast">
            <h2>CO₂ pronosticado</h2>
            <div class="card-value" id="co2Forecast">--</div>
            <div class="card-sub">Siguiente intervalo</div>
          </div>
        </div>
      </div>

      <div class="right-column">
        <div class="section-title">Histórico de variables (BD)</div>
        <div class="charts-grid">
          <div class="chart-panel">
            <div class="chart-title">Temperatura</div>
            <div class="chart-subtitle">Serie reciente</div>
            <canvas id="chartTemp"></canvas>
          </div>
          <div class="chart-panel">
            <div class="chart-title">Humedad</div>
            <div class="chart-subtitle">Porcentaje relativo</div>
            <canvas id="chartHum"></canvas>
          </div>
          <div class="chart-panel">
            <div class="chart-title">CO₂</div>
            <div class="chart-subtitle">ppm registradas</div>
            <canvas id="chartCO2"></canvas>
          </div>
        </div>
      </div>
    </div>

    <div class="section-title" style="margin-top:12px;">Gráficas de pronóstico</div>
    <div class="forecast-grid">
      <div class="forecast-panel temp">
        <div class="forecast-header">
          <div class="forecast-label">Temperatura – histórico + predicción</div>
          <div class="forecast-chip">auto-ARIMA</div>
        </div>
        <div class="forecast-main-value" id="tempForecastMain">--</div>
        <div class="forecast-note">La línea amarilla une el último valor histórico con el valor pronosticado.</div>
        <canvas id="chartTempForecast"></canvas>
      </div>
      <div class="forecast-panel hum">
        <div class="forecast-header">
          <div class="forecast-label">Humedad – histórico + predicción</div>
          <div class="forecast-chip">auto-ARIMA</div>
        </div>
        <div class="forecast-main-value" id="humForecastMain">--</div>
        <div class="forecast-note">Pronóstico basado en el comportamiento reciente.</div>
        <canvas id="chartHumForecast"></canvas>
      </div>
      <div class="forecast-panel co2">
        <div class="forecast-header">
          <div class="forecast-label">CO₂ – histórico + predicción</div>
          <div class="forecast-chip">auto-ARIMA</div>
        </div>
        <div class="forecast-main-value" id="co2ForecastMain">--</div>
        <div class="forecast-note">El punto final indica la tendencia inmediata de CO₂.</div>
        <canvas id="chartCO2Forecast"></canvas>
      </div>
    </div>

    <div class="control-bar">
      <span>Intervalo de lectura (minutos):</span>
      <input type="number" id="intervalInput" min="1" placeholder="Ej. 10">
      <button onclick="sendControl()">Enviar al ESP32</button>
      <span id="statusMsg"></span>
    </div>
  </div>
</div>

<script>
const baseLineOptions = {
  type: 'line',
  options: {
    responsive: true,
    maintainAspectRatio:false,
    elements: { line: { tension: 0.3 }, point:{ radius:2 } },
    scales: {
      x: { display:false },
      y: { beginAtZero:false }
    },
    plugins: { legend:{ display:false } }
  }
};

let lastLabels = [];
let lastTemps = [];
let lastHums = [];
let lastCO2 = [];

const chartTemp = new Chart(document.getElementById('chartTemp'), {
  ...baseLineOptions,
  data: { labels: [], datasets: [{ label:"Temperatura", data:[], borderColor:"#f97316", backgroundColor:"rgba(248,171,120,0.3)", fill:true }] }
});
const chartHum = new Chart(document.getElementById('chartHum'), {
  ...baseLineOptions,
  data: { labels: [], datasets: [{ label:"Humedad", data:[], borderColor:"#0ea5e9", backgroundColor:"rgba(125,211,252,0.3)", fill:true }] }
});
const chartCO2 = new Chart(document.getElementById('chartCO2'), {
  ...baseLineOptions,
  data: { labels: [], datasets: [{ label:"CO2", data:[], borderColor:"#22c55e", backgroundColor:"rgba(134,239,172,0.3)", fill:true }] }
});

function makeForecastChart(ctx){
  return new Chart(ctx, {
    type:'line',
    data:{
      labels:[],
      datasets:[
        {
          label:"Histórico",
          data:[],
          borderColor:"#6b7280",
          backgroundColor:"rgba(148,163,184,0.25)",
          tension:0.25,
          fill:true,
          pointRadius:1.5
        },
        {
          label:"Pronóstico",
          data:[],
          borderColor:"#facc15",
          backgroundColor:"rgba(250,204,21,0.35)",
          tension:0,
          fill:false,
          pointRadius:6,
          pointBackgroundColor:"#fde047",
          pointBorderColor:"#f97316",
          pointBorderWidth:2,
          borderDash:[5,4],
          borderWidth:2.2
        }
      ]
    },
    options:{
      responsive:true,
      maintainAspectRatio:false,
      scales:{
        x:{ display:true, ticks:{ color:"#6b7280", font:{size:9} }, grid:{ display:false } },
        y:{ beginAtZero:false, ticks:{ color:"#374151", font:{size:10} }, grid:{ color:"#e5e7eb", lineWidth:0.6 } }
      },
      plugins:{ legend:{ display:false } }
    }
  });
}

const chartTempForecast = makeForecastChart(document.getElementById('chartTempForecast'));
const chartHumForecast  = makeForecastChart(document.getElementById('chartHumForecast'));
const chartCO2Forecast  = makeForecastChart(document.getElementById('chartCO2Forecast'));

function fetchData() {
  // ahora /data lee la última fila de la BD
  fetch("/data").then(r => r.json()).then(data => {
    document.getElementById("temp").innerText = data.temperature + "°C";
    document.getElementById("hum").innerText  = data.humidity + "%";
    document.getElementById("co2").innerText  = data.co2 + " ppm";
  });
}

function fetchHistory() {
  fetch("/history").then(r => r.json()).then(data => {
    const labels = data.map(d => d.fecha);
    const temps  = data.map(d => d.temperatura);
    const hums   = data.map(d => d.humedad);
    const co2s   = data.map(d => d.co2);

    lastLabels = labels;
    lastTemps  = temps;
    lastHums   = hums;
    lastCO2    = co2s;

    chartTemp.data.labels = labels;
    chartTemp.data.datasets[0].data = temps;
    chartTemp.update();

    chartHum.data.labels = labels;
    chartHum.data.datasets[0].data = hums;
    chartHum.update();

    chartCO2.data.labels = labels;
    chartCO2.data.datasets[0].data = co2s;
    chartCO2.update();

    updateForecastCharts();
  });
}

function fetchForecast() {
  fetch("/forecast").then(r => r.json()).then(data => {
    if (data.temperature !== null) {
      const t = data.temperature.toFixed(2)+"°C";
      document.getElementById("tempForecast").innerText = t;
      document.getElementById("tempForecastMain").innerText = t;
    } else {
      document.getElementById("tempForecast").innerText = "--";
      document.getElementById("tempForecastMain").innerText = "--";
    }

    if (data.humidity !== null) {
      const h = data.humidity.toFixed(2)+"%";
      document.getElementById("humForecast").innerText = h;
      document.getElementById("humForecastMain").innerText = h;
    } else {
      document.getElementById("humForecast").innerText = "--";
      document.getElementById("humForecastMain").innerText = "--";
    }

    if (data.co2 !== null) {
      const c = data.co2.toFixed(2)+" ppm";
      document.getElementById("co2Forecast").innerText = c;
      document.getElementById("co2ForecastMain").innerText = c;
    } else {
      document.getElementById("co2Forecast").innerText = "--";
      document.getElementById("co2ForecastMain").innerText = "--";
    }

    updateForecastCharts(data);
  });
}

function buildForecastSeries(values, forecastVal){
  if (!values || values.length === 0) {
    return { labels: [], hist: [], forecast: [] };
  }
  const n = values.length;
  const labelsWithForecast = [...lastLabels, "Pronóstico"];
  const histForChart = [...values, null];

  const forecastSeries = [];
  for (let i = 0; i < n - 1; i++) forecastSeries.push(null);
  forecastSeries.push(values[n - 1]);
  forecastSeries.push(forecastVal != null && !isNaN(forecastVal) ? forecastVal : null);

  return { labels: labelsWithForecast, hist: histForChart, forecast: forecastSeries };
}

function updateForecastCharts(preds){
  let tempPred = preds && preds.temperature!=null ? preds.temperature : null;
  let humPred  = preds && preds.humidity!=null ? preds.humidity : null;
  let co2Pred  = preds && preds.co2!=null ? preds.co2 : null;

  const sTemp = buildForecastSeries(lastTemps, tempPred);
  chartTempForecast.data.labels = sTemp.labels;
  chartTempForecast.data.datasets[0].data = sTemp.hist;
  chartTempForecast.data.datasets[1].data = sTemp.forecast;
  chartTempForecast.update();

  const sHum = buildForecastSeries(lastHums, humPred);
  chartHumForecast.data.labels = sHum.labels;
  chartHumForecast.data.datasets[0].data = sHum.hist;
  chartHumForecast.data.datasets[1].data = sHum.forecast;
  chartHumForecast.update();

  const sCO2 = buildForecastSeries(lastCO2, co2Pred);
  chartCO2Forecast.data.labels = sCO2.labels;
  chartCO2Forecast.data.datasets[0].data = sCO2.hist;
  chartCO2Forecast.data.datasets[1].data = sCO2.forecast;
  chartCO2Forecast.update();
}

function sendControl() {
  const value = document.getElementById("intervalInput").value;
  if (!value || value <= 0) { alert("Introduce un valor válido en minutos"); return; }
  fetch("/send_control", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({ interval: value })
  })
  .then(res => res.json())
  .then(() => {
    document.getElementById("statusMsg").innerText = "Intervalo enviado ✔ (" + value + " min)";
    setTimeout(() => document.getElementById("statusMsg").innerText = "", 3000);
  });
}

setInterval(fetchData, 10000);
setInterval(fetchHistory, 15000);
setInterval(fetchForecast, 30000);
fetchHistory();
fetchForecast();
</script>
</body>
</html>
"""

# -------------------------------------------------
# Rutas Flask
# -------------------------------------------------
@app.route("/")
def index():
    # Leemos última fila de la BD para las tarjetas
    lectura = Lectura.query.order_by(Lectura.fecha.desc()).first()
    if lectura is None:
        t = h = c = "-"
    else:
        t = lectura.temperatura
        h = lectura.humedad
        c = lectura.co2

    return render_template_string(
        HTML_PAGE,
        temperature=t,
        humidity=h,
        co2=c
    )

@app.route("/data")
def get_data():
    lectura = Lectura.query.order_by(Lectura.fecha.desc()).first()
    if lectura is None:
        return jsonify({"temperature": "-", "humidity": "-", "co2": "-"})
    return jsonify({
        "temperature": lectura.temperatura,
        "humidity": lectura.humedad,
        "co2": lectura.co2
    })

@app.route("/history")
def history():
    lecturas = Lectura.query.order_by(Lectura.fecha.desc()).limit(30).all()
    data = [
        {
            "fecha": l.fecha.strftime("%H:%M:%S"),
            "temperatura": l.temperatura,
            "humedad": l.humedad,
            "co2": l.co2,
        }
        for l in reversed(lecturas)
    ]
    return jsonify(data)

@app.route("/forecast")
def forecast():
    preds = calcular_pronostico()
    return jsonify(preds)

@app.route("/send_control", methods=["POST"])
def send_control():
    data = request.json
    interval = data.get("interval")
    if interval:
        msg = json.dumps({"interval": int(interval)})
        client.publish(topic_control, msg)
        print(f"📤 Intervalo enviado al ESP32: {interval} minutos")
        return jsonify({"status": "ok"})
    return jsonify({"status": "error"}), 400

if __name__ == "__main__":
    print("🌐 Servidor Flask corriendo en http://127.0.0.1:5000")
    app.run(debug=True, use_reloader=False)