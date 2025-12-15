import socket
import threading
import json
import pygame
import time

DISCOVERY_PORT = 50001
TCP_PORT = 50000

# Discover rooms
def discover_rooms(timeout=1.5):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(0.4)

    found = []
    start = time.time()

    while time.time() - start < timeout:
        sock.sendto(b"DISCOVER_ROOM", ("<broadcast>", DISCOVERY_PORT))
        try:
            data, addr = sock.recvfrom(1024)
            info = json.loads(data.decode())
            found.append(info)
        except:
            pass

    return found

class Client:
    def __init__(self):
        self.sock = None
        self.players = []
        self.running = True

    def connect(self, host):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, TCP_PORT))
        threading.Thread(target=self.recv_loop, daemon=True).start()

    def recv_loop(self):
        buf = b""
        while self.running:
            try:
                data = self.sock.recv(4096)
                if not data:
                    break
                buf += data
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    msg = json.loads(line.decode())
                    if msg["type"] == "welcome":
                        self.id = msg["id"]
                    elif msg["type"] == "state":
                        self.players = msg["players"]
            except:
                break

    def send_input(self, dx, dy):
        msg = json.dumps({"dx": dx, "dy": dy}) + "\n"
        try:
            self.sock.sendall(msg.encode())
        except:
            pass

# ---------------------- PYGAME LOOP ----------------------
pygame.init()
screen = pygame.display.set_mode((1000, 700))
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 24)

client = Client()

rooms = discover_rooms()
if rooms:
    print("Found rooms:", rooms)
    client.connect(rooms[0]["host"])   # auto-join first found
else:
    print("No rooms found.")

running = True
while running:
    dx = dy = 0
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False

    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT]: dx = -5
    if keys[pygame.K_RIGHT]: dx = 5
    if keys[pygame.K_UP]: dy = -5
    if keys[pygame.K_DOWN]: dy = 5

    client.send_input(dx, dy)

    # draw
    screen.fill((30, 30, 30))
    for p in client.players:
        pygame.draw.rect(screen, (0,255,0), (p["x"], p["y"], 40, 40))

    # sidebar showing connected player IDs (updates in real-time)
    sidebar_w = 220
    sx = screen.get_width() - sidebar_w
    pygame.draw.rect(screen, (40, 40, 40), (sx, 0, sidebar_w, screen.get_height()))
    hdr = font.render("Players", True, (255, 255, 255))
    screen.blit(hdr, (sx + 10, 10))
    for i, p in enumerate(client.players):
        y = 40 + i * 28
        my_id = getattr(client, "id", None)
        color = (255, 220, 0) if my_id and p.get("id") == my_id else (200, 200, 200)
        txt = font.render(p.get("id", "?"), True, color)
        screen.blit(txt, (sx + 10, y))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
client.running = False
