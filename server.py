import socket
import threading
import json
import random
import time

class GameServer:
    def __init__(self, host='0.0.0.0', port=5555):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Allow port reuse
        self.server.bind((host, port))
        self.server.listen()
        
        self.clients = {}
        self.balls = []
        self.scores = {}
        self.client_lock = threading.Lock()  # Add thread lock for client operations
        
        # Generate initial balls
        for _ in range(10):
            self.balls.append({
                'x': random.randint(50, 750),
                'y': random.randint(50, 550),
                'color': (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            })
    
    def handle_client(self, conn, addr):
        try:
            # Send initial player position
            with self.client_lock:
                player_id = len(self.clients)
                initial_pos = {'x': random.randint(50, 750), 'y': random.randint(50, 550)}
                self.clients[conn] = initial_pos
                self.scores[conn] = 0
            
            # Set timeout for client connection
            conn.settimeout(1.0)
            
            # Send initial game state
            initial_state = {
                'player_id': player_id,
                'position': initial_pos,
                'balls': self.balls
            }
            self.safe_send(conn, initial_state)
            
            while True:
                try:
                    data = conn.recv(1024).decode()
                    if not data:
                        print(f"Client {addr} disconnected (no data)")
                        break
                    
                    data = json.loads(data)
                    with self.client_lock:
                        self.clients[conn] = {'x': data['x'], 'y': data['y']}
                        
                        # Check ball collection
                        player_rect = {'x': data['x'], 'y': data['y'], 'width': 40, 'height': 40}
                        for ball in self.balls[:]:
                            ball_rect = {'x': ball['x'], 'y': ball['y'], 'width': 20, 'height': 20}
                            if self.check_collision(player_rect, ball_rect):
                                self.balls.remove(ball)
                                self.scores[conn] += 1
                                # Generate new ball
                                self.balls.append({
                                    'x': random.randint(50, 750),
                                    'y': random.randint(50, 550),
                                    'color': (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
                                })
                    
                    # Prepare and send game state
                    game_state = self.prepare_game_state()
                    self.broadcast_game_state(game_state)
                    
                except socket.timeout:
                    # Send ping to check if client is still connected
                    try:
                        self.safe_send(conn, {"ping": True})
                    except:
                        print(f"Client {addr} disconnected (timeout)")
                        break
                except json.JSONDecodeError:
                    print(f"Client {addr} sent invalid data")
                    continue
                except Exception as e:
                    print(f"Error handling client {addr}: {e}")
                    break
        
        finally:
            # Clean up client connection
            with self.client_lock:
                if conn in self.clients:
                    del self.clients[conn]
                if conn in self.scores:
                    del self.scores[conn]
            try:
                conn.close()
            except:
                pass
            print(f"Client {addr} cleanup complete")
    
    def safe_send(self, conn, data):
        try:
            conn.send(json.dumps(data).encode())
        except Exception as e:
            print(f"Error sending data: {e}")
            raise
    
    def prepare_game_state(self):
        with self.client_lock:
            return {
                'players': {i: pos for i, pos in enumerate(self.clients.values())},
                'balls': self.balls,
                'scores': {i: score for i, score in enumerate(self.scores.values())}
            }
    
    def broadcast_game_state(self, game_state):
        with self.client_lock:
            disconnected_clients = []
            for client in self.clients:
                try:
                    self.safe_send(client, game_state)
                except:
                    disconnected_clients.append(client)
            
            # Clean up disconnected clients
            for client in disconnected_clients:
                if client in self.clients:
                    del self.clients[client]
                if client in self.scores:
                    del self.scores[client]
    
    def check_collision(self, rect1, rect2):
        return (rect1['x'] < rect2['x'] + rect2['width'] and
                rect1['x'] + rect1['width'] > rect2['x'] and
                rect1['y'] < rect2['y'] + rect2['height'] and
                rect1['y'] + rect1['height'] > rect2['y'])
    
    def start(self):
        print("Server started, waiting for connections...")
        while True:
            try:
                conn, addr = self.server.accept()
                print(f"Connected to: {addr}")
                thread = threading.Thread(target=self.handle_client, args=(conn, addr))
                thread.daemon = True
                thread.start()
            except Exception as e:
                print(f"Error accepting connection: {e}")

if __name__ == "__main__":
    # To run the server
     server = GameServer('0.0.0.0', 5555)
     server.start()