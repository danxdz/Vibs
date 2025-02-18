import socket
import time
import numpy as np
import threading
import csv
import os
import wave
import matplotlib.pyplot as plt
import sounddevice as sd
import pandas as pd

# -----------------------------
# Global Constants and Variables
# -----------------------------
DEFAULT_SAMPLE_RATE = 44100  # Default sample rate for WAV conversion
ESP_PORT = 12345
CALIBRATION_SAMPLES = 200
CALIBRATION_THRESHOLD = 100
CALIBRATION_DELAY = 0.05
KEEP_ALIVE_INTERVAL = 1
DISCOVER_MSG = b"DISCOVER_VIBS_SERVER"
DEBUG = False

gyro_offset = [0, 0, 0]
acc_offset = [0, 0, 0]
is_calibrated = False
connection_status = "🔴 Disconnected"
data_rate = 0
last_data_time = 0
last_timestamp = None
collected_data = []  # Will hold rows of data: [GyX, GyY, GyZ, AcX, AcY, AcZ, timestamp]
stop_thread = False
capture_data = False

# -----------------------------
# Thread Safety Lock
# -----------------------------
data_lock = threading.Lock()  # Define a lock for shared data access

# -----------------------------
# UDP Socket Setup
# -----------------------------
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", ESP_PORT))
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

# -----------------------------
# Keep Connection Alive
# -----------------------------
def keepConnected():
    global stop_thread
    while not stop_thread:
        try:
            # Change IP address as needed (your ESP32 hotspot IP)
            sock.sendto(DISCOVER_MSG, ("192.168.4.1", ESP_PORT))
            time.sleep(KEEP_ALIVE_INTERVAL)
        except Exception as e:
            print(f"KeepConnected error: {e}")
            break

# -----------------------------
# UDP Data Reception
# -----------------------------
def start_data_capture():
    global capture_data
    capture_data = True
    print("📡 Data capture started. Collecting data...")

def stop_data_collection():
    global stop_thread, capture_data
    stop_thread = True
    capture_data = False
    print("\nStopping data collection...")

stop_event = threading.Event()

def receive_data():
    global connection_status, last_timestamp, data_rate, last_data_time, capture_data
    total_data_received = 0
    start_time = time.time()

    while not stop_event.is_set():
        try:
            data, addr = sock.recvfrom(4096)  # Use a large buffer size
            connection_status = "🟢 Connected"
            packets = data.decode().strip().split('\n')

            for packet in packets:
                values = packet.strip().split(',')
                if len(values) != 7:
                    #print(f"Skipping malformed packet: {packet}")
                    continue

                try:
                    gx, gy, gz, acx, acy, acz, ts = map(int, values)
                    if capture_data:
                        with data_lock:  # Ensure thread-safe appending of data
                            collected_data.append([gx, gy, gz, acx, acy, acz, ts])
                    total_data_received += 1
                    elapsed = time.time() - start_time
                    if elapsed >= 1.0:
                        data_rate = total_data_received / elapsed
                        total_data_received = 0
                        start_time = time.time()
                except ValueError:
                    continue
        except Exception as e:
            print(f"Error: {e}")
            connection_status = "🔴 Disconnected"

# -----------------------------
# Start Threads for UDP
# -----------------------------
threading.Thread(target=receive_data, daemon=True).start()
threading.Thread(target=keepConnected, daemon=True).start()

# -----------------------------
# Functions to Save Data & Analysis
# -----------------------------
def create_new_folder():
    rec_folder = "rec"
    os.makedirs(rec_folder, exist_ok=True)
    return rec_folder

def save_to_csv(filename):
    print(f"💾 Saving to CSV: {filename}")
    mode = 'w' if not os.path.exists(filename) else 'a'
    with open(filename, mode, newline="") as file:
        writer = csv.writer(file)
        if mode == 'w':
            writer.writerow(["GyX", "GyY", "GyZ", "AcX", "AcY", "AcZ", "Timestamp"])  # Write header only if new file
        writer.writerows(collected_data)

def normalize_to_16bit(data):
    max_val = np.max(np.abs(data))
    if max_val == 0:
        return np.int16(data)  # Avoid division by zero
    return np.int16(data / max_val * 32767)

