
import pygame
import random
import math
import sys

pygame.init()

# ==================================================
# WINDOW AND SETTINGS
# ==================================================
WIDTH, HEIGHT = 900, 600
FPS = 60

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("DEADLAST")
clock = pygame.time.Clock()

SURVIVAL_TIME = 30
MAX_HEALTH = 100
PLAYER_SPEED = 230
ENEMY_SPEED = 65
BULLET_SPEED = 520
FIRE_COOLDOWN = 0.22
DAMAGE_COOLDOWN = 0.6

# ==================================================
# COLORS
# ==================================================
BLACK = (7, 6, 10)
DARK = (16, 12, 17)
GROUND = (29, 25, 30)
GROUND_LIGHT = (39, 32, 37)
CRACK = (12, 11, 15)
RED = (175, 15, 38)
DARK_RED = (75, 8, 22)
BRIGHT_RED = (240, 35, 55)
WHITE = (235, 225, 225)
GRAY = (100, 91, 99)
GREEN = (75, 220, 110)
YELLOW = (255, 205, 85)
ORANGE = (255, 110, 30)
METAL = (65, 61, 68)
RUST = (105, 48, 39)

# ==================================================
# FONTS
# ==================================================
title_font = pygame.font.Font(None, 96)
heading_font = pygame.font.Font(None, 58)
button_font = pygame.font.Font(None, 34)
ui_font = pygame.font.Font(None, 28)
small_font = pygame.font.Font(None, 22)

# ==================================================
# PIXEL-ART SPRITES
# ==================================================
def make_sprite(pattern, palette, scale=3):
    image = pygame.Surface(
        (len(pattern[0]), len(pattern)), pygame.SRCALPHA
    )

    for y, row in enumerate(pattern):
        for x, symbol in enumerate(row):
            if symbol != ".":
                image.set_at((x, y), palette[symbol])

    return pygame.transform.scale(
        image,
        (image.get_width() * scale, image.get_height() * scale)
    )


player_pattern = [
    "......SSSS......",
    ".....SSSSSS.....",
    ".....SSKKS......",
    ".....SSSSSS.....",
    "......BBBB......",
    "...GGGBBBBGGG...",
    "...GGGBBBBGGG...",
    "......BBBB......",
    ".....BBBBBB.....",
    ".....BWWBBB.....",
    ".....BWWBBB.....",
    "......BB.BB.....",
    "......BB.BB.....",
    "......BB.BB.....",
    ".....LLL.LLL....",
    ".....LLL.LLL....",
]

player_palette = {
    "S": (65, 38, 31),
    "K": (245, 185, 135),
    "B": (35, 40, 49),
    "G": (60, 110, 63),
    "W": (180, 35, 35),
    "L": (65, 65, 75),
}

zombie_pattern = [
    "......ZZZZ......",
    ".....ZZZZZZ.....",
    ".....ZEEZZZ.....",
    ".....ZZZZZZ.....",
    "......ZZZZ......",
    "...ZZZZZZZZZZ...",
    "...ZZZZZZZZZZ...",
    "......ZZZZ......",
    ".....ZZZZZZ.....",
    ".....ZZ.ZZZ.....",
    "....ZZ..ZZ.ZZ...",
    "....ZZ..ZZ.ZZ...",
    "....ZZ..ZZ.ZZ...",
    "....ZZ..ZZ.ZZ...",
]

zombie_palette = {
    "Z": (75, 95, 53),
    "E": (255, 45, 45),
}

player_sprite = make_sprite(player_pattern, player_palette)
zombie_sprite = make_sprite(zombie_pattern, zombie_palette)

# ==================================================
# ARENA GENERATION
# All decorations are generated once for consistency.
# ==================================================
random.seed(1407)

floor_tiles = []
for _ in range(260):
    floor_tiles.append((
        random.randrange(12, WIDTH - 12),
        random.randrange(12, HEIGHT - 12),
        random.choice([3, 4, 6, 8]),
        random.choice([GROUND_LIGHT, (24, 22, 27), (35, 27, 33)])
    ))

cracks = []
for _ in range(28):
    x = random.randrange(25, WIDTH - 25)
    y = random.randrange(25, HEIGHT - 25)
    cracks.append((x, y, random.randrange(12, 35)))

