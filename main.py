
import pygame
import random
import math
import sys
from pathlib import Path

pygame.init()

# ==================================================
# WINDOW AND SETTINGS
# ==================================================
WIDTH, HEIGHT = 900, 600
FPS = 60

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("DEADLAST")
clock = pygame.time.Clock()

MAX_HEALTH = 100
PLAYER_SPEED = 230
DAMAGE_COOLDOWN = 0.6
WAVE_GOAL = 10
WAVE_BREAK = 3.0

# ==================================================
# HIGH SCORE SYSTEM
# The file is automatically created beside main.py.
# ==================================================
BASE_DIR = Path(__file__).resolve().parent
HIGHSCORE_FILE = BASE_DIR / "highscore.txt"


def load_high_score():
    try:
        if HIGHSCORE_FILE.exists():
            return max(0, int(HIGHSCORE_FILE.read_text().strip() or "0"))
    except (ValueError, OSError):
        print("Could not read high score. Starting at 0.")

    return 0


def save_high_score(value):
    try:
        HIGHSCORE_FILE.write_text(str(value))
    except OSError as error:
        print(f"Could not save high score: {error}")


high_score = load_high_score()
record_beaten = False

# ==================================================
# AUDIO SYSTEM
# Existing audio files remain in assets/music/
# ==================================================
ASSET_DIR = BASE_DIR / "assets"
MUSIC_DIR = ASSET_DIR / "music"

if pygame.mixer.get_init() is None:
    try:
        pygame.mixer.init()
    except pygame.error as error:
        print(f"Audio initialization failed: {error}")

audio_available = pygame.mixer.get_init() is not None
sounds = {}
current_music = None
audio_state = None


def audio_path(name):
    return MUSIC_DIR / f"{name}.mp3"


def load_sound(name, volume=0.7):
    if not audio_available:
        return None

    path = audio_path(name)

    try:
        sound = pygame.mixer.Sound(str(path))
        sound.set_volume(volume)
        sounds[name] = sound
        print(f"Loaded audio: {path}")
        return sound
    except (pygame.error, OSError) as error:
        print(f"Could not load {path}: {error}")
        return None


MUSIC_VOLUMES = {
    "menu_music": 0.35,
    "gameplay_music": 0.28,
}


def play_music(name):
    global current_music

    if not audio_available:
        return

    if current_music == name and pygame.mixer.music.get_busy():
        return

    try:
        pygame.mixer.music.load(str(audio_path(name)))
        pygame.mixer.music.set_volume(MUSIC_VOLUMES.get(name, 0.3))
        pygame.mixer.music.play(-1)
        current_music = name
        print(f"Playing music: {audio_path(name)}")
    except (pygame.error, OSError) as error:
        current_music = None
        print(f"Could not play {audio_path(name)}: {error}")


def stop_music():
    global current_music

    if audio_available:
        pygame.mixer.music.stop()

    current_music = None


def play_sound(name):
    if audio_available and name in sounds:
        try:
            sounds[name].play()
        except pygame.error:
            pass


load_sound("gunshot", 0.55)
load_sound("player_hurt", 0.8)
load_sound("ui_click", 0.55)
load_sound("victory", 0.75)
load_sound("zombie_death", 0.7)
load_sound("game_over", 0.8)

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
GRAY = (130, 120, 130)
GREEN = (75, 220, 110)
YELLOW = (255, 205, 85)
ORANGE = (255, 110, 30)
METAL = (65, 61, 68)
RUST = (105, 48, 39)
CYAN = (90, 210, 240)
PURPLE = (180, 100, 255)

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
        (len(pattern[0]), len(pattern)),
        pygame.SRCALPHA
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
# ==================================================
random.seed(1407)

floor_tiles = [
    (
        random.randrange(12, WIDTH - 12),
        random.randrange(12, HEIGHT - 12),
        random.choice([3, 4, 6, 8]),
        random.choice([
            GROUND_LIGHT,
            (24, 22, 27),
            (35, 27, 33),
        ]),
    )
    for _ in range(260)
]

