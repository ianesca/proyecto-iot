#include <Arduino.h>
#include <WiFi.h>

// Cambia estos valores por los de tu red Wi-Fi
const char* ssid = "Pc-Alex";
const char* password = "123456789";

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("Conectando al WiFi...");
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println("Conexión exitosa");
  Serial.print("Dirección IP: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  // No es necesario hacer nada en loop
}