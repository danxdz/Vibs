import os
import pandas as pd
from scipy.signal import butter, filtfilt
import matplotlib.pyplot as plt
import numpy as np
import wave

# Constants
OUTPUT_FOLDER = "output"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Butterworth filter
def butter_lowpass_filter(data, cutoff=5, fs=50, order=3):
    nyquist = 0.5 * fs
    normal_cutoff = cutoff / nyquist
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    return filtfilt(b, a, data)

# Process CSV File
def process_csv_file(csv_file):
    """Reads CSV, applies filtering, and saves results."""
    session_name = os.path.splitext(os.path.basename(csv_file))[0]
    session_folder = os.path.join(OUTPUT_FOLDER, session_name)
    os.makedirs(session_folder, exist_ok=True)

    # Read CSV
    df = pd.read_csv(csv_file)
    
    # Filter and save
    filtered_df = df.copy()
    for col in df.columns:
        if df[col].dtype in [np.float64, np.int64]:  # Apply filter only to numerical columns
            filtered_df[col] = butter_lowpass_filter(df[col])

    filtered_csv_path = os.path.join(session_folder, f"{session_name}_filtered.csv")
    filtered_df.to_csv(filtered_csv_path, index=False)
    print(f"✅ Filtered data saved: {filtered_csv_path}")

    # Generate and save plots
    for col in df.columns:
        if df[col].dtype in [np.float64, np.int64]:  
            plt.figure()
            plt.plot(df[col], label="Raw", alpha=0.5)
            plt.plot(filtered_df[col], label="Filtered", linestyle="dashed")
            plt.title(col)
            plt.legend()
            plot_path = os.path.join(session_folder, f"{session_name}_{col}.png")
            plt.savefig(plot_path, dpi=300)
            plt.close()
            print(f"📊 Plot saved: {plot_path}")

if __name__ == "__main__":
    print("⚠ This script should be run from main.py!")
