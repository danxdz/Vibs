#include <Arduino.h>
#include <Wire.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include <WiFi.h>
#include <WiFiUDP.h>  // Use WiFiUDP for UDP communication

const int MPU_ADDR = 0x68;
int16_t AcX, AcY, AcZ, GyX, GyY, GyZ;

const char* ssid = "Home";
const char* password = "password";

// Instead of a fixed server IP, use the broadcast address.
const char* broadcastIP = "255.255.255.255"; 
const int serverPort = 12345; // Port for UDP

WiFiUDP udp;  // Use WiFiUDP object for UDP communication

void setupMPU6050() {
    Wire.begin();
    Wire.setClock(1000000); // Set I²C clock to 1MHz for max speed

    Wire.beginTransmission(MPU_ADDR);
    Wire.write(0x6B); 
    Wire.write(0x01); 
    Wire.endTransmission(true);

    Wire.beginTransmission(MPU_ADDR);
    Wire.write(0x1A);
    Wire.write(0x00); // Disable low-pass filter
    Wire.endTransmission(true);
}

void readMPU6050() {
    Wire.beginTransmission(MPU_ADDR);
    Wire.write(0x3B);
    Wire.endTransmission(false);
    Wire.requestFrom(MPU_ADDR, 14, true);

    AcX = Wire.read() << 8 | Wire.read();
    AcY = Wire.read() << 8 | Wire.read();
    AcZ = Wire.read() << 8 | Wire.read();
    Wire.read(); Wire.read(); // Skip Temp data
    GyX = Wire.read() << 8 | Wire.read();
    GyY = Wire.read() << 8 | Wire.read();
    GyZ = Wire.read() << 8 | Wire.read();
}

void setup() {
    Serial.begin(115200);
    WiFi.begin(ssid, password);
    
    while (WiFi.status() != WL_CONNECTED) {
        delay(2000);
        Serial.println("Connecting to WiFi...");
    }
    Serial.println("Connected to WiFi");



    udp.begin(serverPort);  // Initialize UDP communication on the desired port

    Serial.println("Setup MPU6050");
    setupMPU6050();
}

void loop() {
    static unsigned long lastTime = 0;
    unsigned long currentTime = millis();

    // Only send data every 1ms
    if (currentTime - lastTime >= 1) {
        readMPU6050();

        // Prepare data as binary format (14 bytes: 7 values, 2 bytes each)
        byte data[14];
        data[0] = (AcX >> 8) & 0xFF;
        data[1] = AcX & 0xFF;
        data[2] = (AcY >> 8) & 0xFF;
        data[3] = AcY & 0xFF;
        data[4] = (AcZ >> 8) & 0xFF;
        data[5] = AcZ & 0xFF;
        data[6] = (GyX >> 8) & 0xFF;
        data[7] = GyX & 0xFF;
        data[8] = (GyY >> 8) & 0xFF;
        data[9] = GyY & 0xFF;
        data[10] = (GyZ >> 8) & 0xFF;
        data[11] = GyZ & 0xFF;
        data[12] = (millis() >> 8) & 0xFF;  // Timestamp high byte
        data[13] = millis() & 0xFF;         // Timestamp low byte

        // Send data over UDP to the broadcast address
        udp.beginPacket(broadcastIP, serverPort);
        udp.write(data, sizeof(data));  // Send binary data
        udp.endPacket();  // End the packet and send it
        
        lastTime = currentTime;
    }
}
