#include <Arduino.h>
#include <Servo.h>

Servo ESC1;  // Create ESC object


bool manualControl = false;  // Flag for manual mode

// Original throttle constants
const int minThrottle = 1570;
const int maxThrottle = 1800;
const int interval = 2000;
const int endInterval = 10000;  // 10-second wait after a cycle before restarting

// New music constants
const int NOTE_LOW = 1600;
const int NOTE_MID = 1700;
const int NOTE_HIGH = 1800;
const int BEAT = 200;  // Basic timing unit

int step = (maxThrottle - minThrottle) / 10;  // Make 10 speed steps

void playPattern() {
    Serial.println("\n--- Playing Pattern ---");
    
    // Simple ascending pattern
    int notes[] = {NOTE_LOW, NOTE_MID, NOTE_HIGH, NOTE_MID, NOTE_LOW};
    int durations[] = {BEAT, BEAT, BEAT*2, BEAT, BEAT*2};
    
    for(int i = 0; i < 5; i++) {
        ESC1.writeMicroseconds(notes[i]);
        delay(durations[i]);
        ESC1.writeMicroseconds(minThrottle);
        delay(50);  // Brief pause between notes
    }
    
    ESC1.writeMicroseconds(minThrottle);
    Serial.println("--- Pattern Complete ---");
}

void rampSpeed() {
    Serial.println("\n--- Starting Ramp-Up Process ---");
    // Ramp Up: Increase speed by steps
    for (int speed = minThrottle; speed <= maxThrottle; speed += step) {
        ESC1.writeMicroseconds(speed);
        Serial.print("Ramping up: ");
        Serial.print("Throttle Position: ");
        Serial.print(speed);
        Serial.print(" (Microseconds), ");
        Serial.print("Current Speed: ");
        Serial.print(map(speed, minThrottle, maxThrottle, 0, 100));
        Serial.println("%");
        delay(interval);
    }

    Serial.println("\n--- Reached Max Speed, Maintaining for 2 seconds ---");

    
    Serial.println("\n--- Starting Ramp-Down Process ---");
    // Ramp Down: Decrease speed by steps
    for (int speed = maxThrottle; speed >= minThrottle; speed -= step) {
        ESC1.writeMicroseconds(speed);
        Serial.print("Ramping down: ");
        Serial.print("Throttle Position: ");
        Serial.print(speed);
        Serial.print(" (Microseconds), ");
        Serial.print("Current Speed: ");
        Serial.print(map(speed, minThrottle, maxThrottle, 0, 100));
        Serial.println("%");
        delay(interval);
    }

    ESC1.writeMicroseconds(minThrottle);
    Serial.println("\n--- Ramp Down Complete, Returning to Idle ---");
}

void setup() {
    Serial.begin(115200);
    ESC1.attach(9);  // Attach ESC to pin 9
    delay(2000);     // Wait for ESC to initialize
    ESC1.writeMicroseconds(maxThrottle);
    delay(10);
    ESC1.writeMicroseconds(minThrottle);
    delay(1000);

    Serial.println("\n--- ESC Initialization Complete ---");
    Serial.println("Press Enter to start ramping sequence");
}


void loop() {
    if (Serial.available() > 0) {
        char input = Serial.read();
        if (input == '\n' || input == '\r') {
            Serial.println("Starting ramp sequence...");
            rampSpeed();
            Serial.println("\n--- Press Enter for ramp, Space for pattern ---");
        }
        else if (input == ' ') {
            Serial.println("Playing pattern...");
            playPattern();
            Serial.println("\n--- Press Enter for ramp, Space for pattern ---");
        }
        
        // Clear buffer
        while(Serial.available()) { 
            Serial.read();
        }
    }
    
    if (!manualControl) {
        ESC1.writeMicroseconds(minThrottle);
    }
} 