import socket
import time

ESP_PORT = 12345
DISCOVER_MSG = b"DISCOVER_VIBS_SERVER"

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", ESP_PORT))
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

# Send discovery packet
sock.sendto(DISCOVER_MSG, ("192.168.4.1", ESP_PORT))
print("Sent discovery packet, waiting for server...")

# Wait for acknowledgment
while True:
    data, addr = sock.recvfrom(1024)
    if data == b"SERVER_ACK":
        print(f"Connected to server at {addr[0]}")
        break

# Now receive data
try:
    while True:
        data, addr = sock.recvfrom(1024)
        values = data.decode().strip().split(',')
        print(f"GyX={values[0]}, GyY={values[1]}, GyZ={values[2]}")
except KeyboardInterrupt:
    sock.close()
    print("\nConnection closed")