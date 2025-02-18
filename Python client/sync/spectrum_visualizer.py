import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import queue
from collections import deque
from scipy.signal import butter, filtfilt  # For filtering

class SpectrumVisualizer:
    def __init__(self, chunk_size=256, sample_rate=1000, cutoff_freq=30):
        self.chunk_size = chunk_size
        self.sample_rate = sample_rate
        self.data_queue = queue.Queue()  # Thread-safe queue

        # Buffers for Gyro & Accel data (X, Y, Z)
        self.data_buffers = {
            'gyro_x': deque([0] * chunk_size, maxlen=chunk_size),
            'gyro_y': deque([0] * chunk_size, maxlen=chunk_size),
            'gyro_z': deque([0] * chunk_size, maxlen=chunk_size),
            'accel_x': deque([0] * chunk_size, maxlen=chunk_size),
            'accel_y': deque([0] * chunk_size, maxlen=chunk_size),
            'accel_z': deque([0] * chunk_size, maxlen=chunk_size),
        }

        self.freqs = np.fft.rfftfreq(chunk_size, d=1/sample_rate)

        self.fig, self.ax = plt.subplots()
        
        # Create different lines for Gyro & Accel (Raw & Filtered)
        self.lines = {
            'gyro_x': self.ax.plot(self.freqs, np.zeros_like(self.freqs), color='r', label='Gyro X (Filtered)')[0],
            'gyro_y': self.ax.plot(self.freqs, np.zeros_like(self.freqs), color='g', label='Gyro Y (Filtered)')[0],
            'gyro_z': self.ax.plot(self.freqs, np.zeros_like(self.freqs), color='b', label='Gyro Z (Filtered)')[0],
            'accel_x': self.ax.plot(self.freqs, np.zeros_like(self.freqs), color='r', linestyle='dashed', alpha=0.7, label='Accel X (Filtered)')[0],
            'accel_y': self.ax.plot(self.freqs, np.zeros_like(self.freqs), color='g', linestyle='dashed', alpha=0.7, label='Accel Y (Filtered)')[0],
            'accel_z': self.ax.plot(self.freqs, np.zeros_like(self.freqs), color='b', linestyle='dashed', alpha=0.7, label='Accel Z (Filtered)')[0],
            'gyro_x_raw': self.ax.plot(self.freqs, np.zeros_like(self.freqs), color='r', alpha=0.5, label='Gyro X (Raw)')[0],
            'gyro_y_raw': self.ax.plot(self.freqs, np.zeros_like(self.freqs), color='g', alpha=0.5, label='Gyro Y (Raw)')[0],
            'gyro_z_raw': self.ax.plot(self.freqs, np.zeros_like(self.freqs), color='b', alpha=0.5, label='Gyro Z (Raw)')[0],
            'accel_x_raw': self.ax.plot(self.freqs, np.zeros_like(self.freqs), color='r', linestyle='dashed', alpha=0.3, label='Accel X (Raw)')[0],
            'accel_y_raw': self.ax.plot(self.freqs, np.zeros_like(self.freqs), color='g', linestyle='dashed', alpha=0.3, label='Accel Y (Raw)')[0],
            'accel_z_raw': self.ax.plot(self.freqs, np.zeros_like(self.freqs), color='b', linestyle='dashed', alpha=0.3, label='Accel Z (Raw)')[0],
        }

        self.ax.set_ylim(0, 1)
        self.ax.set_xlim(0, sample_rate / 2)
        self.ax.set_xlabel("Frequency (Hz)")
        self.ax.set_ylabel("Magnitude")
        self.ax.legend()

        # Create Low-pass filter
        self.b, self.a = butter(4, cutoff_freq / (sample_rate / 2), btype='low')

        self.ani = animation.FuncAnimation(self.fig, self.update_plot, interval=5, blit=False, cache_frame_data=False)

    def update_plot(self, frame):
        """Fetch new data from queue and update spectrum."""
        while not self.data_queue.empty():
            new_data = self.data_queue.get()
            for key in self.data_buffers:
                self.data_buffers[key].extend(new_data[key])

        for key in self.data_buffers:
            buffer = self.data_buffers[key]

            if len(buffer) == self.chunk_size:
                fft_output = np.fft.rfft(buffer)
                fft_magnitude = np.abs(fft_output) / len(buffer)
                fft_magnitude = np.log1p(fft_magnitude)  # Log scale
                
                if "raw" in key:
                    self.lines[key].set_ydata(fft_magnitude)  # Update raw data
                else:
                    filtered_data = filtfilt(self.b, self.a, list(buffer))  # Apply low-pass filter
                    fft_filtered = np.fft.rfft(filtered_data)
                    fft_filtered_mag = np.abs(fft_filtered) / len(filtered_data)
                    fft_filtered_mag = np.log1p(fft_filtered_mag)  # Log scale
                    self.lines[key].set_ydata(fft_filtered_mag)  # Update filtered data

        return self.lines.values()

    def add_data(self, gyro, accel):
        """Add new data safely using a thread-safe queue."""
        self.data_queue.put({
            'gyro_x': [gyro[0]], 'gyro_y': [gyro[1]], 'gyro_z': [gyro[2]],
            'accel_x': [accel[0]], 'accel_y': [accel[1]], 'accel_z': [accel[2]],
            'gyro_x_raw': [gyro[0]], 'gyro_y_raw': [gyro[1]], 'gyro_z_raw': [gyro[2]],
            'accel_x_raw': [accel[0]], 'accel_y_raw': [accel[1]], 'accel_z_raw': [accel[2]],
        })

    def start(self):
        """Start the visualization (must be called in the main thread)."""
        plt.show()

# Create a global instance
visualizer = SpectrumVisualizer()
