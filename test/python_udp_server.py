import os
import time
import socket
import csv
import numpy as np
import wave
import matplotlib.pyplot as plt

# Configuration for UDP communication
UDP_IP = "192.168.1.179"  # The IP address of your Python machine
UDP_PORT = 12345  # Port for UDP server

# Set up the UDP server
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

# Create a new directory in the 'recordings' folder with a timestamp
def create_new_folder():
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    new_folder = os.path.join("recordings", timestamp)
    os.makedirs(new_folder, exist_ok=True)  # Create the folder, if it doesn't exist
    return new_folder

# Function to generate unique filenames
def get_next_filename(base_name, extension, folder):
    i = 1
    while os.path.exists(f"{folder}/{base_name}_{i}{extension}"):
        i += 1
    return f"{folder}/{base_name}_{i}{extension}"

# Create the folder for this session
session_folder = create_new_folder()

# Initialize filenames for CSV and WAV files inside the session folder
csv_filename = get_next_filename("gyro_data", ".csv", session_folder)
wav_filename_x = get_next_filename("gyro_audio_X", ".wav", session_folder)
wav_filename_y = get_next_filename("gyro_audio_Y", ".wav", session_folder)
wav_filename_z = get_next_filename("gyro_audio_Z", ".wav", session_folder)
wav_filename_mixed = get_next_filename("gyro_audio_Mixed", ".wav", session_folder)
png_filename = get_next_filename("gyro_plot", ".png", session_folder)

print(f"📄 CSV File: {csv_filename}")
print(f"🎵 Audio Files: {wav_filename_x}, {wav_filename_y}, {wav_filename_z}, {wav_filename_mixed}")
print(f"📊 PNG Plot: {png_filename}")

# Data collection in memory
collected_data = []
print("📡 Waiting for data... Press Ctrl+C to stop.")

# Variables to calculate data rate
start_time = time.time()
total_data_received = 0
interval = 0.1  # Interval to measure data rate in seconds

try:
    while True:
        # Receive data over UDP
        data, addr = sock.recvfrom(1024)  # Buffer size
        total_data_received += len(data)  # Add the length of the received data

        # Check if received data length is as expected (14 bytes or more)
        if len(data) >= 14:
            # If data length is 14 bytes, interpret it as 7 values (2 bytes each)
            try:
                # Extract the raw sensor data
                raw_data = [int.from_bytes(data[i:i+2], byteorder='big', signed=True) for i in range(0, 14, 2)]
                # Append the parsed data (AcX, AcY, AcZ, GyX, GyY, GyZ, timestamp)
                collected_data.append(raw_data)

            except Exception as e:
                print(f"Error parsing data: {e}")
                continue

        # Measure data rate every interval seconds
        elapsed_time = time.time() - start_time
        if elapsed_time >= interval:
            data_rate = total_data_received / elapsed_time  # Data rate in bytes per second
            print(f"Data Rate: {data_rate / 1024:.2f} KB/s")  # Print the data rate in KB/s

            # Reset counters for the next interval
            start_time = time.time()
            total_data_received = 0

except KeyboardInterrupt:
    print("\nStopping capture...")
    sock.close()
    print("✅ UDP closed.")

    # Save to CSV after capture
    print("💾 Saving to CSV...")
    with open(csv_filename, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerows(collected_data)

    # Convert to WAV
    print("🎵 Converting to WAV...")

    # Convert collected data to numpy array
    data = np.array(collected_data, dtype=np.float32)

    # Normalize data for audio (0 to 32767 for 16-bit audio)
    # Ensure the data is within bounds for 16-bit PCM
    max_val = np.max(np.abs(data))  # Calculate max value of the data for normalization
    if max_val == 0:
        print("⚠️ Warning: The data contains only zeros, no valid audio data to convert.")
        data = np.zeros_like(data)  # Prevent division by zero

    # Scale and clip the data to be within the 16-bit PCM range
    data = np.clip(np.int16((data / max_val) * 32767), -32768, 32767)

    # Split data into X, Y, Z channels
    data_x = data[:, 0]
    data_y = data[:, 1]
    data_z = data[:, 2]

    # Create the mixed channel by averaging X, Y, Z
    data_mixed = np.mean(data, axis=1)  # Mix by averaging the three channels

    # Function to save WAV file for a given channel
    def save_wav(filename, channel_data):
        try:
            with wave.open(filename, "w") as wav_file:
                wav_file.setnchannels(1)  # Mono channel
                wav_file.setsampwidth(2)  # 2 bytes per sample (16-bit)
                wav_file.setframerate(100)  # Replace with actual sampling rate
                wav_file.writeframes(channel_data.tobytes())  # Write audio data to file
            print(f"✅ Created {filename}")
        except Exception as e:
            print(f"❌ Error creating {filename}: {e}")

    # Write to individual WAV files (X, Y, Z channels)
    for i, (axis_name, wav_filename) in enumerate(zip(["X", "Y", "Z"], [wav_filename_x, wav_filename_y, wav_filename_z])):
        save_wav(wav_filename, data[:, i])

    # Write to mixed WAV file (combined X, Y, Z channels)
    save_wav(wav_filename_mixed, data_mixed)

    print("🎉 WAV file conversion complete!")

    # Generate the plot
    print("📊 Creating Plot...")

    # Plot the filtered channels with small black dots for regular channels and orange dots for mixed
    plt.figure(figsize=(19.2, 10.8), dpi=200)  # 4K resolution: 3840x2160 pixels with a higher DPI
    plt.plot(data_x, color='red', label='X-axis', linewidth=0.1, marker='o', markersize=.2, markerfacecolor='black', markeredgewidth=.5)
    plt.plot(data_y, color='green', label='Y-axis', linewidth=0.1, marker='o', markersize=.2, markerfacecolor='black', markeredgewidth=.5)
    plt.plot(data_z, color='blue', label='Z-axis', linewidth=0.05, marker='o', markersize=.1, markerfacecolor='black', markeredgewidth=.5)
    plt.plot(data_mixed, color='black', label='Mixed Channel', linestyle='--', linewidth=0.05, marker='o', markersize=.1, markerfacecolor='orange', markeredgewidth=.5)

    plt.title("Gyroscope Data - X, Y, Z, and Mixed Channel")
    plt.xlabel("Sample Time")
    plt.ylabel("Amplitude")
    plt.legend()

    # Save the plot as a PNG file with 4K resolution
    plt.savefig(png_filename, dpi=200)  # Increase DPI to make the plot sharper
    print(f"✅ Saved plot to {png_filename}")

    print("🚀 Processing complete!")
