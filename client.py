import pygame
import socket
import json
import threading

class GameClient:
    def __init__(self, host='localhost', port=5555):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.connect((host, port))
        
        # Initialize Pygame
        pygame.init()
        self.screen = pygame.display.set_mode((800, 600))
        pygame.display.set_caption("Ball Grabber")
        
        # Get initial game state
        initial_data = json.loads(self.client.recv(1024).decode())
        self.player_id = initial_data['player_id']
        self.position = initial_data['position']
        self.balls = initial_data['balls']
        self.other_players = {}
        self.scores = {}
        
        # Start receiving thread
        self.receive_thread = threading.Thread(target=self.receive_data)
        self.receive_thread.daemon = True
        self.receive_thread.start()
    
    def receive_data(self):
        while True:
            try:
                data = json.loads(self.client.recv(1024).decode())
                self.other_players = data['players']
                self.balls = data['balls']
                self.scores = data['scores']
            except:
                break
    
    def run(self):
        clock = pygame.time.Clock()
        running = True
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
            
            # Handle player movement
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT]:
                self.position['x'] -= 5
            if keys[pygame.K_RIGHT]:
                self.position['x'] += 5
            if keys[pygame.K_UP]:
                self.position['y'] -= 5
            if keys[pygame.K_DOWN]:
                self.position['y'] += 5
            
            # Keep player in bounds
            self.position['x'] = max(0, min(self.position['x'], 760))
            self.position['y'] = max(0, min(self.position['y'], 560))
            
            # Send position to server
            self.client.send(json.dumps(self.position).encode())
            
            # Draw game state
            self.screen.fill((255, 255, 255))
            
            # Draw balls
            for ball in self.balls:
                pygame.draw.circle(self.screen, ball['color'], (ball['x'], ball['y']), 10)
            
            # Draw players
            for pid, pos in self.other_players.items():
                color = (255, 0, 0) if int(pid) == self.player_id else (0, 0, 255)
                pygame.draw.rect(self.screen, color, (pos['x'], pos['y'], 40, 40))
            
            # Draw scores
            font = pygame.font.Font(None, 36)
            for pid, score in self.scores.items():
                score_text = font.render(f"Player {pid}: {score}", True, (0, 0, 0))
                self.screen.blit(score_text, (10, 10 + int(pid) * 30))
            
            pygame.display.flip()
            clock.tick(60)
        
        pygame.quit()

if __name__ == "__main__":
    # To run the client
    client = GameClient()
    client.run()