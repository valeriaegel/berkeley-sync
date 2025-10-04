import socket
import threading
import time
import random
from datetime import datetime, timedelta
from config import COORDINATOR_PORT, NODE_PORTS, INITIAL_TIME_VARIATION


class Node:
    def __init__(self, node_id, port):
        self.node_id = node_id
        self.port = port
        # Simular un reloj con desfase aleatorio
        self.clock_offset = random.randint(-INITIAL_TIME_VARIATION, INITIAL_TIME_VARIATION)
        self.current_time = datetime.now() + timedelta(seconds=self.clock_offset)
        self.coordinator_socket = None
        self.running = True

    def get_current_time(self):
        self.current_time += timedelta(seconds=1)  # Simular paso del tiempo
        return self.current_time

    def connect_to_coordinator(self):
        try:
            self.coordinator_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.coordinator_socket.connect(('localhost', COORDINATOR_PORT))

            # Registrar nodo en el coordinador
            self.coordinator_socket.send(f"REGISTER:{self.node_id}".encode())
            response = self.coordinator_socket.recv(1024).decode()

            if response == "REGISTERED":
                print(f"Nodo {self.node_id} registrado exitosamente en el coordinador")
                return True
            else:
                print(f"Error registrando nodo {self.node_id}")
                return False

        except Exception as e:
            print(f"Error conectando al coordinador: {e}")
            return False

    def start_server(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(('localhost', self.port))
        server_socket.listen(1)
        print(f"Nodo {self.node_id} escuchando en puerto {self.port}")

        while self.running:
            try:
                client_socket, addr = server_socket.accept()
                threading.Thread(target=self.handle_request, args=(client_socket,)).start()
            except:
                break

        server_socket.close()

    def handle_request(self, client_socket):
        try:
            data = client_socket.recv(1024).decode()

            if data == "GET_TIME":
                current_time = self.get_current_time()
                client_socket.send(f"TIME:{current_time.isoformat()}".encode())

            elif data.startswith("ADJUST"):
                adjustment = float(data.split(":")[1])
                self.current_time += timedelta(seconds=adjustment)
                print(f"Nodo {self.node_id}: Ajuste aplicado: {adjustment:.2f} segundos")
                client_socket.send("ADJUSTED".encode())

        except Exception as e:
            print(f"Error manejando petición: {e}")
        finally:
            client_socket.close()

    def request_time_sync(self):
        while self.running:
            time.sleep(15)  # Solicitar sincronización cada 15 segundos
            if self.coordinator_socket:
                try:
                    current_time = self.get_current_time()
                    self.coordinator_socket.send(f"TIME_REQUEST:{current_time.isoformat()}".encode())
                    response = self.coordinator_socket.recv(1024).decode()

                    if response.startswith("TIME_DIFF"):
                        time_diff = float(response.split(":")[1])
                        print(f"Nodo {self.node_id}: Diferencia con coordinador: {time_diff:.2f} segundos")

                except Exception as e:
                    print(f"Error en sincronización: {e}")
                    # Intentar reconectar
                    self.connect_to_coordinator()

    def start(self):
        print(f"Iniciando nodo {self.node_id}...")
        print(f"Reloj inicial: {self.get_current_time()}")

        if not self.connect_to_coordinator():
            return

        # Hilo para el servidor del nodo
        server_thread = threading.Thread(target=self.start_server)
        server_thread.daemon = True
        server_thread.start()

        # Hilo para solicitudes periódicas de sincronización
        sync_thread = threading.Thread(target=self.request_time_sync)
        sync_thread.daemon = True
        sync_thread.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\nDeteniendo nodo {self.node_id}...")
            self.running = False
            if self.coordinator_socket:
                self.coordinator_socket.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Uso: python node.py <node_id>")
        sys.exit(1)

    node_id = sys.argv[1]
    port = NODE_PORTS[int(node_id) - 1]  # node1 -> puerto 8889, node2 -> puerto 8890

    node = Node(node_id, port)
    node.start()