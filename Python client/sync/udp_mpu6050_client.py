import socket
import time
import struct

BUFFER_SIZE = 16

class UDPSensorClient:
    def __init__(self, local_ip, server_ip, server_port):
        self.local_ip = local_ip
        self.server_ip = server_ip
        self.server_port = server_port
        self.sock = None
        self.packet_count = 0
        self.start_time = time.time()
        self.setup_socket()  # Ensure the socket is set up during initialization

    def setup_socket(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind((self.local_ip, self.server_port))
            self.sock.settimeout(15)
            print(f"Bound to {self.local_ip}:{self.server_port}")
        except Exception as e:
            print(f"Failed to set up socket: {e}")
            self.sock = None  # Ensure sock is None if setup fails

    def discover_server(self):
        if self.sock is None:
            print("Socket is not set up. Cannot discover server.")
            return False

        print("Discovering server...")
        for _ in range(5):
            try:
                self.sock.sendto(b"DISCOVER_VIBS_SERVER", (self.server_ip, self.server_port))
                data, addr = self.sock.recvfrom(32)
                if b"SERVER_ACK" in data:
                    print(f"Server discovered at {addr}")
                    return True
            except socket.timeout:
                print("No response from server, retrying...")
        print("Server discovery failed.")
        return False

    def receive_data(self):
        try:
            data, _ = self.sock.recvfrom(BUFFER_SIZE)
            self.packet_count += 1
            current_time = time.time()
            elapsed_time = current_time - self.start_time
            #send elapsed time to server as raw data
            #self.sock.sendto(b"DISCOVER_VIBS_SERVER", (self.server_ip, self.server_port))
            #self.sock.sendto(struct.pack("<f", elapsed_time), (self.server_ip, self.server_port))
            
            if len(data) == BUFFER_SIZE:
                gyro_data, accel_data, timestamp = self.unpack_data(data)
                self.print_data(gyro_data, accel_data, timestamp, elapsed_time)
                return gyro_data, accel_data, timestamp
        except socket.timeout:
            print("Socket timed out. No data received.")
        return None, None, None

    def unpack_data(self, data):
        try:
            # Unpack the data into 6 int16_t values and 1 uint32_t value
            GyX, GyY, GyZ, AcX, AcY, AcZ, timestamp = struct.unpack("<6hI", data)
            gyro_data = [GyX, GyY, GyZ]
            accel_data = [AcX, AcY, AcZ]
            return gyro_data, accel_data, timestamp
        except struct.error as e:
            print(f"Error unpacking data: {e}. Data: {data}")
            return None, None, None

    def print_data(self, gyro_data, accel_data, timestamp, elapsed_time):
        if elapsed_time >= 1:
            print(f"Data: Gyro={gyro_data}, Accel={accel_data}, Time={timestamp}, Packets/sec={self.packet_count}")
            #self.sock.sendto(b"DISCOVER_VIBS_SERVER", (self.server_ip, self.server_port))

            self.start_time = time.time()
            self.packet_count = 0

    def close(self):
        if self.sock:
            self.sock.close()
