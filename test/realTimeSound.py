import socket
import time
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque
import threading
import sounddevice as sd
import queue

# 🔹 Configuração de áudio
SAMPLE_RATE = 44100  # Hz (Taxa de amostragem padrão)
BLOCK_SIZE = 512  # 🔹 Reduzido para menor latência
AMPLITUDE = 0.3  # Volume ajustado
DURATION = BLOCK_SIZE / SAMPLE_RATE  # Duração dinâmica

# 🔹 Fila de áudio ajustada para evitar atraso
audio_queue = queue.Queue(maxsize=5)  # 🔹 Reduzi para 5 pacotes (antes era 20)

# 🔹 Função para converter giroscópio em som
def process_vibration_data(values):
    """ Converte os dados do giroscópio para um som mais "grrrrgrgrr" realista """
    base_freq = np.clip(abs(values[2]) * 2, 50, 1500)  # 🔹 Frequência baseada no giroscópio
    t = np.linspace(0, DURATION, BLOCK_SIZE, False)
    
    # 🔹 Onda senoidal com modulação (para quebrar o som "piiipiiipii")
    modulation = np.sin(2 * np.pi * (base_freq / 5) * t) * 0.3
    waveform = AMPLITUDE * np.sin(2 * np.pi * base_freq * t + modulation)

    # 🔹 Adiciona ruído branco (para um som mais "grgrgrgr")
    noise = np.random.uniform(-0.2, 0.2, BLOCK_SIZE)
    waveform += noise

    # 🔹 Filtro passa-baixa (remove sons estridentes)
    waveform = np.convolve(waveform, np.ones(5)/5, mode="same")
    
    return waveform.astype(np.float32)

# 🔹 Callback de áudio ajustado
def audio_callback(outdata, frames, time, status):
    """ Reproduz áudio em tempo real sem lag """
    if not audio_queue.empty():
        samples = audio_queue.get_nowait()
        if len(samples) < frames:
            samples = np.pad(samples, (0, frames - len(samples)))  # Ajusta tamanho
        outdata[:] = samples.reshape(-1, 1)
    else:
        outdata[:] = np.zeros((frames, 1))  # 🔹 Silêncio se a fila estiver vazia

# 🔹 Iniciar stream de áudio
stream = sd.OutputStream(
    samplerate=SAMPLE_RATE,
    blocksize=BLOCK_SIZE,
    channels=1,
    callback=audio_callback
)
stream.start()

# 🔹 Configuração do UDP
ESP_PORT = 12345
DISCOVER_MSG = b"DISCOVER_VIBS_SERVER"
KEEP_ALIVE_INTERVAL = 3  # segundos
PLOT_WINDOW = 1000  # Número de amostras no gráfico
MAX_SAMPLES = 5000  # Para análise FFT

# 🔹 Variáveis globais
stop_thread = False
sample_idx = 0

# 🔹 Buffers para gráficos
x_data = deque(maxlen=PLOT_WINDOW)
gy_x = deque(maxlen=PLOT_WINDOW)
gy_y = deque(maxlen=PLOT_WINDOW)
gy_z = deque(maxlen=PLOT_WINDOW)

# 🔹 Buffers para FFT
raw_gy_x = deque(maxlen=MAX_SAMPLES)
raw_gy_y = deque(maxlen=MAX_SAMPLES)
raw_gy_z = deque(maxlen=MAX_SAMPLES)

# 🔹 Configuração do gráfico
fig, ax = plt.subplots(figsize=(12, 6))
ax.set_ylim(-32768, 32768)
ax.set_title("Real-time Gyroscope Data")
ax.set_xlabel("Samples")
ax.set_ylabel("Value")

# 🔹 Criar linhas do gráfico
line_x, = ax.plot([], [], 'r-', label='X', alpha=0.7)
line_y, = ax.plot([], [], 'g-', label='Y', alpha=0.7)
line_z, = ax.plot([], [], 'b-', label='Z', alpha=0.7)
ax.legend()

# 🔹 Configuração do socket UDP
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", ESP_PORT))
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

# 🔹 Keep-alive thread (sends DISCOVER messages)
def keepConnected():
    while not stop_thread:
        try:
            sock.sendto(DISCOVER_MSG, ("192.168.4.1", ESP_PORT))
            time.sleep(KEEP_ALIVE_INTERVAL)
        except:
            break

# 🔹 Conectar ao ESP32
print("Connecting to ESP32...")
sock.sendto(DISCOVER_MSG, ("192.168.4.1", ESP_PORT))
while True:
    data, addr = sock.recvfrom(1024)
    if data == b"SERVER_ACK":
        print(f"Connected to ESP32 at {addr[0]}")
        keep_alive_thread = threading.Thread(target=keepConnected)
        keep_alive_thread.daemon = True
        keep_alive_thread.start()
        break

# 🔹 Função para atualizar gráfico
def update_plot(frame):
    global sample_idx
    try:
        data, addr = sock.recvfrom(1024)
        if data == b"SERVER_ACK":
            return line_x, line_y, line_z
        
        # 🔹 Processar dados do ESP32
        batch = data.decode().strip().split("\n")
        for sample in batch:
            values = [int(x) for x in sample.split(',')]
            sample_idx += 1

            # 🔹 Atualizar buffers do gráfico
            x_data.append(sample_idx)
            gy_x.append(values[0])
            gy_y.append(values[1])
            gy_z.append(values[2])

            # 🔹 Armazenar dados para FFT
            raw_gy_x.append(values[0])
            raw_gy_y.append(values[1])
            raw_gy_z.append(values[2])

            # 🔹 Gerar onda sonora baseada no giroscópio
            waveform = process_vibration_data(values)
            if audio_queue.qsize() < 3:  # 🔹 Reduzi o tamanho da fila para evitar atraso
                audio_queue.put(waveform)

        # 🔹 Atualizar gráfico
        x_min = max(0, sample_idx - PLOT_WINDOW)
        x_max = sample_idx
        line_x.set_data(list(x_data), list(gy_x))
        line_y.set_data(list(x_data), list(gy_y))
        line_z.set_data(list(x_data), list(gy_z))
        ax.set_xlim(x_min, x_max)
    
    except Exception as e:
        print(f"Error: {e}")
    
    return line_x, line_y, line_z

# 🔹 Animação do gráfico
ani = animation.FuncAnimation(
    fig,
    update_plot,
    interval=1,
    blit=True,
    cache_frame_data=False
)

# 🔹 Rodar programa
try:
    plt.show()
except KeyboardInterrupt:
    stop_thread = True
    keep_alive_thread.join()
    sock.close()
    print("Connection closed")
    
finally:
    sock.close()
    print("Connection closed")
