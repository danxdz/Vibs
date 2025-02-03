import socket
import threading
import time
import numpy as np
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

def init_gl():
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
    
    # Light position and properties
    glLight(GL_LIGHT0, GL_POSITION, (5, 5, 5, 1))
    glLightfv(GL_LIGHT0, GL_AMBIENT, (0.2, 0.2, 0.2, 1))
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (1, 1, 1, 1))

def draw_axes():
    glBegin(GL_LINES)
    # X axis - Red
    glColor3f(1, 0, 0)
    glVertex3f(0, 0, 0)
    glVertex3f(2, 0, 0)
    # Y axis - Green
    glColor3f(0, 1, 0)
    glVertex3f(0, 0, 0)
    glVertex3f(0, 2, 0)
    # Z axis - Blue
    glColor3f(0, 0, 1)
    glVertex3f(0, 0, 0)
    glVertex3f(0, 0, 2)
    glEnd()

def draw_cube():
    # Draw solid cube faces
    glBegin(GL_QUADS)
    
    # Front face (cyan)
    glColor3f(0, 1, 1)
    glVertex3f(-1, -1, 1)
    glVertex3f(1, -1, 1)
    glVertex3f(1, 1, 1)
    glVertex3f(-1, 1, 1)
    
    # Back face (magenta)
    glColor3f(1, 0, 1)
    glVertex3f(-1, -1, -1)
    glVertex3f(-1, 1, -1)
    glVertex3f(1, 1, -1)
    glVertex3f(1, -1, -1)
    
    # Top face (yellow)
    glColor3f(1, 1, 0)
    glVertex3f(-1, 1, -1)
    glVertex3f(-1, 1, 1)
    glVertex3f(1, 1, 1)
    glVertex3f(1, 1, -1)
    
    # Bottom face (red)
    glColor3f(1, 0, 0)
    glVertex3f(-1, -1, -1)
    glVertex3f(1, -1, -1)
    glVertex3f(1, -1, 1)
    glVertex3f(-1, -1, 1)
    
    # Right face (green)
    glColor3f(0, 1, 0)
    glVertex3f(1, -1, -1)
    glVertex3f(1, 1, -1)
    glVertex3f(1, 1, 1)
    glVertex3f(1, -1, 1)
    
    # Left face (blue)
    glColor3f(0, 0, 1)
    glVertex3f(-1, -1, -1)
    glVertex3f(-1, -1, 1)
    glVertex3f(-1, 1, 1)
    glVertex3f(-1, 1, -1)
    
    glEnd()

def display():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    
    # Set camera position
    gluLookAt(4, 4, 4, 0, 0, 0, 0, 1, 0)
    
    # Draw coordinate axes
    draw_axes()
    
    # Apply rotations
    glRotatef(cube_rotation[0], 1, 0, 0)
    glRotatef(cube_rotation[1], 0, 1, 0)
    glRotatef(cube_rotation[2], 0, 0, 1)
    
    # Draw cube
    draw_cube()
    
    # Update rotation based on gyro data
    cube_rotation[0] += gyroscope_data[0] * ROTATION_SCALE
    cube_rotation[1] += gyroscope_data[1] * ROTATION_SCALE
    cube_rotation[2] += gyroscope_data[2] * ROTATION_SCALE
    
    glutSwapBuffers()

def reshape(width, height):
    glViewport(0, 0, width, height)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45, width/height, 0.1, 50.0)
    glMatrixMode(GL_MODELVIEW)

def keyboard(key, x, y):
    if key == b'q':
        global stop_thread
        stop_thread = True
        glutLeaveMainLoop()
    elif key == b'r':
        global cube_rotation
        cube_rotation = [0, 0, 0]

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
def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(800, 600)
    glutCreateWindow(b"ESP32 3D Cube")
    
    init_gl()
    
    glutDisplayFunc(display)
    glutIdleFunc(display)
    glutReshapeFunc(reshape)
    glutKeyboardFunc(keyboard)
    
    # Start UDP threads
    threading.Thread(target=receive_data, daemon=True).start()
    threading.Thread(target=keepConnected, daemon=True).start()
    
    print("\nControls:")
    print("R - Reset orientation")
    print("Q - Quit")
    
    glutMainLoop()

if __name__ == "__main__":
    main()