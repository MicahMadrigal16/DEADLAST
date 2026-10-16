
import pygame
import random
import sys
import math

pygame.init()

# ==================================================
# WINDOW
# ==================================================
WIDTH, HEIGHT = 900, 600
FPS = 60

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("DEADLAST")
clock = pygame.time.Clock()

# ==================================================
# COLORS
# ==================================================
BLACK = (8, 7, 11)
DARK = (18, 12, 18)
PANEL = (25, 12, 19)
RED = (175, 15, 38)
BRIGHT_RED = (240, 35, 55)
DARK_RED = (75, 8, 22)
WHITE = (235, 225, 225)
GRAY = (125, 105, 115)
GREEN = (75, 220, 110)
YELLOW = (255, 205, 85)

# ==================================================
# FONTS
# ==================================================
title_font = pygame.font.Font(None, 96)
heading_font = pygame.font.Font(None, 58)
button_font = pygame.font.Font(None, 34)
ui_font = pygame.font.Font(None, 28)
small_font = pygame.font.Font(None, 22)

# ==================================================
# SETTINGS
# ==================================================
PLAYER_SIZE = 26
PLAYER_SPEED = 5
ENEMY_SIZE = 23
ENEMY_SPEED = 2
MAX_HEALTH = 100
SURVIVAL_TIME = 30

game_state = "menu"
player = None
enemies = []
health = MAX_HEALTH
start_time = 0
last_damage_time = 0
last_spawn_second = 0


