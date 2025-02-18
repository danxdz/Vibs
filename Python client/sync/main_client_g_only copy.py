import socket
import time
import numpy as np
import threading
import csv
import os
import wave
import matplotlib.pyplot as plt

import scipy.io.wavfile as wav
import sounddevice as sd

from client_fft_g_only import DataHandler

import pandas as pd


# Default sample rate (adjust as needed)
DEFAULT_SAMPLE_RATE = 16000 
# Constants
ESP_PORT = 12345
CALIBRATION_SAMPLES = 200
CALIBRATION_THRESHOLD = 100
CALIBRATION_DELAY = 0.05
KEEP_ALIVE_INTERVAL = 1
DISCOVER_MSG = b"DISCOVER_VIBS_SERVER"
DEBUG = False

# Variables
gyro_offset = [0, 0, 0]
is_calibrated = False
connection_status = "🔴 Disconnected"
data_rate = 0
last_data_time = 0
last_timestamp = None
collected_data = []
stop_thread = False
capture_data = False



# UDP Socket Setup
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", ESP_PORT))
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)



# Keep Connection Alive
def keepConnected():
    global stop_thread
    while not stop_thread:
        try:
            sock.sendto(DISCOVER_MSG, ("192.168.4.1", ESP_PORT))
            time.sleep(KEEP_ALIVE_INTERVAL)
        except:
            break

# Receive Data Function
def receive_data():
    global connection_status, last_timestamp, data_rate, last_data_time, capture_data
    total_data_received = 0
    start_time = time.time()

    while not stop_thread:
        try:
            data, addr = sock.recvfrom(4096) # 1024 -> 4096 to avoid packet loss
            connection_status = "🟢 Connected"
            packets = data.decode().strip().split('\n')

            for packet in packets:
                values = packet.strip().split(',')
                if len(values) == 6:  # Expect 6 values now (GyX, GyY, GyZ, AcX, AcY, AcZ)
                    try:
                        gx, gy, gz, acx, acy, acz = map(int, values)
                        if capture_data:
                            collected_data.append([gx, gy, gz, acx, acy, acz, ts])  # Include accelerometer data

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

# Start Threads
threading.Thread(target=receive_data, daemon=True).start()
threading.Thread(target=keepConnected, daemon=True).start()

# Functions to Handle Data Saving
def create_new_folder():
    rec_folder = "rec"
    os.makedirs(rec_folder, exist_ok=True)
    return rec_folder

