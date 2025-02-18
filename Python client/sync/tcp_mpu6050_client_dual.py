import socket
import time
import struct

# Adjust buffer size to match the 200 bytes per packet from ESP32 (10 captures per packet)
BUFFER_SIZE = 2200  
CAPTURES_PER_PACKET = 100  # Each packet contains 10 captures
PACKET_SIZE = 22

class TCPSensorClient:
    def __init__(self, server_ip, server_port):
        self.server_ip = server_ip
        self.server_port = server_port
        self.sock = None
        self.packet_count = 0
        self.start_time = time.time()
        self.connected = False  # Track connection status
        self.connect_to_server()

    def connect_to_server(self):
        """ Establish a TCP connection with the ESP32 server. """
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((self.server_ip, self.server_port))
            self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

            self.connected = True
            print(f"✅ Connected to server at {self.server_ip}:{self.server_port}")
        except Exception as e:
            self.connected = False
            print(f"❌ Connection failed: {e}")
            self.sock = None


    def receive_data(self):
        """Receives and ensures a full 200-byte packet before processing."""
        if not self.sock:
            print("⚠️ Socket is not connected!")
            return None

        raw_data = b""  # Accumulate data
        while len(raw_data) < BUFFER_SIZE:
            try:
                chunk = self.sock.recv(BUFFER_SIZE - len(raw_data))  # Request remaining bytes
                if not chunk:  # Connection lost
                    print("❌ Connection closed by server!")
                    self.connected = False
                    return None
                raw_data += chunk
            except Exception as e:
                print(f"❌ Socket error: {e}")
                return None
            
        self.packet_count += 1
        captures = []
        for i in range(0, BUFFER_SIZE, PACKET_SIZE):  # Read 20 bytes per capture
            capture = raw_data[i : i + PACKET_SIZE]
            GyX, GyY, GyZ, AcX, AcY, AcZ, timestamp, cps, num = struct.unpack("<hhhhhhIIh", capture)
            captures.append((GyX, GyY, GyZ, AcX, AcY, AcZ, timestamp, cps, num))
            self.print_data([GyX,GyY, GyZ], [AcX, AcY, AcZ],timestamp, cps, num, i+1)
            
        return captures



    def unpack_data(self, data):
        """ Unpack sensor data from bytes into numerical values. """
        try:
            # Unpack the data from 20 bytes: 3 short (gyro), 3 short (accel), 1 int (timestamp), 1 int (CPS)
            GyX, GyY, GyZ, AcX, AcY, AcZ, timestamp, cps = struct.unpack("<6hII", data)
            return [GyX, GyY, GyZ], [AcX, AcY, AcZ], timestamp, cps
        except struct.error as e:
            print(f"❌ Error unpacking data: {e}. Data: {data}")
            return None, None, None, None

    def print_data(self, gyro_data, accel_data, timestamp, cps, num, capture_num):
        """ Print sensor data for each capture. """
        #print(f"📊 Capture {num}/{capture_num}: Gyro={gyro_data}, Accel={accel_data}, Time={timestamp}, CPS={cps}")

        # Print packets per second every second
        if time.time() - self.start_time >= 1:
            print(f"📦 Packets/sec: {self.packet_count}")
            self.start_time = time.time()
            self.packet_count = 0

    def reconnect(self):
        """ Try to reconnect to the server if the connection is lost. """
        if not self.connected:
            print("🔄 Reconnecting...")
            self.close()
            time.sleep(2)
            self.connect_to_server()

    def close(self):
        """ Close the socket connection. """
        if self.sock:
            self.sock.close()
            self.sock = None
            self.connected = False

if __name__ == "__main__":
    client = TCPSensorClient("192.168.4.1", 12345)  # Use ESP32 hotspot IP

    try:
        while True:
            captures = client.receive_data()
            #time.sleep(0.001)  # Prevent excessive CPU usage
    except KeyboardInterrupt:
        print("\n❌ Closing connection.")
        client.close()
