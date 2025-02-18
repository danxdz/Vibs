import numpy as np
import matplotlib.pyplot as plt
import logging
from scipy import signal
from scipy.fft import fft, fftfreq
import os

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class DataHandler:
    CONFIG = {
        "CUTOFF_FREQUENCY": 400,
        "FILTER_ORDER": 4,
        "FFT_WINDOW_SIZE": 1024,
        "SPEED_INTERVAL": 5.0,
        "RPM_START": 1000,
        "RPM_END": 10000,
        "NOVERLAP": 512,
        "NFFT": 2048,
    }

    def __init__(self, data_file):
        self.data_file = data_file
        self.output_dir = os.path.dirname(data_file) or "."
        self.gyro_data = None
        self.acc_data = None
        self.timestamps = None
        self.sample_rate = None

    def load_data(self):
        try:
            raw_data = np.loadtxt(self.data_file, delimiter=',')
            self.gyro_data = raw_data[:, :3]  # Gyro X, Y, Z
            self.timestamps = raw_data[:, 3] / 1000.0  # Convert ms to seconds
            self.acc_data = raw_data[:, 4:7]  # Acc X, Y, Z

            # Ensure timestamps are increasing
            if np.any(np.diff(self.timestamps) <= 0):
                logging.error("Timestamps are not strictly increasing! Fixing...")
                self.timestamps = np.cumsum(np.maximum(np.diff(self.timestamps, prepend=0), 0.001))  # Ensure monotonic increase

            time_diffs = np.diff(self.timestamps)
            mean_time_diff = np.mean(time_diffs)

            if mean_time_diff <= 0:
                logging.error("Mean time difference is non-positive! Adjusting...")
                mean_time_diff = np.abs(mean_time_diff) + 1e-6  # Avoid division by zero

            self.sample_rate = 1.0 / mean_time_diff
            logging.info(f"✅ Computed Sample Rate: {self.sample_rate:.2f} Hz")

        except Exception as e:
            logging.error(f"Error loading data: {e}")
            raise


    def detect_speed_intervals(self):
        speed_intervals = []
        start_idx = 0
        for i in range(1, len(self.timestamps)):
            if self.timestamps[i] - self.timestamps[start_idx] >= self.CONFIG["SPEED_INTERVAL"]:
                speed_intervals.append((start_idx, i))
                start_idx = i
        if start_idx < len(self.timestamps) - 1:
            speed_intervals.append((start_idx, len(self.timestamps) - 1))
        logging.info(f"Found {len(speed_intervals)} speed intervals.")
        return speed_intervals

    @staticmethod
    def butter_lowpass_filter(data, cutoff, sample_rate, order):
        if sample_rate <= 2 * cutoff:
            logging.warning(f"⚠️ Sample rate ({sample_rate:.2f} Hz) is too low for cutoff frequency ({cutoff} Hz). Skipping filtering.")
            return data  # Return unfiltered data to prevent errors
        
        nyquist = 0.5 * sample_rate
        normal_cutoff = cutoff / nyquist
        
        if normal_cutoff <= 0 or normal_cutoff >= 1:
            logging.warning(f"⚠️ Invalid normal_cutoff value: {normal_cutoff}. Skipping filtering.")
            return data
        
        b, a = signal.butter(order, normal_cutoff, btype='low', analog=False)
        filtered = signal.filtfilt(b, a, data)
        
        logging.info("✅ Low-pass filter applied successfully")
        return filtered


    def perform_fft_analysis(self, data, sample_rate, label):
        N = len(data)
        T = 1.0 / sample_rate
        window = np.hamming(N)
        data_windowed = data * window

        yf = fft(data_windowed)
        xf = fftfreq(N, T)[:N // 2]
        magnitude = 2.0 / N * np.abs(yf[:N // 2])

        peak_index = np.argmax(magnitude)
        peak_freq = xf[peak_index]

        plt.figure()
        plt.plot(xf, magnitude)
        plt.xlabel("Frequency (Hz)")
        plt.ylabel("Amplitude")
        plt.title(f"{label} FFT Analysis")
        plt.grid()
        plt.savefig(f"{label}_fft.png")
        plt.close()

        logging.info(f"Peak frequency for {label}: {peak_freq:.2f} Hz")
        return peak_freq

    def run_analysis(self):
        self.load_data()
        if self.gyro_data is None or self.acc_data is None:
            logging.error("No data loaded. Exiting analysis.")
            return

        speed_intervals = self.detect_speed_intervals()
        if not speed_intervals:
            logging.error("No speed intervals detected.")
            return

        for sensor, data_set in {"Gyro": self.gyro_data, "Acc": self.acc_data}.items():
            for axis, axis_label in enumerate(["X", "Y", "Z"]):
                for segment_id, (start, end) in enumerate(speed_intervals):
                    segment_data = data_set[start:end, axis]
                    filtered_data = self.butter_lowpass_filter(
                        segment_data, self.CONFIG["CUTOFF_FREQUENCY"], self.sample_rate, self.CONFIG["FILTER_ORDER"]
                    )
                    peak_freq = self.perform_fft_analysis(filtered_data, self.sample_rate, f"{sensor}_{axis_label}_Segment{segment_id+1}")
                    logging.info(f"{sensor} {axis_label}-axis segment {segment_id+1}: Peak = {peak_freq:.2f} Hz")

        logging.info("Analysis complete.")