bloodstains = []
for _ in range(13):
    x = random.randrange(35, WIDTH - 35)
    y = random.randrange(35, HEIGHT - 35)
    bloodstains.append((x, y))

# Solid obstacles are kept away from the starting position.
obstacles = [
    pygame.Rect(115, 95, 72, 32),
    pygame.Rect(270, 90, 38, 70),
    pygame.Rect(430, 105, 95, 27),
    pygame.Rect(670, 100, 65, 42),
    pygame.Rect(760, 225, 45, 76),
    pygame.Rect(110, 340, 55, 75),
    pygame.Rect(320, 435, 90, 32),
    pygame.Rect(515, 465, 42, 66),
    pygame.Rect(690, 405, 90, 35),
    pygame.Rect(420, 290, 42, 40),
]

# Decorations that don't block movement.
barrels = [
    (205, 220), (610, 150), (825, 340),
    (220, 500), (570, 365)
]

fence_segments = [
    ((30, 80), (100, 80)),
    ((205, 80), (340, 80)),
    ((550, 80), (635, 80)),
    ((810, 80), (870, 80)),
    ((845, 100), (845, 205)),
    ((845, 400), (845, 540)),
    ((35, 460), (35, 550)),
]

random.seed()

# ==================================================
# BUTTONS
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

back_button = Button("BACK TO MENU", (450, 520))
resume_button = Button("RESUME", (450, 345))
pause_menu_button = Button("MAIN MENU", (450, 420))
restart_button = Button("PLAY AGAIN", (450, 390))
end_menu_button = Button("MAIN MENU", (450, 460))

# ==================================================
# GAME VARIABLES
# ==================================================
game_state = "menu"
player = None
enemies = []
bullets = []

health = MAX_HEALTH
score = 0
kills = 0
elapsed_time = 0.0
last_shot_time = -FIRE_COOLDOWN
last_damage_time = -DAMAGE_COOLDOWN
last_spawn_second = 0

# ==================================================
# COLLISION HELPERS
# ==================================================
def move_rect(rect, dx, dy):
    # Resolve horizontal and vertical collisions separately.
    rect.x += round(dx)

    for obstacle in obstacles:
        if rect.colliderect(obstacle):
            if dx > 0:
                rect.right = obstacle.left
            elif dx < 0:
                rect.left = obstacle.right

    rect.y += round(dy)

    for obstacle in obstacles:
        if rect.colliderect(obstacle):
            if dy > 0:
                rect.bottom = obstacle.top
            elif dy < 0:
                rect.top = obstacle.bottom

    rect.clamp_ip(screen.get_rect())


def spawn_enemy():
    for _ in range(40):
        side = random.choice(["top", "bottom", "left", "right"])

        if side == "top":
            x, y = random.randint(0, WIDTH - 30), 0
        elif side == "bottom":
            x, y = random.randint(0, WIDTH - 30), HEIGHT - 30
        elif side == "left":
            x, y = 0, random.randint(0, HEIGHT - 30)
        else:
            x, y = WIDTH - 30, random.randint(0, HEIGHT - 30)

        candidate = pygame.Rect(x, y, 30, 30)

        if (
            not any(candidate.colliderect(o) for o in obstacles)
            and (player is None or candidate.centerx < 0
                 or candidate.centerx > WIDTH
                 or math.hypot(
                     candidate.centerx - player.centerx,
                     candidate.centery - player.centery
                 ) > 160)
        ):
            enemies.append({"rect": candidate, "hp": 1})
            return

    # Fallback if every candidate is obstructed.
    enemies.append({
        "rect": pygame.Rect(10, 10, 30, 30),
        "hp": 1
    })


def reset_game():
    global player, enemies, bullets
    global health, score, kills, elapsed_time
    global last_shot_time, last_damage_time
    global last_spawn_second, game_state

    player = pygame.Rect(435, 280, 30, 36)
    enemies = []
    bullets = []

    for _ in range(5):
        spawn_enemy()

    health = MAX_HEALTH
    score = 0
    kills = 0
    elapsed_time = 0.0
    last_shot_time = -FIRE_COOLDOWN
    last_damage_time = -DAMAGE_COOLDOWN
    last_spawn_second = 0
    game_state = "playing"


