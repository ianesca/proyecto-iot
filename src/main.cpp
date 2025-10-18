#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <LiquidCrystal.h>
#include "DHT.h"
#include <access.h>

// ===== LCD 16x2 paralelo =====
LiquidCrystal lcd(14, 27, 26, 25, 33, 32); // RS, E, D4, D5, D6, D7

// ===== DHT11 =====
#define DHTPIN 4
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);

// ===== MQ135 =====
#define MQ135_PIN 34  // Pin analógico del MQ135 (GPIO34)

// Calibración MQ135 (ajusta si usas otra resistencia de carga)
float R0 = 10.0;  // Valor de referencia en aire limpio (en KΩ)


// ===== Configuración MQTT =====
const char* mqtt_server = "broker.emqx.io";
const int mqtt_port = 1883;
const char* mqtt_user = "admin";
const char* mqtt_pass = "admin";

WiFiClient espClient;
PubSubClient client(espClient);

// ===== Función de reconexión MQTT =====
void reconnect() {
  while (!client.connected()) {
    Serial.println("Intentando conexión MQTT...");
    String clientId = "ESP32Client-" + String(uint32_t(ESP.getEfuseMac()), HEX);
    if (client.connect(clientId.c_str(), mqtt_user, mqtt_pass)) {
      Serial.println("Conectado al broker MQTT");
    } else {
      Serial.print("Error rc=");
      Serial.print(client.state());
      Serial.println(" - Reintentando en 2s");
      delay(2000);
    }
  }
}

// ===== Función para calcular “ppm de CO₂” estimado =====
float getCO2ppm(int adcValue) {
  // MQ135: RL = 10kΩ
  float voltage = (adcValue / 4095.0) * 5.0;       // ADC → voltaje (ESP32 ADC 12 bits)
  float RS = (5.0 - voltage) / voltage * 10.0;     // RS en KΩ
  float ratio = RS / R0;                           // Relación RS/R0

  // Relación empírica MQ135: CO₂ = 116.6020682 * (ratio ^ -2.769034857)
  float ppm = 116.6020682 * pow(ratio, -2.769034857);

  return ppm;
}

void setup() {
  Serial.begin(115200);

  // LCD
  lcd.begin(16, 2);
  lcd.print("Iniciando...");
  delay(1000);
  lcd.clear();

  // Sensores
  dht.begin();
  pinMode(MQ135_PIN, INPUT);

  // Conexión WiFi
  WiFi.begin(ssid, password);
  Serial.print("Conectando a WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi conectado");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());

  // MQTT
  client.setServer(mqtt_server, mqtt_port);
}

void loop() {
  if (!client.connected()) reconnect();
  client.loop();

  static unsigned long lastRead = 0;
  if (millis() - lastRead > 10000) {
    lastRead = millis();

    float h = dht.readHumidity();
    float t = dht.readTemperature();
    int gasRaw = analogRead(MQ135_PIN);
    float co2ppm = getCO2ppm(gasRaw);

    // Validar lecturas
    if (isnan(h) || isnan(t)) {
      Serial.println("Error leyendo DHT11");
      lcd.clear();
      lcd.print("Error sensor DHT");
      return;
    }

    // Mostrar en LCD
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("T:");
    lcd.print(t);
    lcd.print((char)223);
    lcd.print(" H:");
    lcd.print(h);

    lcd.setCursor(0, 1);
    lcd.print("CO2:");
    lcd.print((int)co2ppm);
    lcd.print(" ppm");

    // Mostrar en Serial
    Serial.print("Temp: "); Serial.print(t);
    Serial.print(" Hum: "); Serial.print(h);
    Serial.print(" CO2: "); Serial.println(co2ppm);

    // Crear JSON y publicar por MQTT
    StaticJsonDocument<256> doc;
    doc["temperature"] = t;
    doc["humidity"] = h;
    doc["co2"] = (int)co2ppm;

    char buffer[256];
    serializeJson(doc, buffer);
    client.publish("iot/esp32/data", buffer);
  }
}
 