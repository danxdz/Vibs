import os
import csv
import wave
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt

from scipy.signal import resample

# Constants
BUFFER_SIZE = 1100  # How many samples to process per write
STANDARD_SAMPLE_RATES = [ 16000, 22050, 32000, 44100, 48000, 96000]




def create_new_folder():
    rec_folder = "rec"
    os.makedirs(rec_folder, exist_ok=True)
    return rec_folder

def save_to_csv(filename, collected_data):
    print(f"💾 Saving to CSV: {filename}")
    mode = 'w' if not os.path.exists(filename) else 'a'
    with open(filename, mode, newline="") as file:
        writer = csv.writer(file)
            
        writer.writerows(collected_data)


def normalize_to_16bit(data):
    """Normalize raw sensor data to 16-bit PCM (-32768 to 32767)."""
    max_val = np.max(np.abs(data))
    if max_val == 0:
        return np.int16(data)  # Avoid division by zero
    return np.int16((data / max_val) * 32767)

def estimate_sample_rate(timestamps):
    """Estimate the closest valid sample rate from timestamps (in microseconds)."""
    time_diffs = np.diff(timestamps) / 1_000_000.0  # Convert µs to seconds
    avg_sample_rate = 1.0 / np.mean(time_diffs)  # Hz
    return min(STANDARD_SAMPLE_RATES, key=lambda x: abs(x - avg_sample_rate))

def resample_to_uniform_timing(data, timestamps, target_sample_rate):
    """Resample data based on timestamps (in microseconds) to a uniform sample rate."""
    total_duration = (timestamps[-1] - timestamps[0]) / 1_000_000.0  # Convert µs to seconds
    num_samples = int(total_duration * target_sample_rate)
    
    # Generate evenly spaced time indices
    uniform_time = np.linspace(timestamps[0], timestamps[-1], num_samples)

    # Interpolate data onto uniform time grid
    resampled_data = np.interp(uniform_time, timestamps, data)

    return normalize_to_16bit(resampled_data)


def save_wav(filename, data, sample_rate):
    """Writes resampled sensor data to a WAV file."""
    with wave.open(filename, "wb") as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(2) #
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(data.tobytes())
    print(f"✅ Saved WAV: {filename} at {sample_rate} Hz")

def process_realtime_wav(csv_file, session_folder, session_name):
    """Reads CSV, synchronizes timestamps, and saves WAV files in real-time."""
    os.makedirs(session_folder, exist_ok=True)
    
    df = pd.read_csv(csv_file, delimiter=",")
    timestamps = df.iloc[:, 6].values  # Extract timestamps (column 6)
    
    if len(timestamps) < 2:
        print("❌ Error: Not enough data to estimate sample rate.")
        return
    
    # Estimate best sample rate based on timestamp intervals
    sample_rate = estimate_sample_rate(timestamps)
    print(f"📊 Estimated Sample Rate: {sample_rate} Hz")

    # Process & save WAV files for each axis
    axis_labels = ["GyX", "GyY", "GyZ", "AcX", "AcY", "AcZ"]
    for i, label in enumerate(axis_labels):
        sensor_data = df.iloc[:, i].values  # Extract column data
        resampled_data = resample_to_uniform_timing(sensor_data, timestamps, sample_rate)
        
        wav_filename = os.path.join(session_folder, f"{session_name}_{label}.wav")
        save_wav(wav_filename, resampled_data, sample_rate)

    print("🎉 All WAV files are synchronized and saved successfully!")



def butter_lowpass_filter(data, cutoff=5, fs=50, order=3):
    """Apply a low-pass Butterworth filter to the data."""
    nyquist = 0.5 * fs
    normal_cutoff = cutoff / nyquist
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    return filtfilt(b, a, data)

def generate_plots(session_folder, session_name, collected_data):
    if not collected_data:
        print("⚠️ No data to plot.")
        return

    data = np.array(collected_data)
    timestamps = data[:, -1] / 1_000_000.0  # Convert µs to seconds
    time_data = np.arange(len(data))  # Sample indices
    time_shifted = timestamps - timestamps[0]  # Start time from 0

    axis_labels = ["GyX", "GyY", "GyZ", "AcX", "AcY", "AcZ"]
    colors = ["red", "green", "blue"] * 2  # Keep same color scheme

    # Create combined plot (all axes in one figure)
    fig, axs = plt.subplots(6, 1, figsize=(14, 12), dpi=600)  # Reduced resolution
    for i, label in enumerate(axis_labels):
        raw_data = data[:, i]
        filtered_data = butter_lowpass_filter(raw_data)

        axs[i].plot(time_data, raw_data, linestyle="solid", linewidth=0.2, alpha=0.5, color=colors[i], label=f"{label} (Raw)")
        axs[i].plot(time_data, filtered_data, linestyle="dashed", linewidth=0.2, color=colors[i], label=f"{label} (Filtered)")

        axs[i].legend(loc="upper right")
        axs[i].grid(True, linestyle="dotted", linewidth=0.3)
        axs[i].set_ylabel(f"{label} Value")

    axs[-1].set_xlabel("Time (s)")
    axs[-1].set_xticks(np.linspace(0, len(time_data), num=6))
    axs[-1].set_xticklabels(np.round(np.linspace(0, time_shifted[-1], num=6), 2))

    plt.tight_layout()
    combined_plot_filename = os.path.join(session_folder, f"{session_name}_filtered_plot.png")
    plt.savefig(combined_plot_filename, dpi=300)  # High resolution for full plot
    plt.close()
    print(f"✅ Combined plot saved to {combined_plot_filename}")

    # Create separate plots for each axis
    for i, label in enumerate(axis_labels):
        fig, ax = plt.subplots(figsize=(8, 6), dpi=600)
        raw_data = data[:, i]
        filtered_data = butter_lowpass_filter(raw_data)

        ax.plot(time_data, raw_data, linestyle="solid", linewidth=0.2, alpha=0.5, color="red", label=f"{label} (Raw)")
        ax.plot(time_data, filtered_data, linestyle="dashed", linewidth=0.2, color="blue", label=f"{label} (Filtered)")

        ax.legend(loc="upper right")
        ax.grid(True, linestyle="dotted", linewidth=0.3)
        ax.set_xlabel("Sample Index")
        ax.set_ylabel(f"{label} Value")
        ax.set_title(f"{label} Data Plot")

        plot_filename = os.path.join(session_folder, f"{session_name}_{label}_plot.png")
        plt.savefig(plot_filename, dpi=200)
        plt.close()
        print(f"✅ Plot saved to {plot_filename}")

    print("🎉 All plots saved successfully!")



        


