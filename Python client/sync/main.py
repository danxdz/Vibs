
#electroniccats/MPU6050@^1.4.1

import threading
import time
import numpy as np
import os
import csv
from udp_mpu6050_client import UDPSensorClient
from visualization3d import start_visualization, update_gyro_data
from save_data import create_new_folder, save_to_csv, generate_plots, process_realtime_wav

# Global variables
gyroscope_data = [0, 0, 0]
acceleration_data = [0, 0, 0]
stop_thread = False
capture_data = False
collected_data = []

gyro_offset = [0, 0, 0]
accel_offset = [0, 0, 0]

def calibrate_sensors(client):
    """Calibrate gyroscope and accelerometer by averaging initial readings."""
    global gyro_offset, accel_offset
    
    gyro_samples = []
    accel_samples = []
    
    print("⏳ Calibrating sensors... Keep the device **STILL**!")
    
    for _ in range(100):
        gyro_data, accel_data, _ = client.receive_data()
        if gyro_data and accel_data:
            gyro_samples.append(gyro_data)
            accel_samples.append(accel_data)
    
    gyro_offset = np.mean(gyro_samples, axis=0)
    accel_offset = np.mean(accel_samples, axis=0)
    
    print(f"✅ Gyro Offset: {gyro_offset}")
    print(f"✅ Accel Offset: {accel_offset}")

def receive_data(client):
    """Thread function to receive sensor data."""
    global gyroscope_data, acceleration_data, collected_data, capture_data

    while not stop_thread:
        gyro_data, accel_data, timestamp = client.receive_data()
        if gyro_data and accel_data:
            # Use calibrated data for visualization
            gyroscope_data = [gyro_data[i] - gyro_offset[i] for i in range(3)]
            acceleration_data = [accel_data[i] - accel_offset[i] for i in range(3)]
            update_gyro_data(acceleration_data)
            # Save raw data only
            if capture_data:
                collected_data.append([*gyro_data, *accel_data, timestamp])

def start_capture():
    """Start capturing data."""
    global capture_data, collected_data
    collected_data = []
    capture_data = True
    print("▶️ Data capture started...")

def stop_capture():
    """Stop capturing and save data."""
    global capture_data
    capture_data = False
    print("⏹️ Data capture stopped.")
    
    session_name = input("Enter a name for this recording session: ").strip()
    if not session_name:
        session_name = time.strftime("%Y%m%d_%H%M%S")
    
    rec_folder = create_new_folder()
    session_folder = os.path.join(rec_folder, session_name)
    os.makedirs(session_folder, exist_ok=True)
    
    csv_filename = os.path.join(session_folder, f"{session_name}_raw_data.csv")
    save_to_csv(csv_filename, collected_data)
    generate_plots(session_folder, session_name, collected_data)
    process_realtime_wav(csv_filename, session_folder, session_name)
    print(f"🎉 Data saved as {session_name}!")
    
    
def get_sensor_data():
    """Return gyroscope and accelerometer raw data for visualization."""
    if not gyroscope_data or not acceleration_data:
        return (0, 0, 0, 0, 0, 0)  # Ensure the correct structure
    return (*gyroscope_data, *acceleration_data)


def main():
    """Main function to start the UDP client and visualization."""
    global stop_thread
    
    client = UDPSensorClient(local_ip="192.168.42.2", server_ip="192.168.4.1", server_port=12345)
    
    if not client.discover_server():
        print("❌ Server not found. Exiting...")
        return

    print("📡 Connected to ESP32. Starting visualization...")
    
    udp_thread = threading.Thread(target=receive_data, args=(client,), daemon=True)
    udp_thread.start()
    
    calibrate_sensors(client)
    start_visualization()
    
    try:
        while True:
            input("Press Enter to START/STOP capture, or Ctrl+C to exit.")
            if capture_data:
                stop_capture()
            else:
                start_capture()
    except KeyboardInterrupt:
        print("🚪 Exiting program.")
        stop_thread = True
        udp_thread.join()
        client.close()

if __name__ == "__main__":
    main()
