import socket
import threading
import json
import pygame
import time
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import server.server as srv

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
class Button:
    def __init__(self, rect, text):
        self.rect = pygame.Rect(rect)
        self.text = text

    def draw(self, surf, hover=False):
        color = (200, 200, 200) if hover else (160, 160, 160)
        pygame.draw.rect(surf, color, self.rect)
        txt = font.render(self.text, True, (0, 0, 0))
        tw, th = txt.get_size()
        surf.blit(txt, (self.rect.x + (self.rect.w - tw) // 2, self.rect.y + (self.rect.h - th) // 2))

    def is_hover(self, pos):
        return self.rect.collidepoint(pos)


def start_local_room_and_join():
    # start a server in background and join localhost
    server = srv.RoomServer()
    threading.Thread(target=server.start, daemon=True).start()
    time.sleep(0.2)
    client.connect("127.0.0.1")


# Menu state
state = "menu"  # menu or playing
menu_stage = "main"  # main or join_list or msg
message = ""
found_rooms = []

# buttons
btn_join = Button((400, 250, 200, 60), "Join Room")
btn_create = Button((400, 350, 200, 60), "Create Room")

running = True
while running:
    dx = dy = 0
    mouse_pos = pygame.mouse.get_pos()
    mouse_pressed = pygame.mouse.get_pressed()

    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False
        elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if state == "menu":
                if menu_stage == "main":
                    if btn_join.is_hover(mouse_pos):
                        # discover rooms and show list
                        found_rooms = discover_rooms()
                        if found_rooms:
                            menu_stage = "join_list"
                        else:
                            message = "No rooms found."
                            menu_stage = "msg"
                    elif btn_create.is_hover(mouse_pos):
                        start_local_room_and_join()
                        state = "playing"
                elif menu_stage == "join_list":
                    # check clicks on room entries
                    for i, r in enumerate(found_rooms):
                        rect = pygame.Rect(300, 200 + i * 70, 400, 60)
                        if rect.collidepoint(mouse_pos):
                            client.connect(r["host"])
                            state = "playing"
                            break
                elif menu_stage == "msg":
                    # click anywhere to return to main menu
                    menu_stage = "main"

    if state == "playing":
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]: dx = -5
        if keys[pygame.K_RIGHT]: dx = 5
        if keys[pygame.K_UP]: dy = -5
        if keys[pygame.K_DOWN]: dy = 5

        client.send_input(dx, dy)

        # draw game
        screen.fill((30, 30, 30))
        for p in client.players:
            pygame.draw.rect(screen, (0,255,0), (p["x"], p["y"], 40, 40))
            if getattr(client, "id", None) and p["id"] == client.id:
                pygame.draw.rect(screen, (255,255,255), (p["x"], p["y"], 40, 40), 3)
                text = font.render("You", True, (255,255,255))
                screen.blit(text, (p["x"], p["y"] - 30))

    else:
        # draw menu
        screen.fill((40, 40, 40))
        title = pygame.font.SysFont(None, 48).render("Multiplayer Car Game", True, (255,255,255))
        screen.blit(title, (350, 120))

        if menu_stage == "main":
            btn_join.draw(screen, btn_join.is_hover(mouse_pos))
            btn_create.draw(screen, btn_create.is_hover(mouse_pos))
        elif menu_stage == "join_list":
            for i, r in enumerate(found_rooms):
                rect = pygame.Rect(300, 200 + i * 70, 400, 60)
                pygame.draw.rect(screen, (180,180,180), rect)
                txt = font.render(f"{r.get('room_code','?')} - {r.get('host')}", True, (0,0,0))
                screen.blit(txt, (rect.x + 10, rect.y + 20))
        elif menu_stage == "msg":
            txt = font.render(message, True, (255,255,255))
            screen.blit(txt, (380, 300))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
client.running = False
