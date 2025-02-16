import socket
import threading
import json
import random
import time

class GameServer:
    def __init__(self, host='localhost', port=5555):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((host, port))
        self.server.listen()
        
        self.clients = {}
        self.balls = []
        self.scores = {}
        
        # Generate initial balls
        for _ in range(10):
            self.balls.append({
                'x': random.randint(50, 750),
                'y': random.randint(50, 550),
                'color': (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            })
    
    def handle_client(self, conn, addr):
        # Send initial player position
        player_id = len(self.clients)
        initial_pos = {'x': random.randint(50, 750), 'y': random.randint(50, 550)}
        self.clients[conn] = initial_pos
        self.scores[conn] = 0
        
        conn.send(json.dumps({
            'player_id': player_id,
            'position': initial_pos,
            'balls': self.balls
        }).encode())
        
        while True:
            try:
                data = conn.recv(1024).decode()
                if not data:
                    break
                
                data = json.loads(data)
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
                
                # Send game state to all clients
                game_state = {
                    'players': {i: pos for i, pos in enumerate(self.clients.values())},
                    'balls': self.balls,
                    'scores': {i: score for i, score in enumerate(self.scores.values())}
                }
                
                for client in self.clients:
                    client.send(json.dumps(game_state).encode())
                    
            except:
                break
        
        del self.clients[conn]
        del self.scores[conn]
        conn.close()
    
    def check_collision(self, rect1, rect2):
        return (rect1['x'] < rect2['x'] + rect2['width'] and
                rect1['x'] + rect1['width'] > rect2['x'] and
                rect1['y'] < rect2['y'] + rect2['height'] and
                rect1['y'] + rect1['height'] > rect2['y'])
    
    def start(self):
        print("Server started, waiting for connections...")
        while True:
            conn, addr = self.server.accept()
            print(f"Connected to: {addr}")
            thread = threading.Thread(target=self.handle_client, args=(conn, addr))
            thread.start()

if __name__ == "__main__":
    # To run the server
     server = GameServer()
     server.start()  