cracks = [
    (
        random.randrange(25, WIDTH - 25),
        random.randrange(25, HEIGHT - 25),
        random.randrange(12, 35),
    )
    for _ in range(28)
]

bloodstains = [
    (
        random.randrange(35, WIDTH - 35),
        random.randrange(35, HEIGHT - 35),
    )
    for _ in range(13)
]

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

barrels = [
    (205, 220),
    (610, 150),
    (825, 340),
    (220, 500),
    (570, 365),
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
# WEAPONS
# ==================================================
WEAPONS = {
    "pistol": {
        "label": "PISTOL",
        "damage": 1,
        "cooldown": 0.28,
        "bullet_speed": 520,
        "magazine": None,
        "unlock_wave": 1,
        "color": YELLOW,
    },
    "rifle": {
        "label": "ASSAULT RIFLE",
        "damage": 1,
        "cooldown": 0.105,
        "bullet_speed": 680,
        "magazine": 30,
        "unlock_wave": 2,
        "color": CYAN,
    },
    "shotgun": {
        "label": "SHOTGUN",
        "damage": 1,
        "cooldown": 0.72,
        "bullet_speed": 470,
        "magazine": 8,
        "unlock_wave": 3,
        "color": ORANGE,
    },
}

# ==================================================
# GAME VARIABLES
# ==================================================
game_state = "menu"

player = None
enemies = []
bullets = []
powerups = []

health = MAX_HEALTH
score = 0
kills = 0

wave = 1
elapsed_time = 0.0
wave_banner_time = 0.0
wave_break_timer = 0.0
waiting_for_next_wave = False

last_shot_time = -10.0
last_damage_time = -10.0
rapid_fire_timer = 0.0

current_weapon = "pistol"
ammo = {"rifle": 90, "shotgun": 24}

# ==================================================
# AUDIO STATE
# ==================================================
def sync_audio_state():
    global audio_state

    if game_state == audio_state:
        return

    previous_state = audio_state
    audio_state = game_state

    if game_state in ("menu", "howto"):
        if current_music != "menu_music":
            play_music("menu_music")

    elif game_state == "playing":
        if previous_state == "paused" and current_music == "gameplay_music":
            if audio_available:
                pygame.mixer.music.unpause()
        else:
            play_music("gameplay_music")

    elif game_state == "paused":
        if audio_available and current_music is not None:
            pygame.mixer.music.pause()

    elif game_state in ("won", "lost"):
        stop_music()
        play_sound("victory" if game_state == "won" else "game_over")

# ==================================================
# COLLISION HELPERS
# ==================================================
def move_rect(rect, dx, dy):
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


def spawn_enemy(boss=False):
    """Spawn an enemy at the arena edge, away from the player."""
    for _ in range(80):
        side = random.choice(["top", "bottom", "left", "right"])

        if side == "top":
            x, y = random.randint(0, WIDTH - 35), 0
        elif side == "bottom":
            x, y = random.randint(0, WIDTH - 35), HEIGHT - 35
        elif side == "left":
            x, y = 0, random.randint(0, HEIGHT - 35)
        else:
            x, y = WIDTH - 35, random.randint(0, HEIGHT - 35)

        size = 46 if boss else 30
        candidate = pygame.Rect(x, y, size, size)

        too_close = (
            player is not None
            and math.hypot(
                candidate.centerx - player.centerx,
                candidate.centery - player.centery,
            ) < 170
        )

        if (
            not too_close
            and not any(candidate.colliderect(o) for o in obstacles)
        ):
            enemy_hp = 1 + (wave - 1) // 3
            enemy_speed = min(65 + (wave - 1) * 5, 125)

            if boss:
                enemy_hp = 10 + wave
                enemy_speed = min(48 + wave * 2, 75)

            enemies.append({
                "rect": candidate,
                "hp": enemy_hp,
                "max_hp": enemy_hp,
                "speed": enemy_speed,
                "boss": boss,
            })
            return

    candidate = pygame.Rect(20, 20, 46 if boss else 30, 46 if boss else 30)
    candidate.center = (WIDTH // 2, 35)

    enemy_hp = 10 + wave if boss else 1 + (wave - 1) // 3

    enemies.append({
        "rect": candidate,
        "hp": enemy_hp,
        "max_hp": enemy_hp,
        "speed": 55 if boss else min(65 + (wave - 1) * 5, 125),
        "boss": boss,
    })


def start_wave(number):
    global wave, wave_banner_time, waiting_for_next_wave
    global wave_break_timer, current_weapon

    wave = number
    wave_banner_time = 2.5
    waiting_for_next_wave = False
    wave_break_timer = 0.0

    if wave >= 2:
        current_weapon = "rifle"
    if wave >= 3:
        current_weapon = "shotgun"

    enemy_count = min(4 + wave * 2, 24)

    for _ in range(enemy_count):
        spawn_enemy()

    if wave % 5 == 0:
        spawn_enemy(boss=True)


def reset_game():
    global player, enemies, bullets, powerups
    global health, score, kills, elapsed_time
    global last_shot_time, last_damage_time, rapid_fire_timer
    global ammo, current_weapon, wave, game_state
    global waiting_for_next_wave, wave_break_timer, wave_banner_time
    global record_beaten

    player = pygame.Rect(435, 280, 30, 36)
    enemies = []
    bullets = []
    powerups = []

    health = MAX_HEALTH
    score = 0
    kills = 0
    elapsed_time = 0.0

    last_shot_time = -10.0
    last_damage_time = -10.0
    rapid_fire_timer = 0.0

    ammo = {"rifle": 90, "shotgun": 24}
    current_weapon = "pistol"

    wave = 1
    waiting_for_next_wave = False
    wave_break_timer = 0.0
    wave_banner_time = 0.0

    record_beaten = False
    game_state = "playing"
    start_wave(1)

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
    pygame.draw.rect(screen, (8, 7, 10), rect.move(5, 5))
    pygame.draw.rect(screen, (42, 38, 43), rect)
    pygame.draw.rect(screen, METAL, rect, 3)

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

    for x, y, size, color in floor_tiles:
        pygame.draw.rect(screen, color, (x, y, size, size))

    for x, y, length in cracks:
        pygame.draw.line(
            screen, CRACK, (x, y), (x + length, y + 8), 2
        )
        pygame.draw.line(
            screen, CRACK,
            (x + length, y + 8),
            (x + length - 7, y + 17), 2
        )

    for x, y in bloodstains:
        pygame.draw.rect(screen, (65, 10, 23), (x, y, 13, 5))
        pygame.draw.rect(screen, (85, 10, 23), (x + 4, y + 3, 8, 4))
        pygame.draw.rect(screen, (65, 10, 23), (x + 12, y + 1, 4, 3))

    for x in range(30, 140, 18):
        pygame.draw.polygon(
            screen, (100, 60, 25),
            [(x, 20), (x + 9, 20), (x + 18, 35), (x + 9, 35)]
        )

    for start, end in fence_segments:
        pygame.draw.line(screen, (8, 7, 10), start, end, 7)
        pygame.draw.line(screen, (72, 55, 61), start, end, 3)

    for x, y in [
        (240, 270), (375, 185), (550, 250),
        (730, 360), (365, 510), (100, 225)
    ]:
        pygame.draw.rect(screen, (12, 10, 14), (x + 3, y + 3, 22, 12))
        pygame.draw.rect(screen, (60, 51, 57), (x, y, 22, 12))
        pygame.draw.rect(screen, (36, 29, 35), (x + 4, y + 3, 12, 4))

    for obstacle in obstacles:
        draw_obstacle(obstacle)

    for x, y in barrels:
        draw_barrel(x, y)

    pygame.draw.rect(
        screen, (42, 11, 23), (5, 5, WIDTH - 10, HEIGHT - 10), 5
    )
    pygame.draw.rect(
        screen, (94, 16, 34), (10, 10, WIDTH - 20, HEIGHT - 20), 1
    )

    for i in range(0, 90, 10):
        pygame.draw.rect(
            screen, (15, 5, 12),
            (i, i, WIDTH - i * 2, HEIGHT - i * 2), 2
        )


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
# TEXT AND HUD
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

    draw_text(f"HEALTH: {max(0, health)}", ui_font, WHITE, x, y - 27)


def draw_enemy(enemy):
    rect = enemy["rect"]
    size = (52, 56) if enemy["boss"] else (36, 42)
    image = pygame.transform.scale(zombie_sprite, size)

    if enemy["boss"]:
        pygame.draw.rect(screen, BRIGHT_RED, rect.inflate(8, 8), 3)

    screen.blit(image, image.get_rect(center=rect.center))

    if enemy["max_hp"] > 1:
        bar_width = rect.width + 8
        bar_rect = pygame.Rect(
            rect.centerx - bar_width // 2,
            rect.top - 10,
            bar_width,
            5,
        )
        pygame.draw.rect(screen, DARK, bar_rect)

        fill_width = int(
            bar_width * max(0, enemy["hp"]) / enemy["max_hp"]
        )
        pygame.draw.rect(
            screen, BRIGHT_RED,
            (bar_rect.x, bar_rect.y, fill_width, bar_rect.height)
        )


def draw_powerups():
    for pickup in powerups:
        rect = pickup["rect"]
        kind = pickup["type"]

        color, symbol = {
            "health": (GREEN, "+"),
            "ammo": (YELLOW, "A"),
            "rapid": (PURPLE, "!"),
        }[kind]

        pygame.draw.rect(screen, (10, 8, 12), rect.inflate(6, 6))
        pygame.draw.rect(screen, color, rect)
        pygame.draw.rect(screen, WHITE, rect, 2)

        label = button_font.render(symbol, True, BLACK)
        screen.blit(label, label.get_rect(center=rect.center))


def draw_weapon_hud():
    weapon = WEAPONS[current_weapon]
    y = 120

    draw_text(f"WEAPON: {weapon['label']}", ui_font, CYAN, 20, y)

    if weapon["magazine"] is None:
        ammo_text = "AMMO: UNLIMITED"
    else:
        ammo_text = f"AMMO: {ammo[current_weapon]}"

    draw_text(ammo_text, small_font, WHITE, 20, y + 27)

    if wave >= 3:
        controls = "1 PISTOL  2 RIFLE  3 SHOTGUN"
    elif wave >= 2:
        controls = "1 PISTOL  2 RIFLE  3 SHOTGUN (LOCKED)"
    else:
        controls = "1 PISTOL  2 RIFLE (W2)  3 SHOTGUN (W3)"

    draw_text(controls, small_font, GRAY, 20, y + 52)

    if rapid_fire_timer > 0:
        draw_text(
            f"RAPID FIRE: {rapid_fire_timer:.1f}s",
            small_font, PURPLE, 20, y + 76
        )


def draw_game():
    draw_arena()

    player_image = pygame.transform.scale(player_sprite, (36, 48))
    screen.blit(player_image, player_image.get_rect(center=player.center))

    for enemy in enemies:
        draw_enemy(enemy)

    for bullet in bullets:
        color = bullet["color"]
        pygame.draw.rect(screen, color, bullet["rect"])
        pygame.draw.rect(screen, WHITE, bullet["rect"].inflate(3, 3), 1)

    draw_powerups()
    draw_health_bar()
    draw_weapon_hud()

    draw_text(f"WAVE: {wave}/{WAVE_GOAL}", ui_font, YELLOW, WIDTH - 180, 20)
    draw_text(f"SCORE: {score}", ui_font, WHITE, WIDTH - 180, 55)
    draw_text(f"KILLS: {kills}", ui_font, WHITE, WIDTH - 180, 85)

    # NEW: Persistent high score in the gameplay HUD.
    draw_text(
        f"BEST: {high_score}",
        small_font, YELLOW, WIDTH - 180, 115
    )

    if wave % 5 == 0 and any(enemy["boss"] for enemy in enemies):
        draw_text(
            "BOSS WAVE!",
            button_font, BRIGHT_RED, WIDTH // 2, 28, centered=True
        )

    if wave_banner_time > 0:
        draw_text(
            f"WAVE {wave}",
            heading_font, BRIGHT_RED,
            WIDTH // 2, HEIGHT // 2 - 50, centered=True
        )

        subtitle = (
            "A BOSS IS APPROACHING..."
            if wave % 5 == 0
            else "THE HORDE IS COMING..."
        )

        draw_text(
            subtitle, ui_font, WHITE,
            WIDTH // 2, HEIGHT // 2, centered=True
        )

    if waiting_for_next_wave:
        draw_text(
            f"NEXT WAVE IN {math.ceil(wave_break_timer)}",
            heading_font, YELLOW,
            WIDTH // 2, HEIGHT // 2, centered=True
        )

    draw_text(
        "WASD: MOVE | MOUSE: SHOOT | ESC/P: PAUSE",
        small_font, WHITE, WIDTH // 2, HEIGHT - 20, centered=True
    )

# ==================================================
# PLAYER MOVEMENT
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
            dx / distance * enemy["speed"] * dt,
            dy / distance * enemy["speed"] * dt,
        )

# ==================================================
# WEAPON SYSTEM
# ==================================================
def switch_weapon(number):
    global current_weapon

    choices = {
        1: "pistol",
        2: "rifle",
        3: "shotgun",
    }

    choice = choices.get(number)

    if choice is None:
        return

    if wave < WEAPONS[choice]["unlock_wave"]:
        return

    current_weapon = choice
    play_sound("ui_click")


def shoot():
    global last_shot_time

    weapon = WEAPONS[current_weapon]
    cooldown = weapon["cooldown"]

    if rapid_fire_timer > 0:
        cooldown = min(cooldown, 0.075)

    if elapsed_time - last_shot_time < cooldown:
        return

    if current_weapon != "pistol" and ammo[current_weapon] <= 0:
        return

    mx, my = pygame.mouse.get_pos()
    dx = mx - player.centerx
    dy = my - player.centery
    distance = math.hypot(dx, dy)

    if distance == 0:
        return

    angle = math.atan2(dy, dx)

    if current_weapon == "shotgun":
        spread_angles = [-0.24, -0.12, 0, 0.12, 0.24]
    else:
        spread_angles = [0]

    for spread in spread_angles:
        shot_angle = angle + spread
        vx = math.cos(shot_angle) * weapon["bullet_speed"]
        vy = math.sin(shot_angle) * weapon["bullet_speed"]

        bullets.append({
            "x": float(player.centerx),
            "y": float(player.centery),
            "vx": vx,
            "vy": vy,
            "damage": weapon["damage"],
            "color": weapon["color"],
            "rect": pygame.Rect(player.centerx, player.centery, 8, 8),
        })

    if current_weapon != "pistol":
        ammo[current_weapon] -= 1

    last_shot_time = elapsed_time
    play_sound("gunshot")


def drop_powerup(position, guaranteed=False):
    if not guaranteed and random.random() > 0.22:
        return

    kind = random.choice(["health", "ammo", "rapid"])
    rect = pygame.Rect(0, 0, 22, 22)
    rect.center = position

    powerups.append({
        "type": kind,
        "rect": rect,
        "age": 0.0,
    })


def kill_enemy(enemy):
    global score, kills, high_score, record_beaten

    if enemy not in enemies:
        return

    enemies.remove(enemy)
    kills += 1

    if enemy["boss"]:
        score += 500
        drop_powerup(enemy["rect"].center, guaranteed=True)
    else:
        score += 100
        drop_powerup(enemy["rect"].center)

    # NEW: Save the score immediately whenever a new record is reached.
    if score > high_score:
        high_score = score
        record_beaten = True
        save_high_score(high_score)

    play_sound("zombie_death")


def update_bullets(dt):
    for bullet in bullets[:]:
        bullet["x"] += bullet["vx"] * dt
        bullet["y"] += bullet["vy"] * dt

        bullet["rect"].center = (
            round(bullet["x"]),
            round(bullet["y"]),
        )

        if not screen.get_rect().colliderect(bullet["rect"]):
            bullets.remove(bullet)
            continue

        if any(bullet["rect"].colliderect(o) for o in obstacles):
            bullets.remove(bullet)
            continue

        hit = None

        for enemy in enemies:
            if bullet["rect"].colliderect(enemy["rect"]):
                hit = enemy
                break

        if hit is not None:
            hit["hp"] -= bullet["damage"]
            bullets.remove(bullet)

            if hit["hp"] <= 0:
                kill_enemy(hit)


def update_powerups(dt):
    global health, rapid_fire_timer

    rapid_fire_timer = max(0.0, rapid_fire_timer - dt)

    for pickup in powerups[:]:
        pickup["age"] += dt

        if pickup["age"] >= 15:
            powerups.remove(pickup)
            continue

        if not player.colliderect(pickup["rect"]):
            continue

        kind = pickup["type"]

        if kind == "health":
            health = min(MAX_HEALTH, health + 35)

        elif kind == "ammo":
            ammo["rifle"] = min(180, ammo["rifle"] + 45)
            ammo["shotgun"] = min(64, ammo["shotgun"] + 12)

        elif kind == "rapid":
            rapid_fire_timer = 7.0

        powerups.remove(pickup)
        play_sound("ui_click")


def update_player_damage():
    global health, last_damage_time

    if elapsed_time - last_damage_time < DAMAGE_COOLDOWN:
        return

    for enemy in enemies:
        if player.colliderect(enemy["rect"]):
            damage = 20 if enemy["boss"] else 10
            health -= damage
            last_damage_time = elapsed_time
            play_sound("player_hurt")
            break

# ==================================================
# MENUS
# ==================================================
def draw_menu():
    draw_menu_background()

    pygame.draw.rect(screen, (10, 7, 12), (28, 75, 400, 150))
    pygame.draw.rect(screen, DARK_RED, (28, 75, 400, 150), 2)

    draw_text("DEADLAST", title_font, RED, 225, 125, centered=True)
    draw_text(
        "SURVIVE THE HORDE",
        small_font, WHITE, 225, 190, centered=True
    )

    # NEW: Display the saved high score on the main menu.
    draw_text(
        f"HIGH SCORE: {high_score}",
        ui_font, YELLOW, 225, 255, centered=True
    )

    start_button.draw()
    howto_button.draw()
    quit_button.draw()

    draw_text(
        "10 WAVES. THREE WEAPONS. NO ESCAPE.",
        small_font, GRAY, 65, 555
    )


def draw_how_to_play():
    draw_menu_background()

    pygame.draw.rect(screen, (10, 7, 12), (65, 35, 770, 520))
    pygame.draw.rect(screen, RED, (65, 35, 770, 520), 3)

    draw_text(
        "HOW TO PLAY", heading_font, RED,
        WIDTH // 2, 75, centered=True
    )

    instructions = [
        ("OBJECTIVE", YELLOW),
        ("Survive all 10 waves. Every fifth wave has a boss.", WHITE),
        ("", WHITE),
        ("MOVEMENT AND COMBAT", YELLOW),
        ("WASD / ARROWS - Move", WHITE),
        ("LEFT MOUSE BUTTON - Shoot", WHITE),
        ("ESC / P - Pause or resume", WHITE),
        ("1 - Pistol | 2 - Rifle | 3 - Shotgun", WHITE),
        ("R - Return to menu after the game ends", WHITE),
        ("", WHITE),
        ("WEAPONS AND POWER-UPS", YELLOW),
        ("Rifle unlocks at wave 2. Shotgun unlocks at wave 3.", WHITE),
        ("Green + = health | Yellow A = ammunition", WHITE),
        ("Purple ! = rapid fire for 7 seconds", WHITE),
        ("", WHITE),
        ("Every defeated zombie gives 100 points.", WHITE),
        ("Bosses give 500 points and a guaranteed power-up.", WHITE),
        ("", WHITE),
        (f"CURRENT HIGH SCORE: {high_score}", YELLOW),
    ]

    y = 100

    for text, color in instructions:
        draw_text(text, small_font, color, WIDTH // 2, y, centered=True)
        y += 22

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
        "Take a breath. The horde can wait.",
        small_font, WHITE, WIDTH // 2, 290, centered=True
    )

    resume_button.draw()
    pause_menu_button.draw()


def draw_end_screen():
    draw_game()
    draw_overlay()

    if game_state == "won":
        heading, color = "YOU SURVIVED!", GREEN
        subtitle = "You cleared every wave."
    else:
        heading, color = "YOU DIED", BRIGHT_RED
        subtitle = f"You reached wave {wave} of {WAVE_GOAL}."

    draw_text(heading, heading_font, color, WIDTH // 2, 180, centered=True)
    draw_text(subtitle, ui_font, WHITE, WIDTH // 2, 222, centered=True)

    draw_text(
        f"FINAL SCORE: {score}",
        ui_font, WHITE, WIDTH // 2, 260, centered=True
    )
    draw_text(
        f"HIGH SCORE: {high_score}",
        ui_font, YELLOW, WIDTH // 2, 292, centered=True
    )
    draw_text(
        f"ZOMBIES DEFEATED: {kills}",
        ui_font, WHITE, WIDTH // 2, 324, centered=True
    )
    draw_text(
        f"WAVES CLEARED: {wave if game_state == 'won' else wave - 1}",
        ui_font, YELLOW, WIDTH // 2, 356, centered=True
    )

    # NEW: Celebrate setting a record during this run.
    if record_beaten:
        draw_text(
            "NEW HIGH SCORE!",
            button_font, GREEN, WIDTH // 2, 385, centered=True
        )

    restart_button.draw()
    end_menu_button.draw()


def clicked_button_for_state(event):
    if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
        return False

    if game_state == "menu":
        buttons = [start_button, howto_button, quit_button]
    elif game_state == "howto":
        buttons = [back_button]
    elif game_state == "paused":
        buttons = [resume_button, pause_menu_button]
    elif game_state in ("won", "lost"):
        buttons = [restart_button, end_menu_button]
    else:
        buttons = []

    return any(button.rect.collidepoint(event.pos) for button in buttons)

# ==================================================
# MAIN LOOP
# ==================================================
running = True

while running:
    dt = min(clock.tick(FPS) / 1000.0, 0.05)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if clicked_button_for_state(event):
            play_sound("ui_click")

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

            if game_state == "playing":
                if event.key == pygame.K_1:
                    switch_weapon(1)
                elif event.key == pygame.K_2:
                    switch_weapon(2)
                elif event.key == pygame.K_3:
                    switch_weapon(3)

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
        wave_banner_time = max(0.0, wave_banner_time - dt)

        move_player(dt)
        move_enemies(dt)
        update_bullets(dt)
        update_powerups(dt)
        update_player_damage()

        if waiting_for_next_wave:
            wave_break_timer -= dt

            if wave_break_timer <= 0:
                start_wave(wave + 1)

        elif not enemies:
            if wave >= WAVE_GOAL:
                game_state = "won"
            else:
                waiting_for_next_wave = True
                wave_break_timer = WAVE_BREAK

        if health <= 0:
            health = 0
            game_state = "lost"

        if pygame.mouse.get_pressed()[0]:
            shoot()

    sync_audio_state()

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
