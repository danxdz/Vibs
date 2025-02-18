#include <Arduino.h>
#include <Wire.h>
#include <WiFi.h>

// MPU6050 settings
const int MPU_ADDR = 0x68;
int16_t AcX, AcY, AcZ, GyX, GyY, GyZ;

// Hotspot credentials
const char* hotspot_ssid = "Vibs_Hotspot";
const char* hotspot_password = "Vibs123456";

// TCP settings
WiFiServer server(12345);
WiFiClient client;

// Sensor data buffer
int packetSize = 22;
#define CAPTURES_PER_PACKET 100  // Send 100 captures in each packet
uint8_t dataBuffer[2200];  // 20 bytes per capture * 100

// CPS Counter Variables
volatile uint32_t captureCount = 0;
volatile uint32_t sendCount = 0;
uint32_t lastReportTime = 0;  // Track last report time
uint32_t lastCPS = 0;         // Store last CPS value
uint32_t lastSent = 0;         // Store last CPS value


int captureIndex = 0;  // Track captures in the buffer

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
    Wire.write(0x00);  // ±500 deg/sec
    Wire.endTransmission(true);

    Wire.beginTransmission(MPU_ADDR);
    Wire.write(0x1C);  // Accelerometer config register
    Wire.write(0x00);  // ±2g (most sensitive setting)
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
    Wire.requestFrom(MPU_ADDR, (uint8_t)14);

    AcX = (Wire.read() << 8) | Wire.read();
    AcY = (Wire.read() << 8) | Wire.read();
    AcZ = (Wire.read() << 8) | Wire.read();
    Wire.read(); Wire.read();  // Skip temperature

    GyX = (Wire.read() << 8) | Wire.read();
    GyY = (Wire.read() << 8) | Wire.read();
    GyZ = (Wire.read() << 8) | Wire.read();

}


void sendData() {
    if (!client || !client.connected()) return;



    int offset = captureIndex * packetSize;
    
    // Copy sensor data into the buffer
    memcpy(dataBuffer + offset, &GyX, 2);
    memcpy(dataBuffer + offset + 2, &GyY, 2);
    memcpy(dataBuffer + offset + 4, &GyZ, 2);
    memcpy(dataBuffer + offset + 6, &AcX, 2);
    memcpy(dataBuffer + offset + 8, &AcY, 2);
    memcpy(dataBuffer + offset + 10, &AcZ, 2);

    uint32_t timestamp = micros();
    uint32_t cpsValue = lastCPS;

    // Store as little-endian (ESP32 default)
    memcpy(dataBuffer + offset + 12, &timestamp, 4);
    memcpy(dataBuffer + offset + 16, &cpsValue, 4);
    memcpy(dataBuffer + offset + 20, &captureIndex, 2);  // Capture Index for loss detection

    captureIndex++;

    // **Send when buffer is full**
    if (captureIndex == CAPTURES_PER_PACKET) {
        if (client.write(dataBuffer, CAPTURES_PER_PACKET * packetSize) != CAPTURES_PER_PACKET * packetSize) {
            Serial.println("⚠️ Packet loss detected! Consider retransmission.");
        } else {
            sendCount++;
        }
        captureIndex = 0;
    }
}



void networkTask(void *pvParameters) {
    while (1) {
        
        if (!client || !client.connected()) {
            client.stop();  // Ensure cleanup
            client = server.available();
            if (client) {
                Serial.println("✅ Client connected.");
            }
        } else {
            sendData();
        }
        uint32_t startTime = micros();
        // Busy-wait until 250 µs passes
        while (micros() - startTime < 50);
        //vTaskDelay(pdMS_TO_TICKS(0));  // Avoid starving other tasks
    }
}

void sensorTask(void *pvParameters) {
    const uint32_t targetInterval = 250;  // 250 µs for 4 kHz
    uint32_t lastTime = micros();
    int32_t errorSum = 0;  // Accumulated error for fine-tuning

    while (1) {
        uint32_t startTime = micros();

        readMPU6050();
        captureCount++;

        // Calculate elapsed time for one iteration
        uint32_t elapsedTime = startTime - lastTime;
        lastTime = startTime;

        // Calculate timing error (difference from target)
        int32_t error = targetInterval - elapsedTime;
        errorSum += error;  // Accumulate error over time

        // Compute correction using proportional-integral control
        int32_t correction = error + (errorSum / 1000);  // Small integral term

        // Ensure the loop maintains exactly 250µs per cycle
        while (micros() - startTime < (targetInterval + correction)) {
            // Wait until the corrected target interval has passed
        }
    }
}





void setup() {
    Serial.begin(115200);
    Wire.begin();
    Wire.setClock(1000000);

    WiFi.softAP(hotspot_ssid, hotspot_password,1);
    WiFi.setTxPower(WIFI_POWER_19_5dBm); // Max TX power
    WiFi.setSleep(false);  // Disable WiFi power-saving to reduce delays

    Serial.println("🛜 Hotspot active");
    Serial.println(WiFi.softAPIP());

    server.begin();
    Serial.println("📡 TCP Server started.");

    setupMPU6050();
    Serial.println("✅ MPU6050 Ready");

    // Create separate tasks for sensor reading and network communication
    xTaskCreatePinnedToCore(sensorTask, "SensorTask", 8192, NULL, -1, NULL, 0);  // Run on Core 0
    xTaskCreatePinnedToCore(networkTask, "NetworkTask", 8192, NULL, 1, NULL, 1); // Run on Core 1
}

void loop() {
    // Print CPS every 3 seconds
    uint32_t currentTime = micros()/1000;
    if (currentTime - lastReportTime >= 3000) {  // 3 seconds
        lastCPS = captureCount / 3;  // Store last CPS value before resetting
        lastSent = sendCount /3;
        Serial.printf("📊 Captures per second (CPS): %d\n", lastCPS);
        Serial.printf("📊 Packets per second (PPS): %d\n", lastSent);
        captureCount = 0;  // Reset count
        sendCount = 0;
        lastReportTime = currentTime;
    }

    vTaskDelay(pdMS_TO_TICKS(1));  // Force execution at ~1000 Hz
;  // Yield CPU without adding delay
}