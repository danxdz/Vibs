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
PLOT_WINDOW = 1000  # Number of samples to show in the real-time graph
BATCH_SIZE = 10  # Number of samples per UDP packet (same as ESP32)
MAX_SAMPLES = 5000  # Storage buffer size for FFT analysis

# Global Variables
stop_thread = False
sample_idx = 0

# Data buffers (for real-time graph)
x_data = deque(maxlen=PLOT_WINDOW)
gy_x = deque(maxlen=PLOT_WINDOW)
gy_y = deque(maxlen=PLOT_WINDOW)
gy_z = deque(maxlen=PLOT_WINDOW)

# Raw buffers (for FFT analysis)
raw_gy_x = deque(maxlen=MAX_SAMPLES)
raw_gy_y = deque(maxlen=MAX_SAMPLES)
raw_gy_z = deque(maxlen=MAX_SAMPLES)

# Plot Configuration
fig, ax = plt.subplots(figsize=(12, 6))
ax.set_ylim(-32768, 32768)
ax.set_title("Real-time Gyroscope Data")
ax.set_xlabel("Samples")
ax.set_ylabel("Value")

# Create lines
line_x, = ax.plot([], [], 'r-', label='X', alpha=0.7)
line_y, = ax.plot([], [], 'g-', label='Y', alpha=0.7)
line_z, = ax.plot([], [], 'b-', label='Z', alpha=0.7)
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
    global sample_idx
    try:
        data, addr = sock.recvfrom(1024)
        if data == b"SERVER_ACK":
            return line_x, line_y, line_z
        
        # Split batch samples from UDP packet
        batch = data.decode().strip().split("\n")

        #print received data
        print(batch)
        
        for sample in batch:
            values = [int(x) for x in sample.split(',')]
            sample_idx += 1
            
            # Update real-time graph buffer
            x_data.append(sample_idx)
            gy_x.append(values[0])
            gy_y.append(values[1])
            gy_z.append(values[2])
            
            # Store raw data for FFT analysis
            raw_gy_x.append(values[0])
            raw_gy_y.append(values[1])
            raw_gy_z.append(values[2])
        
        # Update graph data
        x_min = max(0, sample_idx - PLOT_WINDOW)
        x_max = sample_idx
        line_x.set_data(list(x_data), list(gy_x))
        line_y.set_data(list(x_data), list(gy_y))
        line_z.set_data(list(x_data), list(gy_z))
        ax.set_xlim(x_min, x_max)
    
    except Exception as e:
        print(f"Error: {e}")
    
    return line_x, line_y, line_z


# 🔹 FFT Analysis Function
def run_fft():
    if len(raw_gy_x) < 512:  # Need at least 512 samples for FFT
        print("Not enough data for FFT")
        return
    
    fs = 1600  # Estimated sample rate (based on ESP32 optimizations)
    N = 512  # Number of points for FFT
    f_axis = np.fft.fftfreq(N, d=1/fs)[:N//2]
    
    # Compute FFT
    fft_x = np.abs(np.fft.fft(list(raw_gy_x)[-N:])[:N//2])
    fft_y = np.abs(np.fft.fft(list(raw_gy_y)[-N:])[:N//2])
    fft_z = np.abs(np.fft.fft(list(raw_gy_z)[-N:])[:N//2])
    
    # Plot FFT
    plt.figure(figsize=(12, 6))
    plt.plot(f_axis, fft_x, 'r', label="Gyro X")
    plt.plot(f_axis, fft_y, 'g', label="Gyro Y")
    plt.plot(f_axis, fft_z, 'b', label="Gyro Z")
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Amplitude")
    plt.title("FFT - Vibration Analysis")
    plt.legend()
    plt.show()


# 🔹 Animation (Real-time Plot)
ani = animation.FuncAnimation(
    fig,
    update_plot,
    interval=1,
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
