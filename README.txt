CNC Vibration & Resonance Analyzer

🔹 Key Features:
✅ Real-time UDP data capture
✅ Auto-folder creation for organization
✅ Saves CSV & WAV files (X, Y, Z, Mixed)
✅ Plots gyroscope data with high resolution


## 🔥 Key Improvements

| Feature           | Before                     | After                           |
|------------------|---------------------------|--------------------------------|
| Batch Processing | 1 sample per packet       | 10 samples per packet         |
| UDP Parsing      | Single sample per call    | Parses multiple samples per UDP packet |
| FFT Support      | ❌ No FFT                  | ✅ FFT implemented            |
| UDP Performance  | Blocking operations       | ✅ Non-blocking & faster      |
| Data Buffering   | Small storage             | ✅ Up to 5000 samples stored  |
| CPU Optimization | Some delays in loop       | ✅ Faster execution           |

## 🚀 Expected Gains
- Handles **1600+ samples per second** without packet loss  
- **FFT analysis** for vibration frequency detection  
- More stable **real-time graph**  
