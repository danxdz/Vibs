import os
import tkinter as tk
from tkinter import filedialog
import pandas as pd

import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from save_data import create_new_folder, generate_plots, process_realtime_wav

from pass_filters import process_data

def main():
    # Open file dialog to select CSV file
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    csv_file = filedialog.askopenfilename(title="Select CSV File", filetypes=[("CSV Files", "*.csv")])

    if not csv_file:
        print("❌ No file selected. Exiting...")
        return

    # Read CSV data
    try:
        df = pd.read_csv(csv_file)
        collected_data = df.values.tolist()  # Convert DataFrame to list of lists
    except Exception as e:
        print(f"❌ Error reading CSV file: {e}")
        return

    # Ask for session name
    session_name = input("Enter a name for this session: ").strip()
    if not session_name:
        session_name = os.path.splitext(os.path.basename(csv_file))[0]  # Default to filename without extension

    # Create output folder
    rec_folder = create_new_folder()
    session_folder = os.path.join(rec_folder, session_name)
    os.makedirs(session_folder, exist_ok=True)
    
    process_data(session_folder, session_name, collected_data)

    # Generate plots and process WAV files
    generate_plots(session_folder, session_name, collected_data)
    process_realtime_wav(csv_file, session_folder, session_name)



    print(f"🎉 Processing complete! Data saved in: {session_folder}")

if __name__ == "__main__":
    main()
