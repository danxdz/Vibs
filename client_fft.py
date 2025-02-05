import numpy as np
import matplotlib.pyplot as plt
import logging
from scipy import signal
from scipy.fft import fft, fftfreq
import os

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

class DataHandler:
    # ================================
    # Configuration Parameters
    # ================================
    CONFIG = {
        "DEFAULT_SAMPLE_RATE": 44100,     # Sample rate in Hz
        "CUTOFF_FREQUENCY": 400,           # Low-pass filter cutoff frequency in Hz
        "FILTER_ORDER": 4,               # Order of the Butterworth filter
        "EXPECTED_RPM": 3000,            # Expected rotational speed of the CNC tool (example)
        "FFT_WINDOW_SIZE": 1024,         # Window size for Welch and spectrogram analysis
        "NOVERLAP": 512,                 # Overlap between windows (for spectrogram)
        "NFFT": 1024                     # FFT length for spectrogram analysis
    }

    def __init__(self, data_file):
        """
        Initialize the DataHandler with a file containing vibration data.
        :param data_file: Path to the CSV file containing the vibration data.
        """
        self.data_file = data_file
        self.data = None

    def load_data(self):
        """
        Loads vibration data from a CSV file.
        Expected CSV format: X_value, Y_value, Z_value, timestamp (ms)
        """
        try:
            self.data = np.loadtxt(self.data_file, delimiter=',')
            logging.info(f"Data loaded from {self.data_file}")
        except Exception as e:
            logging.error(f"Error loading data: {e}")
            raise

    @staticmethod
    def butter_lowpass_filter(data, cutoff, sample_rate, order):
        """
        Applies a Butterworth low-pass filter to the data.
        """
        nyquist = 0.5 * sample_rate
        normal_cutoff = cutoff / nyquist  # Normalize cutoff frequency
        b, a = signal.butter(order, normal_cutoff, btype='low', analog=False)
        filtered_data = signal.filtfilt(b, a, data)
        logging.info("Low-pass filter applied")
        return filtered_data

    @classmethod
    def perform_welch(cls, axis_data, sample_rate, label):
        """
        Uses Welch's method to estimate the power spectral density (PSD)
        and saves the plot.
        """
        f, Pxx = signal.welch(axis_data,
                              fs=sample_rate,
                              nperseg=cls.CONFIG["FFT_WINDOW_SIZE"])
        plt.figure()
        plt.semilogy(f, Pxx)
        plt.xlabel("Frequency (Hz)")
        plt.ylabel("PSD")
        plt.title(f"{label}-axis PSD (Welch's Method)")
        plt.grid(True)
        output_file = f"{label}_welch_psd.png"
        plt.savefig(output_file, dpi=300)
        plt.close()
        logging.info(f"Saved {label}-axis Welch PSD plot as {output_file}")
        return f, Pxx

    @classmethod
    def perform_spectrogram(cls, axis_data, sample_rate, label):
        """
        Computes and saves a spectrogram of the data.
        """
        f, t, Sxx = signal.spectrogram(axis_data,
                                       fs=sample_rate,
                                       nperseg=cls.CONFIG["FFT_WINDOW_SIZE"],
                                       noverlap=cls.CONFIG["NOVERLAP"],
                                       nfft=cls.CONFIG["NFFT"])
        plt.figure()
        plt.pcolormesh(t, f, 10 * np.log10(Sxx), shading='gouraud')
        plt.ylabel("Frequency (Hz)")
        plt.xlabel("Time (s)")
        plt.title(f"{label}-axis Spectrogram")
        plt.colorbar(label="PSD (dB/Hz)")
        output_file = f"{label}_spectrogram.png"
        plt.savefig(output_file, dpi=300)
        plt.close()
        logging.info(f"Saved {label}-axis spectrogram plot as {output_file}")
        return f, t, Sxx

    @classmethod
    def perform_fft_analysis(cls, axis_data, sample_rate, label):
        """
        Performs an FFT analysis on the data and returns the dominant (peak) frequency.
        """
        N = len(axis_data)
        T = 1.0 / sample_rate  # Sampling interval
        window = np.hamming(N)  # Apply a Hamming window to reduce spectral leakage
        data_windowed = axis_data * window

        # Compute FFT
        yf = fft(data_windowed)
        xf = fftfreq(N, T)[:N // 2]  # Only positive frequencies
        magnitude = 2.0 / N * np.abs(yf[:N // 2])

        plt.figure(figsize=(8, 4))
        plt.plot(xf, magnitude)
        plt.xlabel("Frequency (Hz)")
        plt.ylabel("Amplitude")
        plt.title(f"{label}-axis FFT Analysis")
        plt.grid(True)
        output_file = f"{label}_fft.png"
        plt.savefig(output_file, dpi=300)
        plt.close()
        logging.info(f"Saved {label}-axis FFT plot as {output_file}")

        # Determine the peak frequency
        peak_index = np.argmax(magnitude)
        peak_freq = xf[peak_index]
        logging.info(f"Peak frequency for {label}-axis: {peak_freq:.2f} Hz")
        return peak_freq

    @classmethod
    def rotational_analysis(cls, expected_rpm, axis_data, sample_rate, label):
        """
        Overlays expected rotational harmonics on the FFT analysis.
        """
        # Calculate the fundamental frequency from the expected RPM.
        fundamental_freq = expected_rpm / 60.0
        harmonics = [fundamental_freq * n for n in range(1, 6)]
        
        N = len(axis_data)
        T = 1.0 / sample_rate
        window = np.hamming(N)
        data_windowed = axis_data * window

        yf = fft(data_windowed)
        xf = fftfreq(N, T)[:N // 2]
        magnitude = 2.0 / N * np.abs(yf[:N // 2])

        plt.figure(figsize=(8, 4))
        plt.plot(xf, magnitude, label="FFT")
        # Overlay the expected harmonic frequencies
        for h in harmonics:
            plt.axvline(x=h, color='r', linestyle='--',
                        label=f'Harmonic {h:.1f} Hz' if h == harmonics[0] else "")
        plt.xlabel("Frequency (Hz)")
        plt.ylabel("Amplitude")
        plt.title(f"{label}-axis Rotational Analysis")
        plt.legend()
        plt.grid(True)
        output_file = f"{label}_rotational_analysis.png"
        plt.savefig(output_file, dpi=300)
        plt.close()
        logging.info(f"Saved {label}-axis rotational analysis plot as {output_file}")
        return fundamental_freq, harmonics

    def run_analysis(self):
        """
        Runs the full analysis pipeline on the loaded data.
        For demonstration, this method analyzes the X-axis data (first column).
        """
        # Load data from file
        self.load_data()
        if self.data is None:
            logging.error("No data loaded. Exiting analysis.")
            return

        # Extract the X-axis data (first column)
        x_data = self.data[:, 0]
        sample_rate = self.CONFIG["DEFAULT_SAMPLE_RATE"]

        # Apply low-pass filter to remove high-frequency noise
        x_filtered = DataHandler.butter_lowpass_filter(
            x_data,
            self.CONFIG["CUTOFF_FREQUENCY"],
            sample_rate,
            self.CONFIG["FILTER_ORDER"]
        )

        # Advanced Frequency-Domain Analysis using Welch's method
        self.perform_welch(x_filtered, sample_rate, "X")

        # Spectrogram analysis to view time-frequency changes
        self.perform_spectrogram(x_filtered, sample_rate, "X")

        # FFT analysis to determine the dominant frequency
        peak_freq = self.perform_fft_analysis(x_filtered, sample_rate, "X")

        # Rotational Analysis to overlay expected harmonics
        expected_rpm = self.CONFIG["EXPECTED_RPM"]
        self.rotational_analysis(expected_rpm, x_filtered, sample_rate, "X")

        logging.info("Analysis complete.")


