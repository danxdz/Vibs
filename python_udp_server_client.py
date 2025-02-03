import os
import time
import socket
import csv
import numpy as np
import wave
import matplotlib.pyplot as plt



def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        # Connect to an external server (e.g., Google's DNS) to get the correct local IP
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
    except Exception:
        local_ip = '127.0.0.1'  # Fallback if the connection fails
    finally:
        s.close()
    return local_ip

#local_ip = get_local_ip()

#print(f"Local LAN IP Address: {local_ip}")


# Configuration for UDP communication
#UDP_IP = local_ip  # Use local IP address for listening
#UDP_PORT = 12345  # Port for UDP server

ESP_PORT = 12345
DISCOVER_MSG = b"DISCOVER_VIBS_SERVER"

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", ESP_PORT))
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)


# Create a new directory in the 'recordings' folder with a timestamp
def create_new_folder():
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    new_folder = os.path.join("recordings", timestamp)
    os.makedirs(new_folder, exist_ok=True)  # Create the folder, if it doesn't exist
    return new_folder

# Function to add additional info (data rate, axes, timestamps, etc.) to the plot
def add_plot_info(ax, data_rate, axis_name, start_timestamp, end_timestamp, num_points, sample_rate):
    # Calculate time duration
    time_duration = (end_timestamp - start_timestamp) / 1000  # Convert milliseconds to seconds
    mean_value = np.mean(data)
    median_value = np.median(data)
    std_value = np.std(data)
    
    # Create a detailed info string
    info = f"Data Rate: {data_rate:.2f} KB/s"
    info += f"\nAxis: {axis_name}"
    info += f"\nStart Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(start_timestamp / 1000))}"
    info += f"\nEnd Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(end_timestamp / 1000))}"
    info += f"\nDuration: {time_duration:.2f} seconds"
    info += f"\nNumber of Data Points: {num_points}"
    info += f"\nSample Rate: {sample_rate} Hz"
    info += f"\nMean: {mean_value:.2f}"
    info += f"\nMedian: {median_value:.2f}"
    info += f"\nStd Dev: {std_value:.2f}"

    # Add text annotation to the plot
    ax.text(0.05, 0.95, info, transform=ax.transAxes, fontsize=8, verticalalignment='top', bbox=dict(facecolor='white', alpha=0.7))

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

# Variable for last timestamp (to calculate the time difference between samples)
last_timestamp = None


# Keep sending discovery messages until ESP32 responds
print("🔍 Searching for ESP32 server...")
while True:
    sock.sendto(DISCOVER_MSG, ("192.168.4.1", ESP_PORT))  # Send to ESP hotspot
    try:
        sock.settimeout(1)  # 1-second timeout
        data, addr = sock.recvfrom(1024)
        if data == b"SERVER_ACK":
            print(f"✅ Connected to ESP32 at {addr[0]}")
            break
    except socket.timeout:
        print("⏳ No response, retrying...")



