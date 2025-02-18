import numpy as np
import matplotlib.pyplot as plt
import logging
from scipy import signal
from scipy.fft import fft, fftfreq
import os

# Set up logging for detailed output.
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")

class DataHandler:
    CONFIG = {
        "CUTOFF_FREQUENCY": 400,      # Maximum frequency to analyze (Hz)
        "FILTER_ORDER": 4,            # Order of the Butterworth filter
        "FFT_WINDOW_SIZE": 1024,      # FFT window size (used if data length allows)
        "SPEED_INTERVAL": 5.0,        # Duration (s) for each speed interval (segment)
        "RPM_START": 1000,            # Starting RPM for the test
        "RPM_END": 10000,             # Ending RPM for the test
        "NOVERLAP": 512,              # Ensure noverlap < nperseg (typically half of window size)
        "NFFT": 2048,                 # Number of FFT points
    }


    def __init__(self, data_file):
        self.data_file = data_file
        self.output_dir = os.path.dirname(data_file) or "."
        self.data = None
        self.timestamps = None
        self.sample_rate = None

    def load_data(self):
        try:
            raw_data = np.loadtxt(self.data_file, delimiter=',')
            self.timestamps = raw_data[:, 3] / 1000.0  # Convert ms to seconds
            self.data = raw_data[:, :3]  # X, Y, Z data

            # Compute average sample rate from time differences
            time_diffs = np.diff(self.timestamps)
            avg_sample_rate = 1.0 / np.mean(time_diffs)
            self.sample_rate = avg_sample_rate

            logging.info(f"📊 Computed Sample Rate: {self.sample_rate:.2f} Hz")
        except Exception as e:
            logging.error(f"❌ Error loading data: {e}")
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
        logging.info(f"⏳ Found {len(speed_intervals)} speed intervals.")
        return speed_intervals

    @staticmethod
    def butter_lowpass_filter(data, cutoff, sample_rate, order):
        nyquist = 0.5 * sample_rate
        normal_cutoff = cutoff / nyquist
        b, a = signal.butter(order, normal_cutoff, btype='low', analog=False)
        filtered = signal.filtfilt(b, a, data)
        logging.info("Low-pass filter applied")
        return filtered

    @staticmethod
    def perform_fft_analysis(axis_data, sample_rate):
        N = len(axis_data)
        T = 1.0 / sample_rate
        window = np.hamming(N)
        data_windowed = axis_data * window

        yf = fft(data_windowed)
        xf = fftfreq(N, T)[:N // 2]
        magnitude = 2.0 / N * np.abs(yf[:N // 2])

        valid_indices = xf <= 400
        xf_filtered = xf[valid_indices]
        magnitude_filtered = magnitude[valid_indices]

        if len(xf_filtered) == 0 or len(magnitude_filtered) == 0:
            return None, None, None

        peak_index = np.argmax(magnitude_filtered)
        peak_freq = xf_filtered[peak_index]
        return xf_filtered, magnitude_filtered, peak_freq

    def plot_peak_vs_rpm(self, peak_dict, axis_label):
        segments = np.array(sorted(peak_dict.keys()))
        if len(segments) < 2:
            logging.warning("Not enough segments for RPM comparison plot.")
            return

        rpm_values = np.linspace(self.CONFIG["RPM_START"], self.CONFIG["RPM_END"], len(segments))
        peaks = [peak_dict[seg] for seg in segments]

        plt.figure(figsize=(10, 6))
        plt.plot(rpm_values, peaks, marker='o', linestyle='-')
        plt.xlabel("RPM")
        plt.ylabel("Peak Frequency (Hz)")
        plt.title(f"Peak Frequency vs. RPM for {axis_label}-axis")
        plt.grid(True)
        output_file = os.path.join(self.output_dir, f"{axis_label}_peak_vs_rpm.png")
        plt.savefig(output_file, dpi=300)
        plt.close()
        logging.info(f"Saved Peak vs. RPM plot for {axis_label}-axis as {output_file}")

    def save_recommendations(self, peak_by_axis):
        recommendations = []
        num_segments = max(len(peaks) for peaks in peak_by_axis.values())
        rpm_values = np.linspace(self.CONFIG["RPM_START"], self.CONFIG["RPM_END"], num_segments)

        for axis in ["X", "Y", "Z"]:
            axis_peaks = peak_by_axis.get(axis, {})
            if not axis_peaks:
                recommendations.append(f"{axis}-axis: No valid data.\n")
                continue

            # Filter valid peaks (exclude 0 or very low peaks)
            valid_peaks = {seg: peak for seg, peak in axis_peaks.items() if peak > 0.1}

            if valid_peaks:
                # Sort by peak frequency first, and if tied, by RPM (descending order for RPM)
                sorted_peaks = sorted(valid_peaks.items(), key=lambda item: (item[1], -rpm_values[item[0]]))

                best_seg, best_peak = sorted_peaks[0]
                best_rpm = rpm_values[best_seg]
                recommendations.append(f"{axis}-axis: Best RPM = {best_rpm:.0f} RPM (Segment {best_seg+1}) with Peak Frequency = {best_peak:.2f} Hz.\n")
            else:
                recommendations.append(f"{axis}-axis: No valid peak frequency greater than 0.1 Hz.\n")

        rec_file = os.path.join(self.output_dir, "recommendations.txt")
        with open(rec_file, "w") as f:
            f.writelines(recommendations)
        logging.info(f"Saved recommendations to {rec_file}")

        for line in recommendations:
            print(line.strip())
            
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
        Runs the complete analysis and saves all files in the csv folder.
        """
        self.load_data()
        if self.data is None:
            logging.error("No data loaded. Exiting analysis.")
            return

        speed_intervals = self.detect_speed_intervals()
        num_segments = len(speed_intervals)
        if num_segments < 1:
            logging.error("No speed intervals detected.")
            return

        peak_by_axis = {"X": {}, "Y": {}, "Z": {}}

        for segment_id, (start, end) in enumerate(speed_intervals):
            logging.info(f"🔍 Analyzing segment {segment_id+1} from {self.timestamps[start]:.2f}s to {self.timestamps[end]:.2f}s")
            for axis, axis_label in enumerate(["X", "Y", "Z"]):
                segment_data = self.data[start:end, axis]
                segment_rate = self.sample_rate

                # Apply low-pass filtering
                filtered_data = self.butter_lowpass_filter(
                    segment_data, self.CONFIG["CUTOFF_FREQUENCY"], segment_rate, self.CONFIG["FILTER_ORDER"]
                )

                # Compute FFT analysis
                peak_freq = self.perform_fft_analysis(filtered_data, segment_rate, axis_label)
                if peak_freq is not None:
                    peak_by_axis[axis_label][segment_id] = peak_freq
                else:
                    logging.warning(f"No valid peak frequency for {axis_label}-axis in segment {segment_id+1}")

                # Additional analysis (Welch, Spectrogram, Rotational)
                self.perform_welch(filtered_data, segment_rate, axis_label)
                self.perform_spectrogram(filtered_data, segment_rate, axis_label)

        # Generate combined Peak vs. RPM plots for each axis
        for axis_label in ["X", "Y", "Z"]:
            self.plot_peak_vs_rpm(peak_by_axis[axis_label], axis_label)

        # Save final recommendations to csv folder
        self.save_recommendations(peak_by_axis)
        logging.info("✅ Full analysis complete.")