# ==================================================
# ARENA RENDERING
# ==================================================
def draw_barrel(x, y):
    pygame.draw.rect(screen, (30, 20, 24), (x + 3, y + 4, 28, 30))
    pygame.draw.rect(screen, RUST, (x, y, 28, 30))
    pygame.draw.rect(screen, METAL, (x, y + 5, 28, 4))
    pygame.draw.rect(screen, METAL, (x, y + 21, 28, 4))
    pygame.draw.rect(screen, (45, 32, 36), (x + 6, y + 10, 16, 8))


def draw_obstacle(rect):
    # Shadow
    pygame.draw.rect(
        screen, (8, 7, 10),
        rect.move(5, 5)
    )

    pygame.draw.rect(screen, (42, 38, 43), rect)
    pygame.draw.rect(screen, METAL, rect, 3)

    # Cracks / panels
    pygame.draw.line(
        screen, (20, 18, 22),
        (rect.left + 5, rect.top + 5),
        (rect.right - 6, rect.bottom - 6), 2
    )
    pygame.draw.line(
        screen, (20, 18, 22),
        (rect.right - 6, rect.top + 5),
        (rect.left + 6, rect.bottom - 6), 2
    )


def draw_arena():
    screen.fill(GROUND)

    # Ground texture
    for x, y, size, color in floor_tiles:
        pygame.draw.rect(screen, color, (x, y, size, size))

    # Pavement cracks
    for x, y, length in cracks:
        pygame.draw.line(
            screen, CRACK, (x, y), (x + length, y + 8), 2
        )
        pygame.draw.line(
            screen, CRACK,
            (x + length, y + 8),
            (x + length - 7, y + 17), 2
        )

    # Bloodstains
    for x, y in bloodstains:
        pygame.draw.rect(screen, (65, 10, 23), (x, y, 13, 5))
        pygame.draw.rect(screen, (85, 10, 23), (x + 4, y + 3, 8, 4))
        pygame.draw.rect(screen, (65, 10, 23), (x + 12, y + 1, 4, 3))

    # Warning stripes near selected edges
    for x in range(30, 140, 18):
        pygame.draw.polygon(
            screen, (100, 60, 25),
            [(x, 20), (x + 9, 20), (x + 18, 35), (x + 9, 35)]
        )

    # Broken fence
    for start, end in fence_segments:
        pygame.draw.line(screen, (8, 7, 10), start, end, 7)
        pygame.draw.line(screen, (72, 55, 61), start, end, 3)

    # Debris
    for x, y in [(240, 270), (375, 185), (550, 250),
                 (730, 360), (365, 510), (100, 225)]:
        pygame.draw.rect(screen, (12, 10, 14), (x + 3, y + 3, 22, 12))
        pygame.draw.rect(screen, (60, 51, 57), (x, y, 22, 12))
        pygame.draw.rect(screen, (36, 29, 35), (x + 4, y + 3, 12, 4))

    # Solid obstacles and barrels
    for obstacle in obstacles:
        draw_obstacle(obstacle)

    for x, y in barrels:
        draw_barrel(x, y)

    # Arena border
    pygame.draw.rect(
        screen, (42, 11, 23), (5, 5, WIDTH - 10, HEIGHT - 10), 5
    )
    pygame.draw.rect(
        screen, (94, 16, 34), (10, 10, WIDTH - 20, HEIGHT - 20), 1
    )

    # Darken corners for a horror vignette
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

    for i in range(70):
        alpha = min(2, i // 25 + 1)
        color = (0, 0, 0, alpha)
        pygame.draw.rect(
            overlay, color,
            (i, i, WIDTH - 2 * i, HEIGHT - 2 * i), 1
        )

    screen.blit(overlay, (0, 0))


def draw_menu_background():
    screen.fill(BLACK)

    random.seed(14)

    for _ in range(230):
        x = random.randrange(WIDTH)
        y = random.randrange(HEIGHT)
        size = random.choice([3, 4, 6, 8])
        color = random.choice([
            (20, 13, 20), (30, 13, 21), (39, 13, 22)
        ])
        pygame.draw.rect(screen, color, (x, y, size, size))

    for x in range(560, 890, 35):
        pygame.draw.rect(screen, (55, 32, 39), (x, 65, 5, 240))

    for y in (95, 175, 255):
        pygame.draw.rect(screen, (55, 32, 39), (550, y, 340, 4))

    for x, y in [(690, 300), (800, 350), (630, 410), (745, 510)]:
        screen.blit(zombie_sprite, (x, y))

    draw_barrel(810, 450)

    random.seed()


# ==================================================
# GAME UI
# ==================================================
def draw_text(text, font, color, x, y, centered=False):
    image = font.render(text, True, color)

    if centered:
        screen.blit(image, image.get_rect(center=(x, y)))
    else:
        screen.blit(image, (x, y))


def draw_health_bar():
    x, y = 20, 55
    width, height = 200, 18

    pygame.draw.rect(screen, DARK, (x, y, width, height))
    current = int(width * max(0, health) / MAX_HEALTH)
    color = GREEN if health > 30 else BRIGHT_RED

    pygame.draw.rect(screen, color, (x, y, current, height))
    pygame.draw.rect(screen, WHITE, (x, y, width, height), 2)

    draw_text(
        f"HEALTH: {max(0, health)}",
        ui_font, WHITE, x, y - 27
    )


def draw_game():
    draw_arena()

    # Player
    image = pygame.transform.scale(player_sprite, (36, 48))
    screen.blit(image, image.get_rect(center=player.center))

    # Zombies
    for enemy in enemies:
        image = pygame.transform.scale(zombie_sprite, (36, 42))
        screen.blit(image, image.get_rect(center=enemy["rect"].center))

    # Bullets
    for bullet in bullets:
        pygame.draw.rect(screen, YELLOW, bullet["rect"])
        pygame.draw.rect(
            screen, ORANGE, bullet["rect"].inflate(4, 4), 1
        )

    draw_health_bar()

    remaining = max(0, SURVIVAL_TIME - int(elapsed_time))

    draw_text(f"TIME: {remaining}s", ui_font, YELLOW, WIDTH - 135, 20)
    draw_text(f"SCORE: {score}", ui_font, WHITE, WIDTH - 170, 55)
    draw_text(f"KILLS: {kills}", ui_font, WHITE, WIDTH - 170, 85)

    draw_text(
        "WASD: MOVE | MOUSE: SHOOT | ESC: PAUSE",
        small_font, WHITE, WIDTH // 2, HEIGHT - 25, centered=True
    )


# ==================================================
# COMBAT
# ==================================================
def move_player(dt):
    keys = pygame.key.get_pressed()
    dx = dy = 0

    if keys[pygame.K_w] or keys[pygame.K_UP]:
        dy -= 1
    if keys[pygame.K_s] or keys[pygame.K_DOWN]:
        dy += 1
    if keys[pygame.K_a] or keys[pygame.K_LEFT]:
        dx -= 1
    if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
        dx += 1

    if dx and dy:
        dx *= 0.7071
        dy *= 0.7071

    move_rect(player, dx * PLAYER_SPEED * dt, dy * PLAYER_SPEED * dt)


def move_enemies(dt):
    for enemy in enemies:
        rect = enemy["rect"]

        dx = player.centerx - rect.centerx
        dy = player.centery - rect.centery
        distance = max(1, math.hypot(dx, dy))

        move_rect(
            rect,
            dx / distance * ENEMY_SPEED * dt,
            dy / distance * ENEMY_SPEED * dt
        )


def shoot():
    global last_shot_time

    if elapsed_time - last_shot_time < FIRE_COOLDOWN:
        return

    mx, my = pygame.mouse.get_pos()
    dx = mx - player.centerx
    dy = my - player.centery
    distance = math.hypot(dx, dy)

    if distance == 0:
        return

    bullets.append({
        "x": float(player.centerx),
        "y": float(player.centery),
        "vx": dx / distance * BULLET_SPEED,
        "vy": dy / distance * BULLET_SPEED,
        "rect": pygame.Rect(player.centerx, player.centery, 8, 8),
    })

    last_shot_time = elapsed_time


def update_bullets(dt):
    global score, kills

    for bullet in bullets[:]:
        bullet["x"] += bullet["vx"] * dt
        bullet["y"] += bullet["vy"] * dt

        bullet["rect"].center = (
            round(bullet["x"]), round(bullet["y"])
        )

        if not screen.get_rect().colliderect(bullet["rect"]):
            bullets.remove(bullet)
            continue

        # Bullets stop at solid obstacles.
        if any(bullet["rect"].colliderect(o) for o in obstacles):
            bullets.remove(bullet)
            continue

        hit = None

        for enemy in enemies:
            if bullet["rect"].colliderect(enemy["rect"]):
                hit = enemy
                break

        if hit is not None:
            enemies.remove(hit)
            bullets.remove(bullet)
            kills += 1
            score += 100


# ==================================================
# MENUS
# ==================================================
def draw_menu():
    draw_menu_background()

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

    draw_text("MOVE: WASD / ARROWS", small_font, GRAY, 65, 555)
    draw_text(
        "SHOOT: LEFT MOUSE | PAUSE: ESC / P",
        small_font, GRAY, 65, 575
    )


def draw_how_to_play():
    draw_menu_background()

    pygame.draw.rect(screen, (10, 7, 12), (65, 45, 770, 490))
    pygame.draw.rect(screen, RED, (65, 45, 770, 490), 3)

    draw_text(
        "HOW TO PLAY", heading_font, RED,
        WIDTH // 2, 95, centered=True
    )

    instructions = [
        ("OBJECTIVE", YELLOW),
        ("Survive for 30 seconds without losing all your health.", WHITE),
        ("", WHITE),
        ("CONTROLS", YELLOW),
        ("WASD / ARROW KEYS - Move", WHITE),
        ("LEFT MOUSE BUTTON - Shoot toward the cursor", WHITE),
        ("ESC / P - Pause or resume", WHITE),
        ("R - Restart after winning or losing", WHITE),
        ("", WHITE),
        ("SCORING", YELLOW),
        ("Each defeated zombie gives you 100 points.", WHITE),
        ("Use obstacles for cover, but don't get cornered!", WHITE),
    ]

    y = 145
    for text, color in instructions:
        draw_text(text, ui_font, color, WIDTH // 2, y, centered=True)
        y += 27

    back_button.draw()


def draw_overlay():
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 215))
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
        heading, color = "YOU SURVIVED!", GREEN
    else:
        heading, color = "YOU DIED", BRIGHT_RED

    draw_text(heading, heading_font, color, WIDTH // 2, 215, centered=True)
    draw_text(
        f"FINAL SCORE: {score}",
        ui_font, WHITE, WIDTH // 2, 270, centered=True
    )
    draw_text(
        f"ZOMBIES DEFEATED: {kills}",
        ui_font, WHITE, WIDTH // 2, 305, centered=True
    )
    draw_text(
        f"SURVIVAL TIME: {int(elapsed_time)} seconds",
        ui_font, WHITE, WIDTH // 2, 340, centered=True
    )

    restart_button.draw()
    end_menu_button.draw()


# ==================================================
# MAIN LOOP
# ==================================================
running = True

while running:
    dt = min(clock.tick(FPS) / 1000.0, 0.05)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
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

        if (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and game_state == "playing"
        ):
            shoot()

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

    if game_state == "playing":
        elapsed_time += dt

        move_player(dt)
        move_enemies(dt)
        update_bullets(dt)

        if elapsed_time - last_damage_time >= DAMAGE_COOLDOWN:
            for enemy in enemies:
                if player.colliderect(enemy["rect"]):
                    health -= 10
                    last_damage_time = elapsed_time
                    break

        elapsed_seconds = int(elapsed_time)

        if (
            elapsed_seconds > 0
            and elapsed_seconds % 5 == 0
            and elapsed_seconds != last_spawn_second
            and len(enemies) < 15
        ):
            spawn_enemy()
            last_spawn_second = elapsed_seconds

        if health <= 0:
            game_state = "lost"
        elif elapsed_time >= SURVIVAL_TIME:
            game_state = "won"

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
