import socket
import time
import threading
import numpy as np

# Configurações
ESP_PORT = 12345
UDP_BUFFER_SIZE = 4096
KEEP_ALIVE_INTERVAL = 3
DISCOVER_MSG = b"DISCOVER_VIBS_SERVER"
DATA_UPDATE_INTERVAL = 3  # Atualiza taxa de dados a cada 1s

# Variáveis Globais
connection_status = "🔴 Disconnected"
total_data_received = 0
total_bytes_received = 0
velocity_x, velocity_y, velocity_z = 0.0, 0.0, 0.0
last_time = time.time()
stop_event = threading.Event()
latency = None

# Socket UDP
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", ESP_PORT))
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

# Acumuladores para filtro
acc_x_sum, acc_y_sum, acc_z_sum = 0.0, 0.0, 0.0
num_samples = 0

def keepConnected():
    interval = KEEP_ALIVE_INTERVAL
    while not stop_event.is_set():
        try:
            sock.sendto(DISCOVER_MSG, ("192.168.4.1", ESP_PORT))
            time.sleep(interval)

            # Se a conexão estiver estável, podemos reduzir o intervalo para evitar congestionamento
            if connection_status == "🟢 Connected":
                interval = min(interval + 0.5, 5)  # Aumenta até 5s no máximo
            else:
                interval = KEEP_ALIVE_INTERVAL  # Mantém rápido se estiver desconectado

        except Exception as e:
            print(f"Erro em keepConnected: {e}")
            time.sleep(KEEP_ALIVE_INTERVAL)  # Espera antes de tentar novamente

def receive_data():
    global connection_status, total_data_received, total_bytes_received
    global velocity_x, velocity_y, velocity_z, last_time
    global acc_x_sum, acc_y_sum, acc_z_sum, num_samples

    while not stop_event.is_set():
        try:
            data, addr = sock.recvfrom(1024)
            connection_status = "🟢 Connected"
            total_bytes_received += len(data)
            total_data_received += 1

            # Converte dados
            ax, ay, az = np.frombuffer(data[:6], dtype=np.int16) / 16384.0  # G -> m/s²
            acc_x_sum += ax * 9.81
            acc_y_sum += ay * 9.81
            acc_z_sum += az * 9.81
            num_samples += 1

            current_time = time.time()
            dt = current_time - last_time  # Tempo entre amostras

            # Atualiza velocidade a cada 1 segundo
            if num_samples >= 10:  # Media de 10 amostras antes de atualizar
                avg_ax = acc_x_sum / num_samples
                avg_ay = acc_y_sum / num_samples
                avg_az = acc_z_sum / num_samples

                velocity_x += avg_ax * dt
                velocity_y += avg_ay * dt
                velocity_z += avg_az * dt

                acc_x_sum, acc_y_sum, acc_z_sum = 0.0, 0.0, 0.0
                num_samples = 0

            last_time = current_time

        except Exception as e:
            print(f"Erro ao receber dados: {e}")
            connection_status = "🔴 Disconnected"


def print_status():
    global total_data_received, total_bytes_received, velocity_x, velocity_y, velocity_z

    while not stop_event.is_set():
        time.sleep(DATA_UPDATE_INTERVAL)

        speed = (velocity_x**2 + velocity_y**2 + velocity_z**2) ** 0.5
        bandwidth_bps = (total_bytes_received * 8) / DATA_UPDATE_INTERVAL if total_bytes_received else 0
        data_rate = total_data_received / DATA_UPDATE_INTERVAL if total_data_received else 0

        print(f"\n📡 {connection_status}")
        print(f"🚀 Velocidade: {speed:.2f} m/s")
        print(f"📈 Taxa de Dados: {data_rate:.2f} pacotes/s")
        print(f"📊 Largura de Banda: {bandwidth_bps:.2f} bps")
        print(f"⏱️ Latência: {latency:.2f} ms" if latency is not None else "⏱️ Sem resposta de latência")

        # Reset a cada intervalo
        total_data_received, total_bytes_received = 0, 0

        # **Reset da velocidade para evitar acumulação infinita**
        velocity_x, velocity_y, velocity_z = 0.0, 0.0, 0.0


# Iniciar Threads
threading.Thread(target=receive_data, daemon=True).start()
threading.Thread(target=print_status, daemon=True).start()
threading.Thread(target=keepConnected, daemon=True).start()

# Main Loop
if __name__ == "__main__":
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_event.set()
        print("Programa encerrado.")
