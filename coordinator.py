import socket
import threading
import time
import random
from datetime import datetime, timedelta
from config import COORDINATOR_PORT, NODE_PORTS, SYNC_INTERVAL, INITIAL_TIME_VARIATION


class Coordinator:
    def __init__(self):
        # Simular un reloj con desfase aleatorio
        self.clock_offset = random.randint(-INITIAL_TIME_VARIATION, INITIAL_TIME_VARIATION)
        self.current_time = datetime.now() + timedelta(seconds=self.clock_offset)
        self.nodes = []
        self.running = True

    def get_current_time(self):
        self.current_time += timedelta(seconds=1)  # Simular paso del tiempo
        return self.current_time

    def start_server(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(('localhost', COORDINATOR_PORT))
        server_socket.listen(5)
        print(f"Coordinador escuchando en puerto {COORDINATOR_PORT}")

        while self.running:
            try:
                client_socket, addr = server_socket.accept()
                threading.Thread(target=self.handle_node, args=(client_socket,)).start()
            except:
                break

        server_socket.close()

    def handle_node(self, client_socket):
        try:
            data = client_socket.recv(1024).decode()
            if data.startswith("REGISTER"):
                node_id = data.split(":")[1]
                self.nodes.append((node_id, client_socket))
                print(f"Nodo {node_id} registrado")
                client_socket.send("REGISTERED".encode())

            elif data.startswith("TIME_REQUEST"):
                node_time_str = data.split(":")[1]
                node_time = datetime.fromisoformat(node_time_str)
                coordinator_time = self.get_current_time()

                # Calcular diferencia
                time_diff = (coordinator_time - node_time).total_seconds()
                print(f"Diferencia con nodo: {time_diff} segundos")
                client_socket.send(f"TIME_DIFF:{time_diff}".encode())

        except Exception as e:
            print(f"Error manejando nodo: {e}")

    def synchronize_clocks(self):
        while self.running:
            time.sleep(SYNC_INTERVAL)
            if len(self.nodes) < 2:
                print("Esperando más nodos para sincronización...")
                continue

            print("\n--- Iniciando sincronización Berkeley ---")
            times = [self.get_current_time()]

            # Recoger tiempos de todos los nodos
            for node_id, node_socket in self.nodes[:]:
                try:
                    # Solicitar tiempo actual del nodo
                    node_socket.send("GET_TIME".encode())
                    response = node_socket.recv(1024).decode()

                    if response.startswith("TIME:"):
                        node_time = datetime.fromisoformat(response.split(":")[1])
                        times.append(node_time)
                        print(f"Tiempo del nodo {node_id}: {node_time}")
                    else:
                        print(f"Respuesta inválida del nodo {node_id}")
                        self.nodes.remove((node_id, node_socket))

                except Exception as e:
                    print(f"Error comunicándose con nodo {node_id}: {e}")
                    self.nodes.remove((node_id, node_socket))

            # Calcular promedio (excluyendo outliers)
            if len(times) >= 2:
                time_diffs = [(t - times[0]).total_seconds() for t in times]

                # Calcular promedio simple
                avg_offset = sum(time_diffs) / len(time_diffs)

                # Ajustar reloj del coordinador
                adjustment = avg_offset
                self.current_time += timedelta(seconds=adjustment)
                print(f"Ajuste del coordinador: {adjustment:.2f} segundos")

                # Enviar ajustes a los nodos
                for i, (node_id, node_socket) in enumerate(self.nodes[:]):
                    if i + 1 < len(times):  # +1 porque times[0] es el coordinador
                        node_adjustment = avg_offset - time_diffs[i + 1]
                        try:
                            node_socket.send(f"ADJUST:{node_adjustment}".encode())
                            response = node_socket.recv(1024).decode()
                            if response == "ADJUSTED":
                                print(f"Nodo {node_id} ajustado: {node_adjustment:.2f} segundos")
                        except Exception as e:
                            print(f"Error ajustando nodo {node_id}: {e}")
                            self.nodes.remove((node_id, node_socket))

            print("--- Sincronización completada ---\n")

    def start(self):
        print("Iniciando coordinador Berkeley...")
        print(f"Reloj inicial: {self.get_current_time()}")

        # Hilo para el servidor
        server_thread = threading.Thread(target=self.start_server)
        server_thread.daemon = True
        server_thread.start()

        # Hilo para sincronización periódica
        sync_thread = threading.Thread(target=self.synchronize_clocks)
        sync_thread.daemon = True
        sync_thread.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nDeteniendo coordinador...")
            self.running = False


if __name__ == "__main__":
    coordinator = Coordinator()
    coordinator.start()