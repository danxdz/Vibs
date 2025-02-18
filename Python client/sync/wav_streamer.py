import numpy as np
import wave
import queue
import threading

class WAVStreamer:
    def __init__(self, sample_rate=1000, num_channels=1, bit_depth=16, buffer_size=1000, output_file=None):
        """
        Initialize the real-time WAV streamer.
        
        :param sample_rate: Sampling rate in Hz (e.g., 1000 for 1 kHz)
        :param num_channels: Number of audio channels (e.g., 1 for mono, 2 for stereo)
        :param bit_depth: Bit depth (default: 16-bit)
        :param buffer_size: Number of samples before writing to WAV
        :param output_file: File path to save the WAV (optional)
        """
        self.sample_rate = sample_rate
        self.num_channels = num_channels
        self.bit_depth = bit_depth
        self.buffer_size = buffer_size
        self.output_file = output_file
        self.audio_queue = queue.Queue()
        self.running = False
        self.file = None

        # Start the streaming thread
        self.thread = threading.Thread(target=self._process_audio, daemon=True)
        self.thread.start()

    def start(self):
        """Start real-time audio streaming."""
        self.running = True
        if self.output_file:
            self.file = wave.open(self.output_file, 'wb')
            self.file.setnchannels(self.num_channels)
            self.file.setsampwidth(self.bit_depth // 8)
            self.file.setframerate(self.sample_rate)

    def stop(self):
        """Stop streaming and finalize WAV file if needed."""
        self.running = False
        self.thread.join()
        if self.file:
            self.file.close()
            print(f"✅ WAV saved as {self.output_file}")

    def add_sample(self, sample):
        """
        Add a sample (or multiple samples) to the queue.
        
        :param sample: List or single value (e.g., [GyX, GyY] for stereo)
        """
        if isinstance(sample, (list, tuple)) and len(sample) != self.num_channels:
            raise ValueError(f"Expected {self.num_channels} channels, but got {len(sample)}")

        self.audio_queue.put(sample)

    def _process_audio(self):
        """Process and convert samples to PCM in real time."""
        buffer = []

        while True:
            if not self.running and self.audio_queue.empty():
                break  # Stop processing when queue is empty and streaming stopped

            try:
                sample = self.audio_queue.get(timeout=1)  # Wait for data
                buffer.append(sample)

                if len(buffer) >= self.buffer_size:
                    self._write_to_wav(buffer)
                    buffer.clear()
            except queue.Empty:
                continue  # No data, just keep looping

    def _write_to_wav(self, buffer):
        """Convert and write buffered data to WAV."""
        if self.file:
            # Convert list of samples into NumPy array
            data = np.array(buffer, dtype=np.float32)

            # Normalize & convert to 16-bit PCM
            max_val = np.max(np.abs(data)) or 1
            int_data = (data / max_val * 32767).astype(np.int16)

            # Flatten multi-channel audio (if needed)
            if self.num_channels > 1:
                int_data = int_data.flatten()

            self.file.writeframes(int_data.tobytes())