def save_wav(filename, data, sample_rate, timestamps):
    """Saves vibration data as a WAV file with correct time scaling."""
    try:
        # Calculate time diffs to match the sample rate properly
        time_diffs = np.diff(timestamps) / 1000.0  # Convert milliseconds to seconds
        time_interval = np.mean(time_diffs)
        
        # Rescale data according to the time interval between readings
        num_samples = int(len(data) * time_interval * sample_rate)
        rescaled_data = np.interp(np.linspace(0, len(data), num_samples), np.arange(len(data)), data)

        # Normalize to 16-bit PCM
        rescaled_data = normalize_to_16bit(rescaled_data)

        with wave.open(filename, "w") as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit PCM
            wav_file.setframerate(int(sample_rate))
            wav_file.writeframes(rescaled_data.tobytes())
        
        print(f"✅ Created WAV file: {filename} at {sample_rate} Hz")
    except Exception as e:
        print(f"❌ Error creating WAV file: {e}")

def save_data_as_wav(csv_file, session_folder, session_name):
    """Reads CSV data and saves it as properly timed WAV files using timestamps."""
    df = pd.read_csv(csv_file, delimiter=",")
    gyro_data = df.iloc[:, :3].values  # Gyroscope data (columns 0-2)
    acc_data = df.iloc[:, 3:6].values  # Accelerometer data (columns 3-5)
    timestamps = df.iloc[:, 6].values  # Timestamps in milliseconds (column 6)

    # Calculate the sample rate from timestamps
    time_diffs = np.diff(timestamps) / 1000.0  # Convert milliseconds to seconds
    avg_sample_rate = 1.0 / np.mean(time_diffs)  # Average sample rate in Hz

    # Adjust to a standard sample rate (e.g., 44100 Hz)
    standard_rates = [8000, 16000, 22050, 32000, 44100, 48000, 96000]
    adjusted_sample_rate = min(standard_rates, key=lambda x: abs(x - avg_sample_rate))
    print(f"📊 Adjusted sample rate for WAV output: {adjusted_sample_rate} Hz")

    # Save individual WAV files for each axis (Gyro and Accel)
    axis_labels = ["GyX", "GyY", "GyZ", "AcX", "AcY", "AcZ"]
    for i, label in enumerate(axis_labels):
        if i < 3:
            axis_data = normalize_to_16bit(gyro_data[:, i])  # Gyro data
        else:
            axis_data = normalize_to_16bit(acc_data[:, i - 3])  # Accel data

        # Save as WAV file (now passing timestamps to save_wav)
        wav_filename = os.path.join(session_folder, f"{session_name}_{label}.wav")
        save_wav(wav_filename, axis_data, adjusted_sample_rate, timestamps)  # Passing timestamps here
        print(f"✅ Saved WAV file: {wav_filename}")

    print("🎉 All WAV files saved successfully!")


def generate_plots(session_folder, session_name):
    if not collected_data:  # More explicit check for empty data
        print("⚠️ No data to plot.")
        return

    data = np.array(collected_data)
    time_data = np.arange(len(data))
    
    # Combined plot for gyro and accelerometer data (columns 0-5)
    fig, axs = plt.subplots(6, 1, figsize=(10, 12))
    axis_labels = ["GyX", "GyY", "GyZ", "AcX", "AcY", "AcZ"]
    
    for i, label in enumerate(axis_labels):
        axs[i].plot(time_data, data[:, i], label=label, linewidth=0.2)
        axs[i].legend()
        axs[i].grid(True)
        axs[i].set_xlabel("Samples")
        axs[i].set_ylabel(f"{label} Value")
    
    plot_filename = os.path.join(session_folder, f"{session_name}_plot.png")
    plt.savefig(plot_filename, dpi=600)
    plt.close()
    print(f"✅ Plot saved to {plot_filename}")

# -----------------------------
# Main Program Logic
# -----------------------------
if __name__ == "__main__":
    try:
        print("📡 Waiting for connection...")
        while connection_status != "🟢 Connected":
            time.sleep(1)

        print("🟢 Connected. Press Enter to start/stop data capture. Press Ctrl+C to quit.")
        while True:
            user_input = input()  # Wait for Enter key press

            if capture_data:
                stop_data_collection()
                session_name = input("Enter a name for this recording session: ").strip()
                if not session_name:
                    session_name = time.strftime("%Y%m%d_%H%M%S", time.localtime())
                rec_folder = create_new_folder()
                session_folder = os.path.join(rec_folder, session_name)
                os.makedirs(session_folder, exist_ok=True)

                csv_filename = os.path.join(session_folder, f"{session_name}_gyro_acc_data.csv")
                save_to_csv(csv_filename)
                generate_plots(session_folder, session_name)
                save_data_as_wav(csv_filename, session_folder, session_name)
                print(f"🎉 Data capture stopped and saved as {session_name}!")
                capture_data = False
            else:
                if connection_status == "🔴 Disconnected":
                    print("🔴 Disconnected. Press Enter to start data capture.")
                    continue
                start_data_capture()
    except KeyboardInterrupt:
        stop_data_collection()
        print("🎉 Data collection complete!")
