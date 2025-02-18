import os
import numpy as np
import matplotlib.pyplot as plt
import pywt
from scipy.signal import butter, filtfilt
from scipy.fftpack import fft
from matplotlib.widgets import RadioButtons, CheckButtons
from matplotlib.widgets import Slider

def compute_sampling_rate(timestamps):
    timestamps_sec = timestamps / 1e6
    dt = np.diff(timestamps_sec)
    fs = 1 / np.mean(dt)
    return fs

def butter_bandpass(lowcut, highcut, fs, order=4):
    nyquist = 0.5 * fs
    lowcut = max(0.1, lowcut)
    highcut = min(highcut, nyquist - 1)
    low = lowcut / nyquist
    high = highcut / nyquist
    b, a = butter(order, [low, high], btype='band')
    return b, a

def bandpass_filter(data, lowcut=50, highcut=300, fs=1000, order=4):
    b, a = butter_bandpass(lowcut, highcut, fs, order=order)
    return filtfilt(b, a, data)

def butter_lowpass_filter(data, cutoff=5, fs=1000, order=4):
    nyquist = 0.5 * fs
    normal_cutoff = cutoff / nyquist
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    return filtfilt(b, a, data)

def wavelet_denoise(data, wavelet='db4', level=1):
    coeffs = pywt.wavedec(data, wavelet, level=level)
    coeffs[1:] = [pywt.threshold(c, np.std(c) / 2, mode='soft') for c in coeffs[1:]]
    denoised = pywt.waverec(coeffs, wavelet)
    return denoised[:len(data)]

def interactive_plot(time_data, data, fs):
    fig, ax = plt.subplots(figsize=(10, 6))
    plt.subplots_adjust(bottom=0.25)
    
    filters = {'Raw': lambda x: x, 'Low-pass': lambda x: butter_lowpass_filter(x, 5, fs),
               'Band-pass': lambda x: bandpass_filter(x, 50, 300, fs),
               'Wavelet': lambda x: wavelet_denoise(x)}
    
    axis_labels = ["GyX", "GyY", "GyZ", "AcX", "AcY", "AcZ"]
    colors = ["red", "green", "blue", "purple", "orange", "brown"]
    active_axis = 0
    active_filter = 'Raw'
    
    def update_plot(label):
        nonlocal active_filter
        active_filter = label
        filtered_data = filters[active_filter](data[:, active_axis])
        ax.clear()
        ax.plot(time_data, data[:, active_axis], linestyle="solid", linewidth=0.2, alpha=0.5, color="black", label=f"{axis_labels[active_axis]} (Raw)")
        ax.plot(time_data, filtered_data, linestyle="solid", linewidth=0.2, color=colors[active_axis], label=f"{axis_labels[active_axis]} ({active_filter})")
        ax.legend()
        ax.grid(True, linestyle="dotted", linewidth=0.3)
        ax.set_ylabel(f"{axis_labels[active_axis]} Value")
        ax.set_xlabel("Time (s)")
        plt.draw()
    
    def toggle_axis(label):
        nonlocal active_axis
        active_axis = axis_labels.index(label)
        update_plot(active_filter)
    
    ax_radio = plt.axes([0.1, 0.02, 0.2, 0.15])
    radio = RadioButtons(ax_radio, list(filters.keys()))
    radio.on_clicked(update_plot)
    
    ax_check = plt.axes([0.4, 0.02, 0.4, 0.15])
    check = RadioButtons(ax_check, axis_labels)
    check.on_clicked(toggle_axis)
    
    update_plot(active_filter)
    plt.show()

def process_data(session_folder, session_name, data):

    data = np.array(data)
    timestamps = data[:, -1]

    fs = compute_sampling_rate(timestamps)
    time_shifted = (timestamps - timestamps[0]) / 1e6
    
    interactive_plot(time_shifted, data, fs)
    print("🎉 Interactive visualization complete!")
