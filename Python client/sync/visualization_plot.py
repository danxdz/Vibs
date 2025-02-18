import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore
import sys
import numpy as np

# Max data points to display
MAX_POINTS = 4000
UPDATE_INTERVAL = 20  # Update every 100ms (10 FPS for smoothness)

# Global storage for sensor data (pre-allocated NumPy arrays)
gyro_x_data = np.zeros(MAX_POINTS)
gyro_y_data = np.zeros(MAX_POINTS)
gyro_z_data = np.zeros(MAX_POINTS)
accel_x_data = np.zeros(MAX_POINTS)
accel_y_data = np.zeros(MAX_POINTS)
accel_z_data = np.zeros(MAX_POINTS)

# Global variables for curves
gyro_x_curve, gyro_y_curve, gyro_z_curve = None, None, None
accel_x_curve, accel_y_curve, accel_z_curve = None, None, None

app = None
win = None

def update_sensor_data(gyro_data, acc_data):
    """Efficiently update sensor data and refresh the plot."""
    global gyro_x_data, gyro_y_data, gyro_z_data, accel_x_data, accel_y_data, accel_z_data
    global gyro_x_curve, gyro_y_curve, gyro_z_curve, accel_x_curve, accel_y_curve, accel_z_curve

    if None in (gyro_x_curve, gyro_y_curve, gyro_z_curve, accel_x_curve, accel_y_curve, accel_z_curve):
        return  # Avoid updating before initialization

    # Shift data left and insert new value (fast rolling update)
    gyro_x_data[:-1], gyro_x_data[-1] = gyro_x_data[1:], gyro_data[0]
    gyro_y_data[:-1], gyro_y_data[-1] = gyro_y_data[1:], gyro_data[1]
    gyro_z_data[:-1], gyro_z_data[-1] = gyro_z_data[1:], gyro_data[2]
    accel_x_data[:-1], accel_x_data[-1] = accel_x_data[1:], acc_data[0]
    accel_y_data[:-1], accel_y_data[-1] = accel_y_data[1:], acc_data[1]
    accel_z_data[:-1], accel_z_data[-1] = accel_z_data[1:], acc_data[2]

def refresh_plot():
    """Refresh the plot with new sensor data."""
    global gyro_x_curve, gyro_y_curve, gyro_z_curve, accel_x_curve, accel_y_curve, accel_z_curve

    # ✅ Only update plots, not data (avoids UI lag)
    gyro_x_curve.setData(gyro_x_data)
    gyro_y_curve.setData(gyro_y_data)
    gyro_z_curve.setData(gyro_z_data)
    accel_x_curve.setData(accel_x_data)
    accel_y_curve.setData(accel_y_data)
    accel_z_curve.setData(accel_z_data)

def start_sensor_visualization():
    """Initialize and start real-time sensor visualization."""
    global app, win, gyro_x_curve, gyro_y_curve, gyro_z_curve, accel_x_curve, accel_y_curve, accel_z_curve

    app = QtWidgets.QApplication(sys.argv)
    win = pg.GraphicsLayoutWidget(show=True, title="Real-Time Sensor Data")
    win.resize(800, 600)

    # Create plot
    plot = win.addPlot(title="Gyroscope & Accelerometer")
    plot.addLegend()

    # ✅ Initialize curves
    gyro_x_curve = plot.plot(pen='r', name="Gyro X")
    gyro_y_curve = plot.plot(pen='g', name="Gyro Y")
    gyro_z_curve = plot.plot(pen='b', name="Gyro Z")
    accel_x_curve = plot.plot(pen='y', name="Accel X")
    accel_y_curve = plot.plot(pen='m', name="Accel Y")
    accel_z_curve = plot.plot(pen='c', name="Accel Z")

    print("✅ Sensor Visualization Initialized")

    # Efficient update timer (avoids lag)
    timer = QtCore.QTimer()
    timer.timeout.connect(refresh_plot)
    timer.start(UPDATE_INTERVAL)  # Refresh every 100ms (smooth & fast)

    sys.exit(app.exec_())  # Run the GUI