# ==================================================
# PIXEL-STYLE BUTTON
# ==================================================
class Button:
    def __init__(self, text, center, width=290, height=56):
        self.text = text
        self.rect = pygame.Rect(0, 0, width, height)
        self.rect.center = center

    def draw(self):
        hovered = self.rect.collidepoint(pygame.mouse.get_pos())

        fill = (55, 8, 18) if hovered else (18, 9, 15)
        border = BRIGHT_RED if hovered else RED

        pygame.draw.rect(screen, fill, self.rect)
        pygame.draw.rect(screen, border, self.rect, 3)

        # Pixel-like corner details
        x, y, w, h = self.rect
        for px, py in [
            (x, y), (x + w - 7, y),
            (x, y + h - 7), (x + w - 7, y + h - 7)
        ]:
            pygame.draw.rect(screen, border, (px, py, 7, 7))

        if hovered:
            pygame.draw.rect(
                screen, BRIGHT_RED,
                (x + 12, y + h // 2 - 5, 10, 10)
            )

        label = button_font.render(self.text, True, WHITE)
        screen.blit(label, label.get_rect(center=self.rect.center))

    def clicked(self, event):
        return (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and self.rect.collidepoint(event.pos)
        )


start_button = Button("START GAME", (225, 335), 310, 58)
howto_button = Button("HOW TO PLAY", (225, 410), 310, 58)
quit_button = Button("QUIT GAME", (225, 485), 310, 58)

back_button = Button("BACK TO MENU", (WIDTH // 2, 520), 280)
resume_button = Button("RESUME", (WIDTH // 2, 345))
pause_menu_button = Button("MAIN MENU", (WIDTH // 2, 420))
restart_button = Button("PLAY AGAIN", (WIDTH // 2, 385))
end_menu_button = Button("MAIN MENU", (WIDTH // 2, 455))


# ==================================================
# PIXEL-ART STYLE BACKGROUND
# ==================================================
def draw_menu_background():
    screen.fill(BLACK)

    # Blocky ground texture
    random.seed(14)
    for _ in range(210):
        x = random.randrange(WIDTH)
        y = random.randrange(HEIGHT)
        size = random.choice([3, 4, 6, 8])
        shade = random.choice([
            (20, 13, 20), (30, 13, 21),
            (39, 13, 22), (25, 20, 25)
        ])
        pygame.draw.rect(screen, shade, (x, y, size, size))

    # Ruined wall silhouettes
    pygame.draw.rect(screen, (15, 10, 16), (0, 0, WIDTH, 48))
    pygame.draw.rect(screen, DARK_RED, (0, 45, WIDTH, 5))

    # Fence on the right side
    fence_color = (55, 32, 39)
    for x in range(560, 890, 35):
        pygame.draw.rect(screen, fence_color, (x, 65, 5, 240))
    for y in (95, 175, 255):
        pygame.draw.rect(screen, fence_color, (550, y, 340, 4))

    # Broken fence posts
    pygame.draw.rect(screen, (70, 35, 42), (615, 65, 7, 55))
    pygame.draw.rect(screen, (70, 35, 42), (790, 175, 7, 70))

    # Red warning light
    pygame.draw.rect(screen, DARK_RED, (800, 40, 42, 26))
    pygame.draw.rect(screen, BRIGHT_RED, (809, 47, 24, 10))

    # Debris
    pygame.draw.rect(screen, (42, 26, 32), (650, 400, 45, 14))
    pygame.draw.rect(screen, (33, 25, 30), (730, 435, 32, 22))
    pygame.draw.rect(screen, (55, 30, 38), (600, 500, 65, 12))

    # Pixel-art burning barrel
    pygame.draw.rect(screen, (68, 30, 35), (810, 450, 40, 64))
    pygame.draw.rect(screen, RED, (816, 440, 28, 18))
    pygame.draw.rect(screen, (255, 100, 20), (822, 425, 15, 20))
    pygame.draw.rect(screen, YELLOW, (827, 432, 6, 12))
    pygame.draw.rect(screen, (95, 40, 37), (810, 466, 40, 5))
    pygame.draw.rect(screen, (95, 40, 37), (810, 492, 40, 5))

    # Survivors and zombies in the distance
    draw_pixel_character(690, 300, RED, zombie=True)
    draw_pixel_character(800, 350, DARK_RED, zombie=True)
    draw_pixel_character(630, 410, RED, zombie=True)
    draw_pixel_character(745, 510, DARK_RED, zombie=True)

    random.seed()


def draw_pixel_character(x, y, color, zombie=False):
    # Simple pixel character built from rectangles
    pygame.draw.rect(screen, color, (x + 6, y, 12, 12))
    pygame.draw.rect(screen, color, (x + 2, y + 12, 20, 16))
    pygame.draw.rect(screen, color, (x, y + 14, 5, 13))
    pygame.draw.rect(screen, color, (x + 19, y + 14, 5, 13))
    pygame.draw.rect(screen, color, (x + 4, y + 27, 6, 9))
    pygame.draw.rect(screen, color, (x + 14, y + 27, 6, 9))

    if zombie:
        pygame.draw.rect(screen, BRIGHT_RED, (x + 8, y + 4, 3, 3))
        pygame.draw.rect(screen, BRIGHT_RED, (x + 14, y + 4, 3, 3))


# ==================================================
# GAME FUNCTIONS
# ==================================================
def spawn_enemy():
    side = random.choice(["top", "bottom", "left", "right"])

    if side == "top":
        x, y = random.randint(0, WIDTH - ENEMY_SIZE), 0
    elif side == "bottom":
        x, y = random.randint(0, WIDTH - ENEMY_SIZE), HEIGHT - ENEMY_SIZE
    elif side == "left":
        x, y = 0, random.randint(0, HEIGHT - ENEMY_SIZE)
    else:
        x, y = WIDTH - ENEMY_SIZE, random.randint(0, HEIGHT - ENEMY_SIZE)

    enemies.append(pygame.Rect(x, y, ENEMY_SIZE, ENEMY_SIZE))


def reset_game():
    global player, enemies, health, start_time
    global last_damage_time, last_spawn_second, game_state

    player = pygame.Rect(
        WIDTH // 2, HEIGHT // 2, PLAYER_SIZE, PLAYER_SIZE
    )

    enemies = []
    for _ in range(5):
        spawn_enemy()

    health = MAX_HEALTH
    start_time = pygame.time.get_ticks()
    last_damage_time = start_time
    last_spawn_second = 0
    game_state = "playing"


def draw_text(text, font, color, x, y, centered=False):
    image = font.render(text, True, color)
    if centered:
        screen.blit(image, image.get_rect(center=(x, y)))
    else:
        screen.blit(image, (x, y))


def move_player():
    keys = pygame.key.get_pressed()
    dx = dy = 0

    if keys[pygame.K_w] or keys[pygame.K_UP]:
        dy -= PLAYER_SPEED
    if keys[pygame.K_s] or keys[pygame.K_DOWN]:
        dy += PLAYER_SPEED
    if keys[pygame.K_a] or keys[pygame.K_LEFT]:
        dx -= PLAYER_SPEED
    if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
        dx += PLAYER_SPEED

    if dx and dy:
        dx *= 0.7071
        dy *= 0.7071

    player.x += round(dx)
    player.y += round(dy)
    player.clamp_ip(screen.get_rect())


def move_enemies():
    for enemy in enemies:
        dx = player.centerx - enemy.centerx
        dy = player.centery - enemy.centery
        distance = max(1, math.hypot(dx, dy))

        enemy.x += round(dx / distance * ENEMY_SPEED)
        enemy.y += round(dy / distance * ENEMY_SPEED)


def draw_health_bar():
    x, y = 20, 54
    width, height = 200, 18

    pygame.draw.rect(screen, DARK, (x, y, width, height))
    current = int(width * max(0, health) / MAX_HEALTH)
    color = GREEN if health > 30 else BRIGHT_RED
    pygame.draw.rect(screen, color, (x, y, current, height))
    pygame.draw.rect(screen, WHITE, (x, y, width, height), 2)

    draw_text(f"HEALTH: {max(0, health)}", ui_font, WHITE, x, y - 27)


def draw_game():
    screen.fill(BLACK)

    # Pixel ground
    for x in range(0, WIDTH, 50):
        pygame.draw.line(screen, (23, 15, 21), (x, 0), (x, HEIGHT))
    for y in range(0, HEIGHT, 50):
        pygame.draw.line(screen, (23, 15, 21), (0, y), (WIDTH, y))

    pygame.draw.rect(screen, DARK_RED, (5, 5, WIDTH - 10, HEIGHT - 10), 3)

    # Player
    pygame.draw.rect(screen, GREEN, player)
    pygame.draw.rect(screen, WHITE, player, 2)

    # Enemies
    for enemy in enemies:
        pygame.draw.rect(screen, RED, enemy)
        pygame.draw.rect(screen, BRIGHT_RED, enemy, 2)
        pygame.draw.rect(
            screen, YELLOW,
            (enemy.x + 5, enemy.y + 6, 4, 4)
        )
        pygame.draw.rect(
            screen, YELLOW,
            (enemy.x + 15, enemy.y + 6, 4, 4)
        )

    draw_health_bar()

    elapsed = (pygame.time.get_ticks() - start_time) // 1000
    remaining = max(0, SURVIVAL_TIME - elapsed)

    draw_text(f"TIME: {remaining}s", ui_font, YELLOW, WIDTH - 140, 20)
    draw_text(f"ENEMIES: {len(enemies)}", ui_font, WHITE, WIDTH - 175, 55)
    draw_text("ESC / P: PAUSE", small_font, GRAY, WIDTH // 2 - 70, 20)

    return remaining


# ==================================================
# MENUS
# ==================================================
def draw_menu():
    draw_menu_background()

    # Dark title panel
    pygame.draw.rect(screen, (10, 7, 12), (28, 75, 400, 150))
    pygame.draw.rect(screen, DARK_RED, (28, 75, 400, 150), 2)

    draw_text("DEADLAST", title_font, RED, 225, 125, centered=True)
    draw_text(
        "HOW LONG CAN YOU SURVIVE?",
        small_font, WHITE, 225, 190, centered=True
    )

    start_button.draw()
    howto_button.draw()
    quit_button.draw()

    draw_text(
        "MOVE: WASD / ARROWS",
        small_font, GRAY, 65, 555
    )
    draw_text(
        "PAUSE: ESC / P",
        small_font, GRAY, 65, 575
    )


def draw_how_to_play():
    draw_menu_background()

    pygame.draw.rect(screen, (10, 7, 12), (80, 65, 740, 465))
    pygame.draw.rect(screen, RED, (80, 65, 740, 465), 3)

    draw_text(
        "HOW TO PLAY", heading_font, RED,
        WIDTH // 2, 115, centered=True
    )

    lines = [
        ("OBJECTIVE", YELLOW),
        ("Survive for 30 seconds without losing all your health.", WHITE),
        ("", WHITE),
        ("CONTROLS", YELLOW),
        ("WASD / ARROW KEYS - Move", WHITE),
        ("ESC / P - Pause or resume", WHITE),
        ("R - Restart after winning or losing", WHITE),
        ("", WHITE),
        ("WARNING", YELLOW),
        ("Red enemies chase you and damage you on contact.", WHITE),
        ("Keep moving. Do not get surrounded!", WHITE),
    ]

    y = 175
    for text, color in lines:
        draw_text(text, ui_font, color, WIDTH // 2, y, centered=True)
        y += 28

    back_button.draw()


def draw_overlay():
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 210))
    screen.blit(overlay, (0, 0))


def draw_pause():
    draw_game()
    draw_overlay()

    draw_text("PAUSED", title_font, RED, WIDTH // 2, 245, centered=True)
    draw_text(
        "Your run is safe. Take a breath.",
        small_font, WHITE, WIDTH // 2, 290, centered=True
    )

    resume_button.draw()
    pause_menu_button.draw()


def draw_end_screen():
    draw_game()
    draw_overlay()

    if game_state == "won":
        title, color = "YOU SURVIVED!", GREEN
    else:
        title, color = "YOU DIED", BRIGHT_RED

    draw_text(title, heading_font, color, WIDTH // 2, 285, centered=True)
    draw_text(
        "Press R or select an option",
        small_font, WHITE, WIDTH // 2, 330, centered=True
    )

    restart_button.draw()
    end_menu_button.draw()


# ==================================================
# MAIN LOOP
# ==================================================
running = True

while running:
    clock.tick(FPS)
    now = pygame.time.get_ticks()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            # ESC now pauses/resumes during gameplay.
            if event.key in (pygame.K_ESCAPE, pygame.K_p):
                if game_state == "playing":
                    game_state = "paused"
                elif game_state == "paused":
                    game_state = "playing"
                elif game_state == "howto":
                    game_state = "menu"
                elif game_state in ("won", "lost"):
                    game_state = "menu"
                elif game_state == "menu":
                    running = False

            if event.key == pygame.K_r and game_state in ("won", "lost"):
                reset_game()

        # Main menu
        if game_state == "menu":
            if start_button.clicked(event):
                reset_game()
            elif howto_button.clicked(event):
                game_state = "howto"
            elif quit_button.clicked(event):
                running = False

        elif game_state == "howto":
            if back_button.clicked(event):
                game_state = "menu"

        elif game_state == "paused":
            if resume_button.clicked(event):
                game_state = "playing"
            elif pause_menu_button.clicked(event):
                game_state = "menu"

        elif game_state in ("won", "lost"):
            if restart_button.clicked(event):
                reset_game()
            elif end_menu_button.clicked(event):
                game_state = "menu"

    # Gameplay only updates while actively playing.
    if game_state == "playing":
        move_player()
        move_enemies()

        if now - last_damage_time >= 500:
            for enemy in enemies:
                if player.colliderect(enemy):
                    health -= 10
                    last_damage_time = now
                    break

        elapsed = (now - start_time) // 1000

        if (
            elapsed > 0
            and elapsed % 5 == 0
            and elapsed != last_spawn_second
            and len(enemies) < 15
        ):
            spawn_enemy()
            last_spawn_second = elapsed

        remaining = max(0, SURVIVAL_TIME - elapsed)

        if health <= 0:
            game_state = "lost"
        elif remaining <= 0:
            game_state = "won"

    # Render current screen
    if game_state == "menu":
        draw_menu()
    elif game_state == "howto":
        draw_how_to_play()
    elif game_state == "playing":
        draw_game()
    elif game_state == "paused":
        draw_pause()
    elif game_state in ("won", "lost"):
        draw_end_screen()

    pygame.display.flip()

pygame.quit()
sys.exit()
