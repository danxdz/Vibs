import socket
import threading
import time
import numpy as np
import glfw
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *

# Constants
ESP_PORT = 12345
DISCOVER_MSG = b"DISCOVER_VIBS_SERVER"
KEEP_ALIVE_INTERVAL = 3
ROTATION_SCALE = 0.1  # Increased for better visibility

# Global Variables
gyroscope_data = [0, 0, 0]
cube_rotation = [0, 0, 0]
stop_thread = False
last_time = time.time()
connection_status = "🔴 Disconnected"
prev_status = None
data_rate = 0
last_data_time = time.time()

CALIBRATION_SAMPLES = 100
CALIBRATION_DELAY = 0.01
axes_map = {'x': 0, 'y': 1, 'z': 2}
gyro_offset = [0, 0, 0]
is_calibrated = False
# Add after global variables
CALIBRATION_THRESHOLD = 500  # Maximum allowed variance
DEBUG = False  # Enable debug prints

def calibrate_gyro():
    global gyro_offset, is_calibrated
    if connection_status != "🟢 Connected":
        print("❌ Wait for connection first!")
        return
        
    print("\n📊 Calibrating gyroscope...")
    print("Keep the sensor still...")
    
    samples = []
    raw_data = []
    buffer = ""
    
    for i in range(CALIBRATION_SAMPLES):
        try:
            data, _ = sock.recvfrom(4096)
            buffer += data.decode()
            
            # Split buffer into complete packets
            packets = buffer.split('\n')
            buffer = packets[-1]  # Keep incomplete packet
            packets = packets[:-1]  # Process complete packets
            
            for packet in packets:
                values = packet.strip().split(',')
                if len(values) == 4:
                    gx, gy, gz, ts = map(int, values)
                    
                    # Debug print
                    if DEBUG:
                        print(f"Raw: X={gx:5d} Y={gy:5d} Z={gz:5d}")
                    
                    # Apply low-pass filter
                    if len(samples) > 0:
                        alpha = 0.8
                        gx = int(alpha * samples[-1][0] + (1-alpha) * gx)
                        gy = int(alpha * samples[-1][1] + (1-alpha) * gy)
                        gz = int(alpha * samples[-1][2] + (1-alpha) * gz)
                    
                    samples.append([gx, gy, gz])
                    print(f"Calibrating: {len(samples)}/{CALIBRATION_SAMPLES}", end='\r')
                    
                    if len(samples) >= CALIBRATION_SAMPLES:
                        break
            
            if len(samples) >= CALIBRATION_SAMPLES:
                break
                
            time.sleep(CALIBRATION_DELAY)
            
        except Exception as e:
            if DEBUG:
                print(f"Error: {e}")
            continue
    
    if samples:
        variance = np.var(samples, axis=0)
        if DEBUG:
            print(f"\nVariance: {variance}")
            print(f"Mean: {np.mean(samples, axis=0)}")
            
        if np.all(variance < CALIBRATION_THRESHOLD):
            gyro_offset = np.mean(samples, axis=0)
            is_calibrated = True
            print(f"\n✅ Calibration complete! Offsets: {gyro_offset}")
        else:
            print("\n❌ Calibration failed: Too much movement")
            print(f"Variance: {variance}")
    else:
        print("\n❌ Calibration failed: No samples collected")


def map_axes():
    global axes_map
    if connection_status != "🟢 Connected":
        print("❌ Wait for connection first!")
        return
        
    print("\nRotate sensor in each direction:")
    
    print("1. Roll (X axis) then press Enter")
    input()
    data, _ = sock.recvfrom(1024)
    x_axis = np.argmax(np.abs(list(map(int, data.decode().strip().split(',')[:3]))))
    
    print("2. Pitch (Y axis) then press Enter")
    input()
    data, _ = sock.recvfrom(1024)
    y_axis = np.argmax(np.abs(list(map(int, data.decode().strip().split(',')[:3]))))
    
    print("3. Yaw (Z axis) then press Enter")
    input()
    data, _ = sock.recvfrom(1024)
    z_axis = np.argmax(np.abs(list(map(int, data.decode().strip().split(',')[:3]))))
    
    axes_map = {'x': x_axis, 'y': y_axis, 'z': z_axis}
    print(f"✅ Axes mapped: {axes_map}")

# OpenGL Cube Definition
vertices = np.array([
    [-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],
    [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]
], dtype=np.float32)