try:
    while True:
        # Receive data over UDP
        data, addr = sock.recvfrom(1024)  # Buffer size
        total_data_received += len(data)  # Add the length of the received data

        # Decode the received byte data to a string
        if len(data) > 0:
            try:
                # Decode byte data to string (assuming UTF-8 encoding)
                data_str = data.decode("utf-8").strip()

                # Process the string as CSV values
                raw_data = [int(value) for value in data_str.split(",")]

                # Extract Gyroscope data and timestamp
                GyX, GyY, GyZ, timestamp = raw_data  # Timestamp is included in the data

                # Sync with timestamp
                if last_timestamp is not None:
                    time_diff = timestamp - last_timestamp
                last_timestamp = timestamp

                # Append the parsed data along with timestamp
                collected_data.append([GyX, GyY, GyZ, timestamp])

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
    #send disconnect to esp


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
    max_val = np.max(np.abs(data))  # Calculate max value of the data for normalization
    if max_val == 0:
        print("⚠️ Warning: The data contains only zeros, no valid audio data to convert.")
        data = np.zeros_like(data)  # Prevent division by zero

    # Apply a gain factor to the data to increase amplitude
    gain_factor = 10  # Choose a value that works best for your data
    data = np.clip(np.int16((data / max_val) * 32767 * gain_factor), -32768, 32767)

    # Split data into X, Y, Z channels
    data_x = data[:, 0]
    data_y = data[:, 1]
    data_z = data[:, 2]

    # Create the mixed channel by averaging X, Y, Z
    data_mixed = np.mean(data, axis=1)  # Mix by averaging the three channels

    # Function to save WAV file for a given channel
    def save_wav(filename, channel_data, timestamps=None):

        timestamps = None  # Default to None if not provided
        try:
            # If timestamps are provided, calculate the sample rate based on the time difference
            if timestamps and len(timestamps) > 1:
                time_diff = timestamps[-1] - timestamps[0]
                sample_rate = len(timestamps) / time_diff if time_diff > 0 else 44100  # Fallback to 44100 if time_diff is zero
            else:
                sample_rate = 44100  # Default sample rate if timestamps are unavailable

            with wave.open(filename, "w") as wav_file:
                wav_file.setnchannels(1)  # Mono channel
                wav_file.setsampwidth(2)  # 2 bytes per sample (16-bit)
                wav_file.setframerate(sample_rate)  # Set dynamically calculated sample rate
                wav_file.writeframes(channel_data.tobytes())  # Write audio data to file
            print(f"✅ Created {filename} with {sample_rate} Hz sample rate")
            return sample_rate  # Return the sample rate for use in plots
        except Exception as e:
            print(f"❌ Error creating {filename}: {e}")
            return 44100  # Return a fallback sample rate in case of error

    # After collecting the data, extract timestamps from the collected data
    timestamps = [entry[3] for entry in collected_data]  # Assuming collected_data has a timestamp in the 4th element

    # Write to individual WAV files (X, Y, Z channels)
    for i, (axis_name, wav_filename) in enumerate(zip(["X", "Y", "Z"], [wav_filename_x, wav_filename_y, wav_filename_z])):
        save_wav(wav_filename, data[:, i], timestamps)

    # Write to mixed WAV file (combined X, Y, Z channels)
    save_wav(wav_filename_mixed, data_mixed, timestamps)

    print("🎉 WAV file conversion complete!")

    # Plot and save data
    # 1. Plot for X-axis (Red)
    plt.figure(figsize=(19.2, 10.8), dpi=600)
    fig, ax = plt.subplots()
    ax.plot(data_x, color='red', label='X-axis', linewidth=0.5, marker='o', markersize=2, markerfacecolor='black', markeredgewidth=0.5)
    ax.set_xlabel("Sample Number")
    ax.set_ylabel("Gyroscope Data")
    ax.set_title("Gyroscope Data (X-axis) over Time")
    ax.legend()
    ax.grid(True)

    # Save WAV for X-axis and get sample rate
    sample_rate_x = save_wav(wav_filename_x, data[:, 0], timestamps)  # Get the actual sample rate for X-axis

    # Adding information with the correct sample rate
    add_plot_info(ax, data_rate, 'X-axis', collected_data[0][3], collected_data[-1][3], len(data_x), sample_rate_x)

    # Save the plot for X-axis
    x_png_filename = get_next_filename("gyro_plot_X", ".png", session_folder)
    plt.savefig(x_png_filename, dpi=600)
    plt.close()
    print(f"✅ X-axis Plot saved to {x_png_filename}")

    # Repeat similar plotting and saving process for Y, Z, and Mixed data...

    # Plot for Y-axis (Green)
    plt.figure(figsize=(19.2, 10.8), dpi=600)
    fig, ax = plt.subplots()
    ax.plot(data_y, color='green', label='Y-axis', linewidth=0.1, marker='o', markersize=.2, markerfacecolor='black', markeredgewidth=.5)
    ax.set_xlabel("Sample Number")
    ax.set_ylabel("Gyroscope Data")
    ax.set_title("Gyroscope Data (Y-axis) over Time")
    ax.legend()
    ax.grid(True)

    # Save WAV for Y-axis and get sample rate
    sample_rate_y = save_wav(wav_filename_y, data[:, 1], timestamps)

    # Adding information with the correct sample rate
    add_plot_info(ax, data_rate, 'Y-axis', collected_data[0][3], collected_data[-1][3], len(data_y), sample_rate_y)

    # Save the plot for Y-axis
    y_png_filename = get_next_filename("gyro_plot_Y", ".png", session_folder)
    plt.savefig(y_png_filename, dpi=600)
    plt.close()
    print(f"✅ Y-axis Plot saved to {y_png_filename}")

    # Plot for Z-axis (Blue)
    plt.figure(figsize=(19.2, 10.8), dpi=600)
    fig, ax = plt.subplots()
    ax.plot(data_z, color='blue', label='Z-axis', linewidth=0.1, marker='o', markersize=.2, markerfacecolor='black', markeredgewidth=.5)
    ax.set_xlabel("Sample Number")
    ax.set_ylabel("Gyroscope Data")
    ax.set_title("Gyroscope Data (Z-axis) over Time")
    ax.legend()
    ax.grid(True)
    
    # Save WAV for Z-axis and get sample rate
    sample_rate_z = save_wav(wav_filename_z, data[:, 2], timestamps)

    # Adding information with the correct sample rate
    add_plot_info(ax, data_rate, 'Z-axis', collected_data[0][3], collected_data[-1][3], len(data_z), sample_rate_z)

    # Save the plot for Z-axis
    z_png_filename = get_next_filename("gyro_plot_Z", ".png", session_folder)
    plt.savefig(z_png_filename, dpi=600)
    plt.close()
    print(f"✅ Z-axis Plot saved to {z_png_filename}")

    # Plot for Mixed data (Combined X, Y, Z)
    plt.figure(figsize=(19.2, 10.8), dpi=600)
    fig, ax = plt.subplots()
    ax.plot(data_mixed, color='purple', label='Mixed (X+Y+Z)', linewidth=0.1, marker='o', markersize=.2, markerfacecolor='black', markeredgewidth=.5)
    ax.set_xlabel("Sample Number")
    ax.set_ylabel("Gyroscope Data")
    ax.set_title("Gyroscope Data (Mixed) over Time")
    ax.legend()
    ax.grid(True)

    # Save WAV for Mixed data and get sample rate
    sample_rate_mixed = save_wav(wav_filename_mixed, data_mixed, timestamps)

    # Adding information with the correct sample rate
    # Note: The data rate here is the total data rate, not individual channel rates
    # You can calculate individual channel rates if needed
    add_plot_info(ax, data_rate, 'Mixed (X+Y+Z)', collected_data[0][3], collected_data[-1][3], len(data_mixed), sample_rate_mixed)

    # Save the plot for Mixed data
    mixed_png_filename = get_next_filename("gyro_plot_Mixed", ".png", session_folder)
    plt.savefig(mixed_png_filename, dpi=600)
    plt.close()
    print(f"✅ Mixed Plot saved to {mixed_png_filename}")

    # Save all plots in a single png file
    plt.figure(figsize=(19.2, 10.8), dpi=600)
    fig, axs = plt.subplots(2, 2)
    axs[0, 0].imshow(plt.imread(x_png_filename))
    axs[0, 0].axis('off')
    axs[0, 1].imshow(plt.imread(y_png_filename))
    axs[0, 1].axis('off')
    axs[1, 0].imshow(plt.imread(z_png_filename))
    axs[1, 0].axis('off')
    axs[1, 1].imshow(plt.imread(mixed_png_filename))
    axs[1, 1].axis('off')
    plt.subplots_adjust(wspace=0.1, hspace=0.1)
    plt.savefig(png_filename, dpi=600)
    plt.close()

    print("🎉 All plots saved successfully!")


          





