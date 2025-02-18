import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore
import numpy as np
import sys

# FFT Settings
DEF_SAMPLE_RATE = 4000  # Default sample rate
N_SAMPLES = 4096  # Number of samples per FFT calculation

# Global variables
sensor_values = []
timestamps = []
fft_curve = None  # ✅ Ensure it's initialized later
app = None
win = None

def update_fft_data(gyro_data):
    """Update FFT visualization with new gyro sensor data."""
    global sensor_values, timestamps, fft_curve

    if fft_curve is None:
        print("⚠️ FFT Curve not initialized yet.")
        return  # Avoid calling setData on None

    GyX, GyY, GyZ = gyro_data  # Use gyro data
    timestamps.append(QtCore.QDateTime.currentMSecsSinceEpoch() * 1e3)  # ✅ Fix timestamp issue
    sensor_values.append(GyX)  # Use GyX for FFT

    # Ensure we have enough samples
    if len(sensor_values) >= N_SAMPLES:
        samples = np.array(sensor_values[-N_SAMPLES:])
        time_diffs = np.diff(timestamps[-N_SAMPLES:]) / 1e6  # Convert to seconds

        # ✅ Compute dynamic sample rate
        SAMPLE_RATE = 1 / np.mean(time_diffs) if len(time_diffs) > 0 else DEF_SAMPLE_RATE

        # Compute FFT
        fft_values = np.fft.fft(samples)
        freqs = np.fft.fftfreq(N_SAMPLES, d=1/SAMPLE_RATE)

        # Only keep positive frequencies
        positive_freqs = freqs[:N_SAMPLES//2]
        magnitude = np.abs(fft_values[:N_SAMPLES//2])

        fft_curve.setData(positive_freqs, magnitude)  # ✅ Ensure fft_curve exists

def start_fft_visualization():
    """Initialize and start the FFT visualization."""
    global app, win, fft_curve

    app = QtWidgets.QApplication(sys.argv)
    win = pg.GraphicsLayoutWidget(show=True, title="Real-Time FFT Analyzer")
    win.resize(800, 600)

    fft_plot = win.addPlot(title="Frequency Spectrum")
    fft_plot.setLogMode(x=False, y=False)
    fft_plot.setLabel('bottom', "Frequency (Hz)")
    fft_curve = fft_plot.plot(pen='c')  # ✅ Initialize fft_curve here

    print("✅ FFT Visualization Ready")

    sys.exit(app.exec_())  # Keep the GUI running