edges = [
    (0, 1), (1, 2), (2, 3), (3, 0),
    (4, 5), (5, 6), (6, 7), (7, 4),
    (0, 4), (1, 5), (2, 6), (3, 7)
]

# UDP Setup
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", ESP_PORT))
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

def keepConnected():
    global stop_thread
    while not stop_thread:
        try:
            sock.sendto(DISCOVER_MSG, ("192.168.4.1", ESP_PORT))
            time.sleep(KEEP_ALIVE_INTERVAL)
        except:
            break

def receive_data():
    global gyroscope_data, last_time, connection_status, data_rate, last_data_time
    total_data_received = 0
    start_time = time.time()

    while not stop_thread:
        try:
            data, addr = sock.recvfrom(1024)
            connection_status = "🟢 Connected"
            packets = data.decode().strip().split('\n')
            
            for packet in packets:
                values = packet.strip().split(',')
                if len(values) == 4:
                    try:
                        gx, gy, gz, ts = map(int, values)
                        
                        # Apply calibration if enabled
                        if is_calibrated:
                            gx -= gyro_offset[0]
                            gy -= gyro_offset[1]
                            gz -= gyro_offset[2]
                        
                        # Apply axis mapping
                        mapped = [
                            gx if axes_map['x'] == 0 else (gy if axes_map['x'] == 1 else gz),
                            gx if axes_map['y'] == 0 else (gy if axes_map['y'] == 1 else gz),
                            gx if axes_map['z'] == 0 else (gy if axes_map['z'] == 1 else gz)
                        ]
                        
                        gyroscope_data = [v/100 for v in mapped]
                        last_time = ts
                        last_data_time = time.time()
                        
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


def display():
    global last_data_time, connection_status, prev_status, cube_rotation
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    
    glLoadIdentity()
    gluLookAt(0, 0, 5, 0, 0, 0, 0, 1, 0)
    
    glRotatef(cube_rotation[0], 1, 0, 0)
    glRotatef(cube_rotation[1], 0, 1, 0)
    glRotatef(cube_rotation[2], 0, 0, 1)
    
    glBegin(GL_LINES)
    glColor3f(0.0, 1.0, 1.0)
    for edge in edges:
        for vertex in edge:
            glVertex3fv(vertices[vertex])
    glEnd()

    # Update rotation
    cube_rotation[0] += gyroscope_data[0] * ROTATION_SCALE
    cube_rotation[1] += gyroscope_data[1] * ROTATION_SCALE
    cube_rotation[2] += gyroscope_data[2] * ROTATION_SCALE

    if time.time() - last_data_time > KEEP_ALIVE_INTERVAL:
        connection_status = "🔴 No Data"

    if connection_status != prev_status:
        print(f"{connection_status} | 📊 Rate: {data_rate:.1f} Hz | 📥 Gyro: {gyroscope_data}")
        prev_status = connection_status

    glfw.swap_buffers(window)
    glfw.poll_events()

# Initialize GLFW and OpenGL
if not glfw.init():
    raise Exception("GLFW initialization failed")

window = glfw.create_window(800, 600, "ESP32 3D Cube", None, None)
if not window:
    glfw.terminate()
    raise Exception("Window creation failed")

glfw.make_context_current(window)
glEnable(GL_DEPTH_TEST)

glMatrixMode(GL_PROJECTION)
glLoadIdentity()
gluPerspective(45, 800/600, 0.1, 50.0)
glMatrixMode(GL_MODELVIEW)

# Start Threads
threading.Thread(target=receive_data, daemon=True).start()
threading.Thread(target=keepConnected, daemon=True).start()

print("\n🎮 Controls:")
print("C - Calibrate")
print("M - Map axes")
print("R - Reset orientation")
print("Q - Quit\n")

# Modify main loop
try:
    while not glfw.window_should_close(window):
        if glfw.get_key(window, glfw.KEY_C) == glfw.PRESS:
            calibrate_gyro()
        elif glfw.get_key(window, glfw.KEY_M) == glfw.PRESS:
            map_axes()
        elif glfw.get_key(window, glfw.KEY_R) == glfw.PRESS:
            cube_rotation = [0, 0, 0]
        elif glfw.get_key(window, glfw.KEY_Q) == glfw.PRESS:
            break
        display()
except KeyboardInterrupt:
    print("\nClosing application...")
finally:
    stop_thread = True
    sock.close()
    glfw.terminate()