def save_to_csv(filename):
    print(f"💾 Saving to CSV: {filename}")
    with open(filename, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerows(collected_data)
       
        dh = DataHandler(filename)

        # Run the analysis (this will load the data, apply filters, and generate plots)
        dh.run_analysis()




def save_wav(filename, data, sample_rate):
    """ Saves vibration data as a WAV file with the correct time scaling. """
    try:
        with wave.open(filename, "w") as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit PCM
            wav_file.setframerate(int(sample_rate))  # Use calculated sample rate
            wav_file.writeframes(data.tobytes())
        print(f"✅ Created WAV file: {filename} at {sample_rate} Hz")
    except Exception as e:
        print(f"❌ Error creating WAV file: {e}")

def save_data_as_wav(csv_file, session_folder, session_name):
    """ Reads CSV data and saves it as a properly timed WAV file. """
    df = pd.read_csv(csv_file, delimiter=",", header=None)
    
    # Extract vibration data (assuming first 3 columns are X, Y, Z)
    timestamps = df.iloc[:, 3].values  # Fourth column is timestamp in ms
    data = df.iloc[:, :3].values  # First three columns are X, Y, Z values

    # Convert timestamps to seconds and compute sampling rate
    time_diffs = np.diff(timestamps) / 1000.0  # Convert ms to seconds
    avg_sample_rate = 1.0 / np.mean(time_diffs)  # Calculate average sample rate

    # Ensure valid playback sample rate
    standard_rates = [8000, 16000, 22050, 32000, 44100, 48000, 96000]
    avg_sample_rate = min(standard_rates, key=lambda x: abs(x - avg_sample_rate))

    print(f"📊 Adjusted sample rate for WAV output: {avg_sample_rate} Hz")


    # Ensure no zero max values to avoid division errors
    max_val = np.max(np.abs(data), axis=0)
    max_val[max_val == 0] = 1  # Avoid division by zero

    # Save combined WAV (All axes merged)
    data_normalized = np.int16(data.flatten() / np.max(max_val) * 32767)
    wav_filename = os.path.join(session_folder, f"{session_name}_gyro_data.wav")
    save_wav(wav_filename, data_normalized, avg_sample_rate)

    # Save individual WAV files for each axis
    for i, label in enumerate(["X", "Y", "Z"]):
        axis_data = np.int16(data[:, i] / max_val[i] * 32767)
        wav_filename = os.path.join(session_folder, f"{session_name}_{label}_gyro_data.wav")
        save_wav(wav_filename, axis_data, avg_sample_rate)

        # Optional: Play audio for each axis at real-time speed
        print(f"🎧 Playing {label}-axis vibration sound at {avg_sample_rate:.2f} Hz...")
        sd.play(axis_data, avg_sample_rate)
        sd.wait()

    print("✅ WAV files saved successfully!")





# User Control Functions
def stop_data_collection():
    global stop_thread, capture_data
    stop_thread = True
    capture_data = False
    print("\nStopping data collection...")

def start_data_capture():
    global capture_data
    capture_data = True
    print("📡 Data capture started. Collecting data...")

def generate_plots(session_folder, session_name):
    # Function to generate and save plots
    if len(collected_data) == 0:
        print("⚠️ No data to plot.")
        return

    data = np.array(collected_data)
    time_data = np.arange(len(data))

    # Combined plot
    fig, axs = plt.subplots(3, 1, figsize=(10, 8))
    axs[0].plot(time_data, data[:, 0], label="X-axis", color="red", linewidth=0.2)

    axs[1].plot(time_data, data[:, 1], label="Y-axis", color="green", linewidth=0.2)
    axs[2].plot(time_data, data[:, 2], label="Z-axis", color="blue", linewidth=0.2)

    for ax in axs:
        ax.legend()
        ax.grid(True)
        ax.set_xlabel("Samples")
        ax.set_ylabel("Gyroscope Value")

    plot_filename = os.path.join(session_folder, f"{session_name}_gyro_plot.png")
    plt.savefig(plot_filename, dpi=600)
    plt.close()
    print(f"✅ Combined Plot saved to {plot_filename}")

    # Individual plots for each axis
    # X, Y, Z and red, green, blue
    for i, label in  enumerate(["X", "Y", "Z"]):
        fig, ax = plt.subplots(figsize=(10, 4))
        if i == 0:
            ax.plot(time_data, data[:, i], label=f"{label}-axis", color="red", linewidth=0.2)
        elif i == 1:
            ax.plot(time_data, data[:, i], label=f"{label}-axis", color="green", linewidth=0.2)
        else:
            ax.plot(time_data, data[:, i], label=f"{label}-axis", color="blue", linewidth=0.2)

        ax.legend()
        ax.grid(True)
        ax.set_xlabel("Samples")
        ax.set_ylabel(f"{label} Gyroscope Value")

        plot_filename = os.path.join(session_folder, f"{session_name}_{label}_gyro_plot.png")
        plt.savefig(plot_filename, dpi=600)
        plt.close()
        print(f"✅ {label}-axis Plot saved to {plot_filename}")




# Main Program Logic
if __name__ == "__main__":
    try:
        # Wait for connection to be established before starting
        print("📡 Waiting for connection...")
        while connection_status != "🟢 Connected":
            time.sleep(1)  # Keep checking for connection

        print("🟢 Connected. Press Enter to start/stop data capture. Press Ctrl+C to quit.")

        while True:
            user_input = input()  # Wait for Enter key press

            if capture_data:
                stop_data_collection()

                # Prompt for session name after finishing recording
                session_name = input("Enter a name for this recording session: ").strip()
                if not session_name:
                    session_name = time.strftime("%Y%m%d_%H%M%S", time.localtime())  # Default to timestamp

                # Create folder inside "rec"
                rec_folder = create_new_folder()
                session_folder = os.path.join(rec_folder, session_name)
                os.makedirs(session_folder, exist_ok=True)

                # Save data
                csv_filename = os.path.join(session_folder, f"{session_name}_gyro_data.csv")
                save_to_csv(csv_filename)
                generate_plots(session_folder, session_name)
                save_data_as_wav(csv_filename, session_folder, session_name)  # Save as WAV
                print(f"🎉 Data capture stopped and saved as {session_name}!")
                capture_data = None
            else:
                # check if connected
                if connection_status == "🔴 Disconnected":
                    print("🔴 Disconnected. Press Enter to start data capture.")
                    continue
                
                start_data_capture()

    except KeyboardInterrupt:
        stop_data_collection()
        print("🎉 Data collection complete!")
