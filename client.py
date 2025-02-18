# client.py
import pygame
import socket
import json
import threading
import time
import math
import random

class GameClient:
    def __init__(self, host='localhost', port=5555):
        pygame.init()
        self.screen = pygame.display.set_mode((800, 600))
        pygame.display.set_caption("Forest Ball Collector")
        
        # Initialize background elements
        self.trees = [(x+random.randint(-20, 20), 350+random.randint(-10, 10)) 
                      for x in range(0, 800, 200)]
        self.clouds = [(random.randint(0, 800), random.randint(50, 150), 
                       random.randint(40, 60)) for _ in range(5)]
        
        self.running = True
        self.connected = False
        self.reconnect_host = host
        self.reconnect_port = port
        
        # Initialize game state
        self.player_id = None
        self.position = {'x': 400, 'y': 300}
        self.balls = []
        self.other_players = {}
        self.scores = {}
        self.facing_right = True
        self.animation_frame = 0
        self.animation_timer = 0
        
        # Connect to server
        self.connect_to_server(host, port)
        
        if self.connected:
            self.receive_thread = threading.Thread(target=self.receive_data)
            self.receive_thread.daemon = True
            self.receive_thread.start()

    def draw_cloud(self, x, y, size):
        cloud_color = (255, 255, 255)
        pygame.draw.circle(self.screen, cloud_color, (x, y), size)
        pygame.draw.circle(self.screen, cloud_color, (x + size*0.7, y), size*0.8)
        pygame.draw.circle(self.screen, cloud_color, (x - size*0.7, y), size*0.8)

    def draw_tree(self, x, y):
        # Tree trunk
        trunk_color = (139, 69, 19)
        leaves_color = (34, 139, 34)
        dark_leaves = (25, 100, 25)
        
        # Draw trunk
        pygame.draw.rect(self.screen, trunk_color, (x+10, y, 20, 80))
        
        # Draw multiple layers of leaves for depth
        for i in range(3):
            offset = i * 15
            points = [
                (x-15+i*5, y-offset+40),
                (x+20, y-offset-20),
                (x+55-i*5, y-offset+40)
            ]
            pygame.draw.polygon(self.screen, 
                              dark_leaves if i == 0 else leaves_color, 
                              points)

    def draw_background(self):
        # Sky gradient
        for y in range(600):
            sky_color = (
                135 - y//10,
                206 - y//10,
                235 - y//10
            )
            pygame.draw.line(self.screen, sky_color, (0, y), (800, y))
        
        # Sun with glow effect
        for radius in range(50, 30, -5):
            alpha = int(155 * (radius - 30) / 20)
            surf = pygame.Surface((800, 600), pygame.SRCALPHA)
            pygame.draw.circle(surf, (255, 255, 0, alpha), (700, 100), radius)
            self.screen.blit(surf, (0, 0))
        pygame.draw.circle(self.screen, (255, 255, 0), (700, 100), 30)
        
        # Clouds
        for cloud in self.clouds:
            self.draw_cloud(*cloud)
        
        # Ground
        pygame.draw.rect(self.screen, (34, 139, 34), (0, 450, 800, 150))
        
        # Draw grass details
        for x in range(0, 800, 10):
            grass_height = random.randint(5, 15)
            grass_color = (random.randint(30, 40), 
                         random.randint(130, 150), 
                         random.randint(30, 40))
            pygame.draw.line(self.screen, grass_color, 
                           (x, 450), (x, 450-grass_height))
        
        # Trees
        for tree_pos in self.trees:
            self.draw_tree(*tree_pos)

    def draw_character(self, x, y, is_current_player, facing_right):
        # Base colors
        if is_current_player:
            body_color = (34, 177, 76)  # Green for current player
        else:
            body_color = (70, 130, 180)  # Blue for other players
        
        # Create character surface with transparency
        char_surface = pygame.Surface((40, 60), pygame.SRCALPHA)
        
        # Bouncing animation
        bounce_offset = math.sin(self.animation_timer/200) * 3
        
        # Body
        pygame.draw.ellipse(char_surface, body_color, (5, 20, 30, 40))
        
        # Head
        pygame.draw.circle(char_surface, body_color, (20, 15), 12)
        
        # Eyes (adjust based on facing direction)
        eye_x = 16 if facing_right else 24
        pygame.draw.circle(char_surface, (255, 255, 255), (eye_x, 12), 4)
        pygame.draw.circle(char_surface, (255, 255, 255), (eye_x+8, 12), 4)
        pygame.draw.circle(char_surface, (0, 0, 0), (eye_x, 12), 2)
        pygame.draw.circle(char_surface, (0, 0, 0), (eye_x+8, 12), 2)
        
        # Add glow effect for current player
        if is_current_player:
            glow_surface = pygame.Surface((60, 80), pygame.SRCALPHA)
            pygame.draw.ellipse(glow_surface, (255, 255, 255, 64), (0, 0, 60, 80))
            self.screen.blit(glow_surface, (x-10, y-10+bounce_offset))
        
        # Flip surface if facing left
        if not facing_right:
            char_surface = pygame.transform.flip(char_surface, True, False)
        
        self.screen.blit(char_surface, (x, y+bounce_offset))

    def draw_magical_ball(self, x, y):
        # Ball floating animation
        float_offset = math.sin(self.animation_timer/500) * 5
        
        # Glowing effect
        for radius in range(15, 5, -2):
            alpha = int(155 * (radius - 5) / 10)
            surf = pygame.Surface((40, 40), pygame.SRCALPHA)
            color = (200, 220, 255, alpha)
            pygame.draw.circle(surf, color, (20, 20), radius)
            self.screen.blit(surf, (x-20, y-20+float_offset))
        
        # Core of the ball
        pygame.draw.circle(self.screen, (255, 255, 255), 
                         (x, y+float_offset), 5)

    def connect_to_server(self, host, port):
        try:
            print(f"Attempting to connect to {host}:{port}")
            self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client.settimeout(5.0)
            self.client.connect((host, port))
            
            print("Waiting for initial game state...")
            initial_data = self.client.recv(1024).decode()
            if not initial_data:
                raise Exception("No initial data received from server")
            
            initial_data = json.loads(initial_data)
            if not isinstance(initial_data, dict):
                raise Exception("Invalid initial data format")
            
            print("Initial data received:", initial_data)
            
            if 'player_id' not in initial_data or 'position' not in initial_data or 'balls' not in initial_data:
                raise Exception("Missing required fields in initial data")
            
            self.player_id = initial_data['player_id']
            self.position = initial_data['position']
            self.balls = initial_data['balls']
            self.connected = True
            print("Connected to server successfully")
            
        except Exception as e:
            print(f"Connection failed: {e}")
            self.connected = False

    def receive_data(self):
        while self.running and self.connected:
            try:
                data = self.client.recv(1024).decode()
                if not data:
                    print("No data received from server")
                    self.connected = False
                    break
                
                data = json.loads(data)
                if "ping" in data:
                    continue
                    
                if all(key in data for key in ['players', 'balls', 'scores']):
                    self.other_players = data['players']
                    self.balls = data['balls']
                    self.scores = data['scores']
                else:
                    print("Received incomplete game state")
                    
            except socket.timeout:
                continue
            except json.JSONDecodeError as e:
                print(f"Invalid data received: {e}")
                continue
            except Exception as e:
                print(f"Connection error: {e}")
                self.connected = False
                break

    def run(self):
        clock = pygame.time.Clock()
        font = pygame.font.Font(None, 36)
        reconnect_delay = 5
        last_reconnect_attempt = 0
        
        while self.running:
            current_time = time.time()
            self.animation_timer = pygame.time.get_ticks()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
            
            if not self.connected:
                self.screen.fill((255, 255, 255))
                if current_time - last_reconnect_attempt >= reconnect_delay:
                    reconnect_text = "Attempting to reconnect..."
                    self.connect_to_server(self.reconnect_host, self.reconnect_port)
                    last_reconnect_attempt = current_time
                    if self.connected:
                        self.receive_thread = threading.Thread(target=self.receive_data)
                        self.receive_thread.daemon = True
                        self.receive_thread.start()
                else:
                    wait_time = int(reconnect_delay - (current_time - last_reconnect_attempt))
                    reconnect_text = f"Reconnecting in {wait_time} seconds..."
                
                text = font.render(reconnect_text, True, (255, 0, 0))
                text_rect = text.get_rect(center=(400, 300))
                self.screen.blit(text, text_rect)
                pygame.display.flip()
                clock.tick(60)
                continue
            
            # Handle movement
            keys = pygame.key.get_pressed()
            moved = False
            if keys[pygame.K_LEFT]:
                self.position['x'] = max(0, self.position['x'] - 5)
                self.facing_right = False
                moved = True
            if keys[pygame.K_RIGHT]:
                self.position['x'] = min(760, self.position['x'] + 5)
                self.facing_right = True
                moved = True
            if keys[pygame.K_UP]:
                self.position['y'] = max(0, self.position['y'] - 5)
                moved = True
            if keys[pygame.K_DOWN]:
                self.position['y'] = min(540, self.position['y'] + 5)
                moved = True
            
            if moved:
                try:
                    self.client.send(json.dumps(self.position).encode())
                except Exception as e:
                    print(f"Failed to send position: {e}")
                    self.connected = False
                    continue
            
            # Draw game state
            self.draw_background()
            
            # Draw balls
            for ball in self.balls:
                self.draw_magical_ball(ball['x'], ball['y'])
            
            # Draw other players
            for pid, pos in self.other_players.items():
                self.draw_character(pos['x'], pos['y'], 
                                 int(pid) == self.player_id,
                                 self.facing_right)
            
            # Draw current player
            self.draw_character(self.position['x'], self.position['y'],
                              True, self.facing_right)
            
            # Draw scores
            score_surface = pygame.Surface((200, 100), pygame.SRCALPHA)
            pygame.draw.rect(score_surface, (0, 0, 0, 128), 
                           (0, 0, 200, 100), border_radius=10)
            for pid, score in self.scores.items():
                score_text = font.render(f"Player {pid}: {score}", 
                                       True, (255, 255, 255))
                score_surface.blit(score_text, (10, 10 + int(pid) * 30))
            self.screen.blit(score_surface, (10, 10))
            
            # Draw connection status
            status_text = "Connected" if self.connected else "Disconnected"
            status_color = (0, 255, 0) if self.connected else (255, 0, 0)
            status = font.render(status_text, True, status_color)
            self.screen.blit(status, (10, 570))
            
            pygame.display.flip()
            clock.tick(60)
        
        try:
            self.client.close()
        except:
            pass
        pygame.quit()

if __name__ == "__main__":
    try:
        client = GameClient('localhost', 5555)
        client.run()
    except Exception as e:
        print(f"Game crashed: {e}")
        import traceback
        traceback.print_exc()
        pygame.quit()