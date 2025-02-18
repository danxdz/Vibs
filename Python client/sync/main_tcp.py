
import threading
import time
import numpy as np
import os
import struct
import msvcrt  # Windows-only module for non-blocking keyboard input

from tcp_mpu6050_client_dual import TCPSensorClient  # Updated TCP client
from save_data import create_new_folder, save_to_csv, generate_plots, process_realtime_wav
from visualization_plot import start_sensor_visualization, update_sensor_data  # Import the real-time plotting function
from visualization3d import start_visualization3d, update_gyro_data
from fft_visualization import start_fft_visualization, update_fft_data



# Global variables for sensor data
gyroscope_data = [0, 0, 0]
acceleration_data = [0, 0, 0]
stop_thread = False
capture_data = False
collected_data = []

gyro_offset = [0, 0, 0]
accel_offset = [0, 0, 0]

def calibrate_sensors(client):
    """Calibrate gyroscope and accelerometer using multiple packets."""
    global gyro_offset, accel_offset
    gyro_samples = []
    accel_samples = []
    
    print("⏳ Calibrating sensors... Keep the device **STILL**!")
    
    for _ in range(100):  # Collect 500 packets
        captures = client.receive_data()
        if captures is None:
            continue

        for capture in captures:
            GyX, GyY, GyZ, AcX, AcY, AcZ, timestamp, cps, num = capture
            gyro_samples.append([GyX, GyY, GyZ])
            accel_samples.append([AcX, AcY, AcZ])
    
    if gyro_samples and accel_samples:
        gyro_offset = np.mean(gyro_samples, axis=0)
        accel_offset = np.mean(accel_samples, axis=0)
        print(f"✅ Gyro Offset: {gyro_offset}")
        print(f"✅ Accel Offset: {accel_offset}")
    else:
        print("⚠️ Calibration failed due to missing data.")

def receive_data_thread(client):
    """Continuously receive data and update global sensor values."""
    global gyroscope_data, acceleration_data, collected_data
    while not stop_thread:
        captures = client.receive_data()
        if captures is not None:
            for capture in captures:
                GyX, GyY, GyZ, AcX, AcY, AcZ, timestamp, cps, num = capture
                
                # Apply calibration offsets
                gyroscope_data = [GyX - gyro_offset[0], GyY - gyro_offset[1], GyZ - gyro_offset[2]]
                acceleration_data = [AcX - accel_offset[0], AcY - accel_offset[1], AcZ - accel_offset[2]]

                update_gyro_data(gyroscope_data)  # ✅ Update visualization
                #update_fft_data([GyX, GyY, GyZ])
                
                #update_sensor_data([GyX, GyY, GyZ], [AcX, AcY, AcZ])

                update_sensor_data(gyroscope_data, acceleration_data)

                # If capture is enabled, store the raw data
                if capture_data:
                    collected_data.append([GyX, GyY, GyZ, AcX, AcY, AcZ, timestamp, cps, num])



def keyboard_listener():
    """Listen for Enter key to toggle data capture."""
    global capture_data
    while not stop_thread:
        if msvcrt.kbhit():
            key = msvcrt.getch()
            if key == b'\r':  # Enter key pressed
                if capture_data:
                    stop_capture()
                else:
                    start_capture()
        time.sleep(0.1)

def start_capture():
    """Start capturing data."""
    global capture_data, collected_data
    collected_data = []  # Reset data
    capture_data = True
    print("▶️ Data capture started...")

def stop_capture():
    """Stop capturing data and save it."""
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

    if len(collected_data) >= 12:  # Ensure enough data for filtering
        generate_plots(session_folder, session_name, collected_data)
        process_realtime_wav(csv_filename, session_folder, session_name)
    else:
        print("⚠️ Not enough data for filtering, skipping processing.")

    print(f"🎉 Data saved as {session_name}!")



def main():
    global stop_thread
    client = None

    while client is None:
        try:
            client = TCPSensorClient(server_ip="192.168.4.1", server_port=12345)
            if client.sock is None:
                raise ConnectionError("❌ Connection to server failed.")
            print("📡 Connected to ESP32. Starting visualization...")
        except Exception as e:
            print(f"🔄 Retrying connection in 5 seconds... Error: {e}")
            time.sleep(5)

    # Calibrate sensors before enabling capture
    calibrate_sensors(client)

    # Start the data receiving thread
    tcp_thread = threading.Thread(target=receive_data_thread, args=(client,), daemon=True)
    tcp_thread.start()
   
    # Start visualization in its own thread
    vis_thread = threading.Thread(target=start_visualization3d, daemon=True)
    vis_thread.start()

    # Start a non-blocking keyboard listener thread
    kb_thread = threading.Thread(target=keyboard_listener, daemon=True)
    kb_thread.start()

    # Start FFT visualization 
    ##fft_thread = threading.Thread(target=start_fft_visualization, daemon=True)
    #fft_thread.start()
    
    analizer_thread = threading.Thread(target=start_sensor_visualization, daemon=True)
    analizer_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("🚪 Exiting program.")
        stop_thread = True
        tcp_thread.join()
        client.close()


if __name__ == "__main__":
    main()
