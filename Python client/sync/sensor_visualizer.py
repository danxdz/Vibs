import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d import Axes3D
from collections import deque

timestamp_queue = deque(maxlen=100)
gyro_data = {axis: deque(maxlen=100) for axis in ['X', 'Y', 'Z']}
accel_data = {axis: deque(maxlen=100) for axis in ['X', 'Y', 'Z']}

fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')
plt.ion()
plt.show()
    
def update_plot():
    plt.clf()
    plt.subplot(2, 1, 1)
    plt.title("Gyroscope Data")
    for axis, color in zip(['X', 'Y', 'Z'], ['r', 'g', 'b']):
        plt.plot(timestamp_queue, gyro_data[axis], color, label=f'Gy{axis}')
    plt.legend()
    
    plt.subplot(2, 1, 2)
    plt.title("Accelerometer Data")
    for axis, color in zip(['X', 'Y', 'Z'], ['r', 'g', 'b']):
        plt.plot(timestamp_queue, accel_data[axis], color, label=f'Ac{axis}')
    plt.legend()
    plt.pause(0.001)

def update_3d_plot(ax, AcX, AcY, AcZ):
    ax.cla()
    ax.quiver(0, 0, 0, AcX, AcY, AcZ, color='r', length=1.0)
    ax.set_xlim([-1, 1])
    ax.set_ylim([-1, 1])
    ax.set_zlim([-1, 1])
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    ax.set_title("3D Acceleration Vector")
    plt.draw()

def visualize_data(GyX, GyY, GyZ, AcX, AcY, AcZ, timestamp):
    timestamp_queue.append(timestamp)
    gyro_data['X'].append(GyX)
    gyro_data['Y'].append(GyY)
    gyro_data['Z'].append(GyZ)
    accel_data['X'].append(AcX)
    accel_data['Y'].append(AcY)
    accel_data['Z'].append(AcZ)
    
    update_plot()
    update_3d_plot(ax, AcX / 16384.0, AcY / 16384.0, AcZ / 16384.0)  # Normalize accel values

