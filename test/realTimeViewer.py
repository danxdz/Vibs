import socket
import time
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque
import threading

# Constants
ESP_PORT = 12345
DISCOVER_MSG = b"DISCOVER_VIBS_SERVER"
KEEP_ALIVE_INTERVAL = 3  # seconds
PLOT_WINDOW = 500  # Reduced number of samples for smoother updates
BATCH_SIZE = 10  # Number of samples per UDP packet (same as ESP32)
MAX_SAMPLES = 2000  # Storage buffer size for FFT analysis (reduced for optimization)

# Global Variables
stop_thread = False
sample_idx = 0
last_time = time.time()
total_samples = 0
total_bytes_received = 0

# Data buffers (for real-time graph)
x_data = deque(maxlen=PLOT_WINDOW)
gy_x = deque(maxlen=PLOT_WINDOW)
gy_y = deque(maxlen=PLOT_WINDOW)
gy_z = deque(maxlen=PLOT_WINDOW)

acc_x = deque(maxlen=PLOT_WINDOW)
acc_y = deque(maxlen=PLOT_WINDOW)
acc_z = deque(maxlen=PLOT_WINDOW)

# Raw buffers (for FFT analysis)
raw_gy_x = deque(maxlen=MAX_SAMPLES)
raw_gy_y = deque(maxlen=MAX_SAMPLES)
raw_gy_z = deque(maxlen=MAX_SAMPLES)

# Plot Configuration
fig, ax = plt.subplots(figsize=(12, 6))
ax.set_ylim(-32768, 32768)  # Adjust the limits as needed
ax.set_title("Real-time Sensor Data (Gyroscope & Accelerometer)")
ax.set_xlabel("Samples")
ax.set_ylabel("Value")

# Create lines for gyroscope
line_x, = ax.plot([], [], 'r-', label='Gyro X', alpha=0.7)
line_y, = ax.plot([], [], 'g-', label='Gyro Y', alpha=0.7)
line_z, = ax.plot([], [], 'b-', label='Gyro Z', alpha=0.7)

# Create lines for accelerometer
line_acc_x, = ax.plot([], [], 'r--', label='Acc X', alpha=0.5)
line_acc_y, = ax.plot([], [], 'g--', label='Acc Y', alpha=0.5)
line_acc_z, = ax.plot([], [], 'b--', label='Acc Z', alpha=0.5)

# Display Metrics (Data rate, Transfer rate)
data_rate_text = ax.text(0.02, 0.95, "", transform=ax.transAxes, fontsize=12, color='black', bbox=dict(facecolor='white', alpha=0.7))
transfer_rate_text = ax.text(0.02, 0.90, "", transform=ax.transAxes, fontsize=12, color='black', bbox=dict(facecolor='white', alpha=0.7))

ax.legend()

# UDP Setup
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", ESP_PORT))
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

# 🔹 Keep-alive thread (sends DISCOVER messages)
def keepConnected():
    global stop_thread
    while not stop_thread:
        try:
            sock.sendto(DISCOVER_MSG, ("192.168.4.1", ESP_PORT))
            time.sleep(KEEP_ALIVE_INTERVAL)
        except:
            break

# 🔹 Connect to ESP32
print("Connecting to ESP32...")
sock.sendto(DISCOVER_MSG, ("192.168.4.1", ESP_PORT))
while True:
    data, addr = sock.recvfrom(1024)
    if data == b"SERVER_ACK":
        print(f"Connected to ESP32 at {addr[0]}")
        keep_alive_thread = threading.Thread(target=keepConnected)
        keep_alive_thread.daemon = True  # Thread will close with main program
        keep_alive_thread.start()
        break

# 🔹 UDP Receiver & Plot Update Function
def update_plot(frame):
    global sample_idx, last_time, total_samples, total_bytes_received
    try:
        data, addr = sock.recvfrom(4096)
        if data == b"SERVER_ACK":
            return line_x, line_y, line_z, line_acc_x, line_acc_y, line_acc_z

        # Get the current time to calculate data rate
        current_time = time.time()

        # Split batch samples from UDP packet
        batch = data.decode().strip().split("\n")
        
        # Calculate the number of samples in this batch
        batch_size = len(batch)

        # Update the total sample count
        total_samples += batch_size
        total_bytes_received += len(data)

        # Print received data for debugging
        #print(batch)

        for sample in batch:
            values = [int(x) for x in sample.split(',')]
            sample_idx += 1

            # Update real-time graph buffer (Gyroscope + Accelerometer)
            x_data.append(sample_idx)
            gy_x.append(values[0])
            gy_y.append(values[1])
            gy_z.append(values[2])

            # Store accelerometer data
            acc_x.append(values[3])  # Accelerometer X
            acc_y.append(values[4])  # Accelerometer Y
            acc_z.append(values[5])  # Accelerometer Z

            # Store raw data for FFT analysis (only Gyroscope here, but you can include accelerometer)
            raw_gy_x.append(values[0])
            raw_gy_y.append(values[1])
            raw_gy_z.append(values[2])

        # Update graph data for gyroscope
        x_min = max(0, sample_idx - PLOT_WINDOW)
        x_max = sample_idx
        line_x.set_data(list(x_data), list(gy_x))
        line_y.set_data(list(x_data), list(gy_y))
        line_z.set_data(list(x_data), list(gy_z))

        # Update graph data for accelerometer
        line_acc_x.set_data(list(x_data), list(acc_x))
        line_acc_y.set_data(list(x_data), list(acc_y))
        line_acc_z.set_data(list(x_data), list(acc_z))

        ax.set_xlim(x_min, x_max)

        # Calculate data rate (samples per second)
        if current_time - last_time >= 1:
            data_rate = total_samples / (current_time - last_time)  # Samples per second
            transfer_rate = total_bytes_received / (current_time - last_time)  # Bytes per second

            # Update the last time and reset counters
            last_time = current_time
            total_samples = 0
            total_bytes_received = 0

            # Display data rate and transfer rate on the plot
            data_rate_text.set_text(f"Data Rate: {data_rate:.2f} samples/s")
            transfer_rate_text.set_text(f"Transfer Rate: {transfer_rate:.2f} bytes/s")

    except Exception as e:
        print(f"Error: {e}")

    return line_x, line_y, line_z, line_acc_x, line_acc_y, line_acc_z

# 🔹 Animation (Real-time Plot)
ani = animation.FuncAnimation(
    fig,
    update_plot,
    interval=1,  # Increased interval (50ms) to reduce processing load
    blit=True,
    cache_frame_data=False
)

# 🔹 Run Program
try:
    plt.show()
except KeyboardInterrupt:
    stop_thread = True  # Stop thread
    keep_alive_thread.join()  # Wait for thread
    sock.close()
    print("Connection closed")
    
finally:
    sock.close()
    print("Connection closed")
