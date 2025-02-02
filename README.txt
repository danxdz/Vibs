CNC Vibration & Resonance Analyzer
A DIY project for measuring CNC machine vibrations, resonance from object taps, and machine milling vibrations using an ESP32 with an MPU6050 sensor. The project collects gyroscope and accelerometer data, processes it in real time via Python, and converts the sensor readings into CSV, WAV audio files, and high-resolution 4K plots. It also includes a real-time 3D viewer using Tkinter to display the sensor’s motion.

Table of Contents
Features
Hardware Requirements
Software Requirements
Installation and Setup
Usage
Project Structure
Troubleshooting
Future Improvements
License
Features
High-Frequency Data Acquisition:
Capture gyroscope and accelerometer data at up to 1 kHz (depending on your configuration) using an ESP32 and MPU6050 sensor.

UDP Data Transmission:
Transmit data wirelessly via UDP from the ESP32 to a Python server for processing and visualization.

Data Storage and Processing:

Save raw sensor data to CSV.
Convert sensor data into WAV audio files for each axis (X, Y, Z) and a mixed channel.
Generate 4K-resolution plots (PNG) with thin lines and small markers.
Real-Time 3D Visualization:
Display a rotating 3D square (with top and front views) using Tkinter. The rotation angles update in real time based on the gyroscope data, allowing you to “see” the sensor movement.

Hardware Requirements
ESP32 Development Board:
Used for reading sensor data and transmitting it over UDP.

MPU6050 Sensor Module:
A 6-axis sensor (accelerometer + gyroscope) that provides the vibration data.

Cabling and Breadboard (or PCB):
For connecting the MPU6050 to the ESP32.

WiFi Network:
For UDP communication between the ESP32 and your computer.

Software Requirements
Arduino IDE:
For programming the ESP32.

Python 3:
For data processing, conversion, plotting, and real-time visualization.

Python Libraries:

numpy
matplotlib
wave
socket
csv
(Optional) tkinter for the 3D viewer
Install these using pip:
bash
Copiar
Editar
pip install numpy matplotlib
(Tkinter is usually included with Python on many systems.)

Installation and Setup
ESP32 and MPU6050 Setup
Hardware Connection:
Connect the MPU6050 to the ESP32 using I2C. For example:

VCC to 3.3V
GND to GND
SCL to ESP32 SCL (e.g., GPIO22)
SDA to ESP32 SDA (e.g., GPIO21)
Program the ESP32:
Use an Arduino sketch (provided separately) to initialize the MPU6050, read sensor data, and transmit it over UDP.

Python Server Setup
Download the Repository:
Clone or download this repository to your computer.

Run the Python Script:
Open a terminal, navigate to the repository folder, and run:

bash
Copiar
Editar
python your_python_script.py
This script will:

Listen for UDP data.
Save the incoming data to CSV.
Convert the data into WAV files.
Generate a high-resolution 4K plot (PNG).
Launch a Tkinter window for real-time 3D visualization.
Usage
Data Capture:
Run the Python script. The UDP server will start receiving data from the ESP32.
Real-Time 3D Viewer:
A Tkinter window will open, displaying two canvas views (top view and front view) that update in real time based on the gyroscope readings.
Stopping the Capture:
Press Ctrl+C in the terminal to stop data capture. The script will then save all data to CSV, generate WAV files, and save a plot as PNG in a new folder inside the recordings directory (named with a timestamp).
Project Structure
bash
Copiar
Editar
.
├── recordings/                  # Folder for saved recordings; each session is stored in a timestamped folder.
│   └── YYYYMMDD_HHMMSS/          # Example: 20230202_153045
│       ├── gyro_data_1.csv      # Raw sensor data
│       ├── gyro_audio_X_1.wav   # Audio file for X-axis
│       ├── gyro_audio_Y_1.wav   # Audio file for Y-axis
│       ├── gyro_audio_Z_1.wav   # Audio file for Z-axis
│       ├── gyro_audio_Mixed_1.wav # Mixed channel audio file
│       └── gyro_plot_1.png      # 4K resolution plot of the data
├── README.md                    # This file
└── your_python_script.py        # Main Python code for data capture, processing, and visualization
Troubleshooting
Audacity Errors:
If Audacity fails to open your WAV files, check that:
The sample rate (framerate) is set appropriately (e.g., 44100 Hz for standard audio or the actual sampling rate of your sensor).
The data normalization and clipping are working correctly to ensure values are within the -32768 to 32767 range.
No UDP Data Received:
Make sure your ESP32 is correctly transmitting data to the correct IP and port.
Tkinter Window Not Updating:
Ensure that the UDP receiving loop uses non-blocking methods (like window.after()) so that the Tkinter event loop remains responsive.
Future Improvements
Enhanced 3D Visualization:
Incorporate more detailed 3D graphics using libraries like pyopengl or vpython for a more realistic view.
Improved Data Analysis:
Add filtering, calibration routines, and advanced signal processing for more detailed vibration analysis.
Mobile/Remote Control:
Develop a web interface or mobile app to control and monitor the device remotely.
Integration with CNC Software:
Allow the system to trigger alerts or actions based on detected vibration patterns.
License
This project is licensed under the MIT License. See the LICENSE file for details.