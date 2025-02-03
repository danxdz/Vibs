import os
import time
import socket
import csv
import numpy as np
import wave
import matplotlib.pyplot as plt

# UDP configuration
ESP_IP = "192.168.4.1"   # Default ESP32 hotspot IP
ESP_PORT = 12345         # UDP port
DISCOVER_MSG = b"DISCOVER_VIBS_SERVER"
ACK_MSG = b"SERVER_ACK"

# Create UDP socket and bind to all interfaces
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", ESP_PORT))
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

def send_discovery():
    """ Send discovery message to find ESP32. """
    print("🔍 Sending discovery message...")
    sock.sendto(DISCOVER_MSG, ("192.168.4.1", ESP_PORT))  # Use broadcast

def wait_for_ack(timeout=1):
    """ Wait for server acknowledgment. If received, update ESP_IP. """
    sock.settimeout(timeout)
    try:
        data, addr = sock.recvfrom(1024)
        if data == ACK_MSG:
            global ESP_IP
            ESP_IP = addr[0]  # Update to the actual ESP IP
            print(f"✅ Connected to server at {ESP_IP}")
            return True
    except socket.timeout:
        print("⏳ No ACK received.")
    return False

def establish_connection():
    """ Keep sending discovery messages until we receive an ACK. """
    while True:
        send_discovery()
        if wait_for_ack(timeout=1):
            return
        time.sleep(1)

# First, try to establish the connection
establish_connection()

print("📡 Now receiving sensor data... (Press Ctrl+C to stop)")

# Data collection section (for later processing, e.g., saving to CSV/WAV)
collected_data = []

# Set an overall data timeout period (e.g., 5 seconds) for re-discovery
DATA_TIMEOUT = 5  # seconds
last_data_time = time.time()

try:
    while True:
        try:
            # Set a timeout for receiving sensor data
            sock.settimeout(1)
            data, addr = sock.recvfrom(4096)
            last_data_time = time.time()  # Update last data received time

            # Process received sensor data
            data_str = data.decode("utf-8").strip()

            # Expecting CSV: GyX,GyY,GyZ,timestamp
            raw_data = [int(value) for value in data_str.split(",")]
            if len(raw_data) == 4:
                GyX, GyY, GyZ, timestamp = raw_data
                collected_data.append([GyX, GyY, GyZ, timestamp])
                print(f"GyX={GyX}, GyY={GyY}, GyZ={GyZ}")
            else:
                print("❌ Received malformed data.")
        
        except socket.timeout:
            # Check if we've exceeded our data timeout
            if time.time() - last_data_time > DATA_TIMEOUT:
                print("⚠️ Data timeout. Re-establishing connection...")
                establish_connection()
                last_data_time = time.time()
            continue

except KeyboardInterrupt:
    print("\nStopping capture...")
    sock.close()
    print("✅ UDP closed.")
