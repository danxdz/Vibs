#include <Arduino.h>
#include <Wire.h>
#include <WiFi.h>
#include <WiFiUDP.h>


// MPU6050 settings
const int MPU_ADDR = 0x68;
int16_t AcX, AcY, AcZ, GyX, GyY, GyZ;

// Hotspot credentials
const char* hotspot_ssid = "Vibs_Hotspot";
const char* hotspot_password = "Vibs123456";

// UDP settings
WiFiUDP udp;
IPAddress clientIP;
bool clientConnected = false;
bool isSending = false;
const int serverPort = 12345;
unsigned long lastDiscoveryTime = 0;
const unsigned long DISCOVERY_TIMEOUT = 10000; // 10 seconds timeout

// Sampling & UDP Buffer
const int BATCH_SIZE = 10;  // Number of samples per UDP packet
String dataBuffer = "";

void setupMPU6050() {
    Wire.beginTransmission(MPU_ADDR);
    Wire.write(0x6B);  // Power management register
    Wire.write(0x01);  // Wake up & set clock source
    Wire.endTransmission(true);

    Wire.beginTransmission(MPU_ADDR);
    Wire.write(0x1A);  // Config register
    Wire.write(0x00);  // No DLPF, max bandwidth
    Wire.endTransmission(true);

    Wire.beginTransmission(MPU_ADDR);
    Wire.write(0x1B);  // Gyroscope config
    Wire.write(0x08);  // ±500 deg/sec
    Wire.endTransmission(true);

    Wire.beginTransmission(MPU_ADDR);
    Wire.write(0x19);  // Sample Rate Divider
    Wire.write(0x00);  // 1kHz sampling (SMPRT_DIV = 0)
    Wire.endTransmission(true);
}

void readMPU6050() {
    Wire.beginTransmission(MPU_ADDR);
    Wire.write(0x3B);  // Start reading at register 0x3B
    Wire.endTransmission(false);
    Wire.requestFrom(MPU_ADDR, (uint8_t)14, true);

    AcX = (Wire.read() << 8) | Wire.read();
    AcY = (Wire.read() << 8) | Wire.read();
    AcZ = (Wire.read() << 8) | Wire.read();
    Wire.read(); Wire.read();  // Skip temperature

    GyX = (Wire.read() << 8) | Wire.read();
    GyY = (Wire.read() << 8) | Wire.read();
    GyZ = (Wire.read() << 8) | Wire.read();
}

// Check for client discovery packets
void checkForDiscovery() {
    int packetSize = udp.parsePacket();
    if (packetSize) {
        char buffer[32];
        int len = udp.read(buffer, sizeof(buffer) - 1);
        if (len > 0) {
            buffer[len] = 0; 
            if (String(buffer) == "DISCOVER_VIBS_SERVER") {
                clientIP = udp.remoteIP();
                if (!clientConnected) {
                    Serial.print("✅ New client connected: ");
                    Serial.println(clientIP.toString());
                }
                clientConnected = true;
                lastDiscoveryTime = millis();
                udp.beginPacket(clientIP, serverPort);
                udp.write((uint8_t*)"SERVER_ACK", strlen("SERVER_ACK"));
                udp.endPacket();
            }
        }
    }
}

// Check if the client is still active
void checkClientStatus() {
    if (clientConnected && (WiFi.softAPgetStationNum() == 0 || millis() - lastDiscoveryTime > DISCOVERY_TIMEOUT)) {
        clientConnected = false;
        if (isSending) {
            Serial.println("🛑 Stopped sending packets. Client disconnected.");
            isSending = false;
        }
    }
}

// Task to send sensor data via UDP
void sendDataTask(void* pvParameters) {
    unsigned long lastTime = millis();
    int count = 0;

    while (true) {
        checkForDiscovery();
        checkClientStatus();

        if (clientConnected) {
            if (!isSending) {
                Serial.println("🚀 Started sending packets...");
                isSending = true;
            }

            readMPU6050();
            dataBuffer += String(GyX) + "," + String(GyY) + "," + String(GyZ) + "," + String(millis()) + "\n";

            count++;

            if (count >= BATCH_SIZE) { // Send in batches
                udp.beginPacket(clientIP, serverPort);
                udp.write((uint8_t*)dataBuffer.c_str(), dataBuffer.length());
                udp.endPacket();
                dataBuffer = ""; // Clear buffer after sending
                count = 0;
            }

            if (millis() - lastTime >= 1000) {  // Print sample rate every second
                Serial.print("📊 Samples per second: ");
                Serial.println(count * BATCH_SIZE);
                lastTime = millis();
            }
        } else if (isSending) {
            Serial.println("🛑 Stopped sending packets.");
            isSending = false;
        }

        vTaskDelay(1); // Prevents CPU hogging
    }
}

void setup() {
    Serial.begin(400000);
    Wire.begin();
    Wire.setClock(1000000);  // Set I2C clock to 1MHz for fast reads

    // Start WiFi hotspot
    WiFi.softAP(hotspot_ssid, hotspot_password);
    Serial.println("🛜 Hotspot active");
    Serial.print("Hotspot IP: ");
    Serial.println(WiFi.softAPIP());

    udp.begin(serverPort);
    Serial.println("🔄 UDP server started. Waiting for client...");

    setupMPU6050();
    Serial.println("✅ MPU6050 Ready");

    // Start the data transmission task
    xTaskCreate(sendDataTask, "Send Data Task", 4096, NULL, 1, NULL);
}

void loop() {
    vTaskDelay(1000);  // Nothing in loop to avoid unnecessary CPU usage
}
