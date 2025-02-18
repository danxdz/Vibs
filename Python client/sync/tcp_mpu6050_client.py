import socket
import time
import struct

BUFFER_SIZE = 16

class TCPSensorClient:
    def __init__(self, server_ip, server_port):
        self.server_ip = server_ip
        self.server_port = server_port
        self.sock = None
        self.packet_count = 0
        self.start_time = time.time()
        self.connect_to_server()

    def connect_to_server(self):
        """ Establish a TCP connection with the ESP32 server. """
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((self.server_ip, self.server_port))
            print(f"✅ Connected to server at {self.server_ip}:{self.server_port}")
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            self.sock = None

    def receive_data(self):
        """ Receive sensor data from the ESP32 over TCP. """
        if self.sock is None:
            print("⚠️ Not connected to server.")
            return None, None, None

        try:
            data = self.sock.recv(BUFFER_SIZE)
            if len(data) == BUFFER_SIZE:
                self.packet_count += 1
                current_time = time.time()
                elapsed_time = (current_time - self.start_time) * 1000  # Convert to milliseconds

                gyro_data, accel_data, timestamp = self.unpack_data(data)
                self.print_data(gyro_data, accel_data, timestamp, elapsed_time)

                # Send elapsed time back to the ESP32 as an interval adjustment
                #interval_bytes = struct.pack("<I", int(elapsed_time))
                #self.sock.sendall(interval_bytes)

                return gyro_data, accel_data, timestamp
        except socket.error as e:
            print(f"⚠️ Socket error: {e}")
            self.reconnect()
        return None, None, None

    def unpack_data(self, data):
        """ Unpack sensor data from bytes into numerical values. """
        try:
            GyX, GyY, GyZ, AcX, AcY, AcZ, timestamp = struct.unpack("<6hI", data)
            return [GyX, GyY, GyZ], [AcX, AcY, AcZ], timestamp
        except struct.error as e:
            print(f"❌ Error unpacking data: {e}. Data: {data}")
            return None, None, None

    def print_data(self, gyro_data, accel_data, timestamp, elapsed_time):
        """ Print sensor data and update packet count. """
        if elapsed_time >= 1000:  # Every 10 seconds
            print(f"📊 Gyro={gyro_data}, Accel={accel_data}, Time={timestamp}, Packets/sec={self.packet_count}")
            self.start_time = time.time()
            self.packet_count = 0

    def reconnect(self):
        """ Try to reconnect to the server if the connection is lost. """
        print("🔄 Reconnecting...")
        self.close()
        time.sleep(2)
        self.connect_to_server()

    def close(self):
        """ Close the socket connection. """
        if self.sock:
            self.sock.close()
            self.sock = None

if __name__ == "__main__":
    client = TCPSensorClient("192.168.4.1", 12345)  # Use ESP32 hotspot IP

    try:
        while True:
            client.receive_data()
            time.sleep(0.001)  # Prevent excessive CPU usage
    except KeyboardInterrupt:
        print("\n❌ Closing connection.")
        client.close()
