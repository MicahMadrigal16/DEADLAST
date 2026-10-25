import pygame
import random
import math
import sys
import json
from pathlib import Path

pygame.init()

# ============================================================
# DEADLAST - 1920 x 1080 SURVIVAL GAME
# ============================================================
WIDTH, HEIGHT = 1920, 1080
WINDOW_WIDTH, WINDOW_HEIGHT = 1280, 720
FPS = 60
TITLE = "DEADLAST"

# Internal canvas is always 1920 x 1080; the window may be resized or fullscreen.
screen = pygame.Surface((WIDTH, HEIGHT))
pygame.display.set_caption(TITLE)
clock = pygame.time.Clock()

# Detect desktop resolution for fullscreen launch
_display_info = pygame.display.Info()
DESKTOP_W, DESKTOP_H = _display_info.current_w, _display_info.current_h

# Fullscreen state (toggled in Options / by pressing F11)
fullscreen = True

# Create window: fullscreen at desktop resolution, or windowed
# (will be adjusted after load_settings() reads saved preference below)
window = pygame.display.set_mode((DESKTOP_W, DESKTOP_H), pygame.FULLSCREEN)

# Paths for normal Python and packaged EXE versions
RESOURCE_DIR = Path(__file__).resolve().parent

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = RESOURCE_DIR

ASSET_DIR = BASE_DIR / "assets"
MUSIC_DIR = ASSET_DIR / "music"
HIGH_SCORE_FILE = BASE_DIR / "highscore.txt"
SETTINGS_FILE = BASE_DIR / "settings.txt"

MAX_HEALTH = 100
PLAYER_SPEED = 330
DAMAGE_COOLDOWN = 0.6
WAVE_GOAL = 10
WAVE_BREAK = 3.0

# Colors
BLACK = (8, 10, 12)
WHITE = (230, 232, 220)
RED = (190, 38, 38)
DARK_RED = (88, 20, 24)
GREEN = (83, 170, 88)
YELLOW = (235, 190, 75)
GRAY = (100, 105, 103)
DARK_GRAY = (35, 40, 40)
PANEL = (15, 19, 19)
BLOOD = (75, 18, 25)

# Fonts
title_font = pygame.font.Font(None, 150)
heading_font = pygame.font.Font(None, 90)
button_font = pygame.font.Font(None, 54)
ui_font = pygame.font.Font(None, 42)
small_font = pygame.font.Font(None, 30)
tiny_font = pygame.font.Font(None, 24)

# ============================================================
# AUDIO
# ============================================================
mixer_ready = False
sounds = {}
music_enabled = True
sound_enabled = True
music_volume = 0.7
sfx_volume = 0.8

try:
    if not pygame.mixer.get_init():
        pygame.mixer.init()
    mixer_ready = True
except pygame.error:
    pass

SOUND_FILES = {
    "gunshot": "Gunshot.mp3",
    "hurt": "player_hurt.mp3",
    "click": "ui_click.mp3",
    "victory": "victory.mp3",
    "zombie_death": "zombie_death.mp3",
    "game_over": "game_over.mp3",
}

if mixer_ready:
    for key, filename in SOUND_FILES.items():
        try:
            sounds[key] = pygame.mixer.Sound(str(MUSIC_DIR / filename))
            sounds[key].set_volume(sfx_volume)
        except (pygame.error, OSError):
            sounds[key] = None


def load_settings():
    global music_volume, sfx_volume, fullscreen, music_enabled, sound_enabled
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        music_volume = float(data.get("music_volume", 0.7))
        sfx_volume = float(data.get("sfx_volume", 0.8))
        fullscreen = bool(data.get("fullscreen", False))
        music_enabled = bool(data.get("music_enabled", True))
        sound_enabled = bool(data.get("sound_enabled", True))
        # Apply loaded sfx volume to existing sounds
        for s in sounds.values():
            if s:
                s.set_volume(sfx_volume)
    except (OSError, ValueError, json.JSONDecodeError):
        pass


def save_settings():
    data = {
        "music_volume": music_volume,
        "sfx_volume": sfx_volume,
        "fullscreen": fullscreen,
        "music_enabled": music_enabled,
        "sound_enabled": sound_enabled,
    }
    try:
        SETTINGS_FILE.write_text(json.dumps(data), encoding="utf-8")
    except OSError:
        pass


def play_sound(name):
    if sound_enabled and mixer_ready and sounds.get(name):
        try:
            sounds[name].set_volume(sfx_volume)
            sounds[name].play()
        except pygame.error:
            pass


def play_music(filename, loops=-1):
    if not mixer_ready or not music_enabled:
        return
    try:
        pygame.mixer.music.load(str(MUSIC_DIR / filename))
        pygame.mixer.music.set_volume(music_volume)
        pygame.mixer.music.play(loops)
    except (pygame.error, OSError):
        pass


def stop_music():
    if mixer_ready:
        try:
            pygame.mixer.music.stop()
        except pygame.error:
            pass


def toggle_fullscreen():
    global window, fullscreen
    fullscreen = not fullscreen
    try:
        if fullscreen:
            _info = pygame.display.Info()
            window = pygame.display.set_mode(
                (_info.current_w, _info.current_h),
                pygame.FULLSCREEN
            )
        else:
            window = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE)
    except pygame.error:
        # Fall back to previous state if display mode change fails
        fullscreen = not fullscreen
    save_settings()


# Load persisted settings (volumes, fullscreen, audio toggles)
load_settings()

# Adjust window mode if saved fullscreen preference differs from current
if not fullscreen:
    window = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE)


# ============================================================
# ARENA
# ============================================================
TILE_SIZE = 64
floor_tiles = []

for y in range(0, HEIGHT, TILE_SIZE):
    for x in range(0, WIDTH, TILE_SIZE):
        floor_tiles.append((x, y, random.randint(0, 3)))

cracks = []

for _ in range(180):
    cracks.append((
        random.randint(20, WIDTH - 20),
        random.randint(20, HEIGHT - 20),
        random.randint(12, 50),
        random.choice([-1, 1])
    ))

bloodstains = []

for _ in range(65):
    bloodstains.append((
        random.randint(30, WIDTH - 30),
        random.randint(30, HEIGHT - 30),
        random.randint(8, 30)
    ))

obstacles = [
    pygame.Rect(220, 180, 150, 65),
    pygame.Rect(490, 160, 75, 155),
    pygame.Rect(800, 210, 190, 55),
    pygame.Rect(1240, 160, 145, 90),
    pygame.Rect(1530, 290, 90, 165),
    pygame.Rect(250, 660, 105, 150),
    pygame.Rect(610, 800, 190, 65),
    pygame.Rect(980, 830, 85, 145),
    pygame.Rect(1330, 720, 190, 70),
    pygame.Rect(850, 500, 90, 90),
    pygame.Rect(1660, 760, 135, 70),
    pygame.Rect(430, 430, 90, 55),
    pygame.Rect(1120, 400, 150, 65),
    pygame.Rect(700, 580, 70, 130),
    pygame.Rect(1480, 520, 70, 120),
]

barrels = [
    (410, 360), (1110, 240), (1710, 550), (450, 900),
    (1030, 680), (1450, 890), (180, 480), (870, 340),
    (1260, 570), (620, 280), (1600, 180), (1030, 950)
]

fence_segments = []

for x in range(0, WIDTH, 100):
    fence_segments.append((x, 18, 80, 18))
    fence_segments.append((x, HEIGHT - 36, 80, 18))

for y in range(0, HEIGHT, 100):
    fence_segments.append((18, y, 18, 80))
    fence_segments.append((WIDTH - 36, y, 18, 80))


def draw_text(surface, text, font, color, center, shadow=True):
    image = font.render(str(text), True, color)
    rect = image.get_rect(center=(int(center[0]), int(center[1])))

    if shadow:
        shadow_img = font.render(str(text), True, BLACK)
        surface.blit(shadow_img, (rect.x + 4, rect.y + 4))

    surface.blit(image, rect)
    return rect


def draw_text_left(surface, text, font, color, pos, shadow=True):
    image = font.render(str(text), True, color)

    if shadow:
        shadow_img = font.render(str(text), True, BLACK)
        surface.blit(shadow_img, (pos[0] + 3, pos[1] + 3))

    surface.blit(image, pos)
    return image.get_rect(topleft=pos)


def draw_arena(surface):
    surface.fill((27, 32, 30))

    for x, y, variation in floor_tiles:
        shade = 31 + variation * 3
        pygame.draw.rect(
            surface,
            (shade, shade + 5, shade + 1),
            (x, y, TILE_SIZE - 2, TILE_SIZE - 2)
        )

    # Cracked and worn floor
    for x, y, length, direction in cracks:
        pygame.draw.line(
            surface, (19, 24, 23),
            (x, y), (x + length, y + direction * 9), 2
        )
        pygame.draw.line(
            surface, (43, 47, 43),
            (x + 2, y + 2),
            (x + length - 3, y + direction * 7), 1
        )

    # Blood on the ground
    for x, y, radius in bloodstains:
        pygame.draw.ellipse(
            surface, BLOOD,
            (x - radius, y - radius // 2, radius * 2, radius)
        )

    # Scattered debris
    for x, y, _ in floor_tiles[::7]:
        pygame.draw.rect(
            surface, (55, 56, 48),
            (x + 14, y + 21, 10, 5)
        )
        pygame.draw.rect(
            surface, (18, 22, 20),
            (x + 38, y + 45, 7, 7)
        )

    # Fence
    for x, y, w, h in fence_segments:
        pygame.draw.rect(surface, (54, 60, 55), (x, y, w, h))

        if w > h:
            for px in range(x, x + w, 28):
                pygame.draw.line(
                    surface, (91, 94, 81),
                    (px, y), (px, y + h), 3
                )
        else:
            for py in range(y, y + h, 28):
                pygame.draw.line(
                    surface, (91, 94, 81),
                    (x, py), (x + w, py), 3
                )

    # Obstacles / broken crates
    for rect in obstacles:
        pygame.draw.rect(
            surface, (13, 16, 15), rect.move(7, 8),
            border_radius=5
        )
        pygame.draw.rect(
            surface, (74, 67, 52), rect, border_radius=4
        )
        pygame.draw.rect(
            surface, (110, 93, 65), rect, 5, border_radius=4
        )
        pygame.draw.line(
            surface, (42, 42, 35),
            rect.topleft, rect.bottomright, 5
        )
        pygame.draw.line(
            surface, (42, 42, 35),
            rect.topright, rect.bottomleft, 5
        )
        pygame.draw.line(
            surface, (132, 112, 76),
            (rect.left + 10, rect.top + 8),
            (rect.right - 10, rect.top + 8), 3
        )

    # Barrels
    for x, y in barrels:
        pygame.draw.ellipse(
            surface, (13, 15, 14),
            (x - 29, y - 23, 65, 54)
        )
        pygame.draw.rect(
            surface, (94, 49, 35),
            (x - 25, y - 30, 50, 60), border_radius=6
        )
        pygame.draw.rect(
            surface, (139, 77, 48),
            (x - 25, y - 30, 50, 10)
        )
        pygame.draw.rect(
            surface, (44, 48, 42),
            (x - 25, y - 7, 50, 8)
        )
        pygame.draw.rect(
            surface, (44, 48, 42),
            (x - 25, y + 14, 50, 8)
        )
        pygame.draw.line(
            surface, (160, 95, 58),
            (x - 12, y - 23), (x - 12, y + 20), 3
        )

    # Dark border around the arena
    pygame.draw.rect(surface, (10, 13, 12), (0, 0, WIDTH, 18))
    pygame.draw.rect(
        surface, (10, 13, 12), (0, HEIGHT - 18, WIDTH, 18)
    )
    pygame.draw.rect(surface, (10, 13, 12), (0, 0, 18, HEIGHT))
    pygame.draw.rect(
        surface, (10, 13, 12), (WIDTH - 18, 0, 18, HEIGHT)
    )


# ============================================================
# ARENA CACHE (static background drawn once, blitted each frame)
# ============================================================
arena_cache = pygame.Surface((WIDTH, HEIGHT))
draw_arena(arena_cache)


# ============================================================
# BUTTONS / MENUS
# ============================================================
class Button:
    def __init__(self, rect, text):
        self.rect = pygame.Rect(rect)
        self.text = text

    def draw(self, surface, mouse_pos):
        hovered = self.rect.collidepoint(mouse_pos)
        fill = (103, 35, 39) if hovered else (46, 52, 49)
        border = (230, 90, 73) if hovered else (110, 119, 104)

        pygame.draw.rect(
            surface, fill, self.rect, border_radius=8
        )
        pygame.draw.rect(
            surface, border, self.rect, 3, border_radius=8
        )

        draw_text(
            surface, self.text, button_font, WHITE,
            self.rect.center, shadow=False
        )

    def clicked(self, pos):
        return self.rect.collidepoint(pos)


class Slider:
    """Horizontal slider for volume controls."""
    def __init__(self, rect, min_val=0.0, max_val=1.0, value=0.5):
        self.rect = pygame.Rect(rect)
        self.min_val = min_val
        self.max_val = max_val
        self.value = value
        self.dragging = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.dragging = True
                self._set_from_mouse(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._set_from_mouse(event.pos)

    def _set_from_mouse(self, pos):
        rel = max(0, min(1, (pos[0] - self.rect.x) / self.rect.w))
        self.value = self.min_val + rel * (self.max_val - self.min_val)

    def draw(self, surface, mouse_pos, label):
        # Track groove
        groove = pygame.Rect(
            self.rect.x, self.rect.centery - 4, self.rect.w, 8
        )
        pygame.draw.rect(surface, (55, 62, 58), groove, border_radius=4)

        # Fill proportion
        fill_w = int(self.rect.w * (self.value - self.min_val) / (self.max_val - self.min_val))
        fill = pygame.Rect(self.rect.x, self.rect.centery - 4, fill_w, 8)
        pygame.draw.rect(surface, (230, 90, 73), fill, border_radius=4)

        # Thumb
        thumb_x = self.rect.x + fill_w
        thumb = pygame.Rect(thumb_x - 10, self.rect.centery - 12, 20, 24)
        hovered = self.rect.collidepoint(mouse_pos) or self.dragging
        thumb_color = (230, 90, 73) if hovered else (170, 180, 160)
        pygame.draw.rect(surface, thumb_color, thumb, border_radius=6)
        pygame.draw.rect(surface, (90, 100, 90), thumb, 2, border_radius=6)

        # Label + value
        pct = int((self.value - self.min_val) / (self.max_val - self.min_val) * 100)
        draw_text_left(
            surface, f"{label}: {pct}%", ui_font, WHITE,
            (self.rect.x, self.rect.y - 30)
        )


menu_buttons = [
    Button((760, 470, 400, 78), "START GAME"),
    Button((760, 570, 400, 78), "OPTIONS"),
    Button((760, 670, 400, 78), "HOW TO PLAY"),
    Button((760, 770, 400, 78), "CREDITS"),
    Button((760, 870, 400, 78), "HIGH SCORES"),
    Button((760, 970, 400, 78), "QUIT"),
]

howto_back_button = Button((760, 940, 400, 78), "BACK")

options_back_button = Button((760, 900, 400, 78), "BACK")
credits_back_button = Button((760, 900, 400, 78), "BACK")
highscores_back_button = Button((760, 900, 400, 78), "BACK")

pause_buttons = [
    Button((760, 445, 400, 78), "RESUME"),
    Button((760, 545, 400, 78), "MAIN MENU"),
]

end_buttons = [
    Button((760, 660, 400, 78), "PLAY AGAIN"),
    Button((760, 760, 400, 78), "MAIN MENU"),
]


# ============================================================
# GAME OBJECTS
# ============================================================
class Player:
    def __init__(self):
        self.rect = pygame.Rect(945, 520, 42, 52)
        self.health = MAX_HEALTH
        self.last_damage = 0
        self.rapid_until = 0
        self.weapon = "Pistol"
        self.ammo = {
            "Pistol": float("inf"),
            "Rifle": 90,
            "Shotgun": 24
        }
        self.last_shot = 0

    @property
    def center(self):
        return self.rect.center

    def draw(self, surface, mouse_pos):
        x, y = self.rect.center

        # Shadow
        pygame.draw.ellipse(
            surface, (12, 14, 13),
            (x - 31, self.rect.bottom - 5, 65, 22)
        )

        # Boots
        pygame.draw.rect(
            surface, (27, 30, 28),
            (x - 20, y + 12, 15, 25)
        )
        pygame.draw.rect(
            surface, (27, 30, 28),
            (x + 5, y + 12, 15, 25)
        )

        # Body armor
        pygame.draw.rect(
            surface, (61, 83, 68),
            (x - 21, y - 12, 42, 39), border_radius=5
        )
        pygame.draw.rect(
            surface, (113, 126, 87),
            (x - 16, y - 9, 32, 10)
        )

        # Head
        pygame.draw.rect(
            surface, (173, 143, 105),
            (x - 14, y - 32, 28, 25), border_radius=4
        )
        pygame.draw.rect(
            surface, (42, 48, 41),
            (x - 17, y - 35, 34, 10)
        )

        # Eyes
        pygame.draw.rect(
            surface, (20, 24, 22),
            (x - 9, y - 23, 5, 4)
        )
        pygame.draw.rect(
            surface, (20, 24, 22),
            (x + 4, y - 23, 5, 4)
        )

        # Weapon aims at the mouse position
        angle = math.atan2(mouse_pos[1] - y, mouse_pos[0] - x)
        end_x = x + math.cos(angle) * 53
        end_y = y + math.sin(angle) * 53

        pygame.draw.line(
            surface, (20, 23, 22),
            (x, y), (end_x, end_y), 12
        )
        pygame.draw.line(
            surface, (116, 120, 106),
            (x, y), (end_x, end_y), 6
        )


class Enemy:
    def __init__(self, x, y, wave, boss=False):
        self.boss = boss
        size = 76 if boss else 44
        self.rect = pygame.Rect(x, y, size, size)
        self.max_hp = (10 + wave * 2) if boss else wave
        self.hp = self.max_hp
        self.speed = (
            min(105 + (wave - 1) * 9, 190)
            if boss else min(90 + (wave - 1) * 10, 180)
        )
        self.damage = 12 + wave if boss else 8 + wave // 2
        self.attack_time = 0

    def draw(self, surface):
        x, y = self.rect.center

        if self.boss:
            pygame.draw.ellipse(
                surface, (12, 14, 13),
                (x - 49, self.rect.bottom - 4, 100, 28)
            )
            pygame.draw.rect(
                surface, (82, 33, 37),
                (x - 37, y - 28, 74, 66), border_radius=8
            )
            pygame.draw.rect(
                surface, (124, 48, 43),
                (x - 33, y - 43, 66, 37), border_radius=8
            )
            pygame.draw.rect(
                surface, (235, 66, 49),
                (x - 23, y - 31, 12, 9)
            )
            pygame.draw.rect(
                surface, (235, 66, 49),
                (x + 11, y - 31, 12, 9)
            )
            pygame.draw.rect(
                surface, (38, 24, 24),
                (x - 19, y + 5, 38, 10)
            )

        else:
            pygame.draw.ellipse(
                surface, (12, 14, 13),
                (x - 28, self.rect.bottom - 3, 58, 19)
            )
            pygame.draw.rect(
                surface, (63, 88, 58),
                (x - 19, y - 12, 38, 35), border_radius=4
            )
            pygame.draw.rect(
                surface, (100, 115, 65),
                (x - 15, y - 25, 30, 23), border_radius=4
            )
            pygame.draw.rect(
                surface, (228, 64, 48),
                (x - 10, y - 18, 6, 5)
            )
            pygame.draw.rect(
                surface, (228, 64, 48),
                (x + 4, y - 18, 6, 5)
            )
            pygame.draw.rect(
                surface, (30, 25, 23),
                (x - 9, y - 2, 18, 5)
            )

        bar_w = 100 if self.boss else 54
        bar_h = 9 if self.boss else 7
        bar_y = self.rect.top - (25 if self.boss else 15)
        bar_x = x - bar_w // 2
        health_ratio = max(0, self.hp) / self.max_hp
        health_color = (
            GREEN if health_ratio > 0.6
            else YELLOW if health_ratio > 0.3
            else RED
        )

        pygame.draw.rect(
            surface, (18, 12, 13),
            (bar_x - 2, bar_y - 2, bar_w + 4, bar_h + 4)
        )
        pygame.draw.rect(
            surface, (58, 20, 23),
            (bar_x, bar_y, bar_w, bar_h)
        )
        pygame.draw.rect(
            surface, health_color,
            (bar_x, bar_y, int(bar_w * health_ratio), bar_h)
        )


class Bullet:
    def __init__(self, x, y, target, damage=1, speed=1000):
        self.pos = pygame.Vector2(x, y)
        direction = pygame.Vector2(target[0] - x, target[1] - y)

        if direction.length_squared() == 0:
            direction = pygame.Vector2(1, 0)

        self.velocity = direction.normalize() * speed
        self.damage = damage
        self.alive = True

    def update(self, dt):
        self.pos += self.velocity * dt

        if (
            self.pos.x < 0 or self.pos.x > WIDTH
            or self.pos.y < 0 or self.pos.y > HEIGHT
        ):
            self.alive = False

        for obstacle in obstacles:
            if obstacle.collidepoint(int(self.pos.x), int(self.pos.y)):
                self.alive = False
                break

    def draw(self, surface):
        pygame.draw.circle(
            surface, (255, 224, 123),
            (int(self.pos.x), int(self.pos.y)), 5
        )
        pygame.draw.circle(
            surface, (255, 255, 218),
            (int(self.pos.x), int(self.pos.y)), 2
        )


class PowerUp:
    def __init__(self, x, y, kind):
        self.rect = pygame.Rect(x - 20, y - 20, 40, 40)
        self.kind = kind
        self.created = pygame.time.get_ticks()

    def draw(self, surface):
        colors = {
            "health": GREEN,
            "ammo": YELLOW,
            "rapid": (85, 165, 235)
        }
        color = colors[self.kind]

        pygame.draw.rect(
            surface, (15, 17, 15),
            self.rect.move(4, 5), border_radius=6
        )
        pygame.draw.rect(
            surface, color, self.rect, border_radius=6
        )
        pygame.draw.rect(
            surface, WHITE, self.rect, 3, border_radius=6
        )

        symbol = {
            "health": "+",
            "ammo": "A",
            "rapid": "R"
        }[self.kind]

        draw_text(
            surface, symbol, ui_font, BLACK,
            self.rect.center, False
        )


# ============================================================
# GAME STATE
# ============================================================
def load_high_score():
    try:
        return int(HIGH_SCORE_FILE.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return 0


high_score = load_high_score()

state = "menu"
player = None
enemies = []
bullets = []
powerups = []
particles = []
wave = 1
score = 0
kills = 0
enemies_to_spawn = 0
spawn_timer = 0
wave_break_timer = 0
banner_text = ""
banner_until = 0
record_beaten = False
game_over_reason = "GAME OVER"

# Transition / fade state
transition_state = None      # None, "fade_out", "fade_in"
transition_alpha = 0
transition_next_state = None
transition_speed = 450       # alpha per second


def save_high_score():
    global high_score

    if score > high_score:
        high_score = score
        try:
            HIGH_SCORE_FILE.write_text(str(high_score), encoding="utf-8")
        except OSError:
            pass


def point_blocked(x, y, padding=55):
    for obstacle in obstacles:
        if obstacle.inflate(padding, padding).collidepoint(x, y):
            return True
    return False


def spawn_enemy(boss=False):
    for _ in range(100):
        side = random.randint(0, 3)

        if side == 0:
            x, y = random.randint(50, WIDTH - 100), 60
        elif side == 1:
            x, y = random.randint(50, WIDTH - 100), HEIGHT - 120
        elif side == 2:
            x, y = 60, random.randint(50, HEIGHT - 100)
        else:
            x, y = WIDTH - 120, random.randint(50, HEIGHT - 100)

        if player and math.hypot(
            x - player.rect.x, y - player.rect.y
        ) < 320:
            continue

        if point_blocked(x, y, 45):
            continue

        return Enemy(x, y, wave, boss)

    return Enemy(70, 70, wave, boss)


def reset_game():
    global player, enemies, bullets, powerups, particles
    global wave, score, kills, enemies_to_spawn, spawn_timer
    global wave_break_timer, banner_text, banner_until, record_beaten

    player = Player()
    enemies = []
    bullets = []
    powerups = []
    particles = []
    wave = 1
    score = 0
    kills = 0
    enemies_to_spawn = 0
    spawn_timer = 0
    wave_break_timer = 0
    banner_text = "WAVE 1"
    banner_until = pygame.time.get_ticks() + 2200
    record_beaten = False

    begin_wave()


def begin_wave():
    global enemies_to_spawn, spawn_timer, banner_text, banner_until

    enemies_to_spawn = min(5 + wave * 2, 28)
    spawn_timer = 0.4
    banner_text = f"WAVE {wave}"
    banner_until = pygame.time.get_ticks() + 2200

    if wave % 5 == 0:
        enemies.append(spawn_enemy(True))
        banner_text = f"WAVE {wave} - BOSS INCOMING!"


def clamp_player():
    player.rect.left = max(35, player.rect.left)
    player.rect.right = min(WIDTH - 35, player.rect.right)
    player.rect.top = max(40, player.rect.top)
    player.rect.bottom = min(HEIGHT - 35, player.rect.bottom)


def move_player(dx, dy):
    player.rect.x += round(dx)

    for obstacle in obstacles:
        if player.rect.colliderect(obstacle):
            if dx > 0:
                player.rect.right = obstacle.left
            elif dx < 0:
                player.rect.left = obstacle.right

    player.rect.y += round(dy)

    for obstacle in obstacles:
        if player.rect.colliderect(obstacle):
            if dy > 0:
                player.rect.bottom = obstacle.top
            elif dy < 0:
                player.rect.top = obstacle.bottom

    clamp_player()


def fire_weapon(target):
    now = pygame.time.get_ticks() / 1000
    rapid = now < player.rapid_until
    delay = 0.095 if rapid else 0.24

    if player.weapon == "Rifle":
        delay = 0.075 if rapid else 0.13
    elif player.weapon == "Shotgun":
        delay = 0.36 if rapid else 0.65

    if now - player.last_shot < delay:
        return

    if (
        player.weapon != "Pistol"
        and player.ammo[player.weapon] <= 0
    ):
        return

    player.last_shot = now
    play_sound("gunshot")

    if player.weapon == "Shotgun":
        base_angle = math.atan2(
            target[1] - player.rect.centery,
            target[0] - player.rect.centerx
        )

        for offset in (-0.22, -0.11, 0, 0.11, 0.22):
            spread_target = (
                player.rect.centerx
                + math.cos(base_angle + offset) * 1000,
                player.rect.centery
                + math.sin(base_angle + offset) * 1000
            )
            bullets.append(
                Bullet(
                    *player.rect.center,
                    spread_target,
                    damage=2,
                    speed=850
                )
            )

        player.ammo["Shotgun"] -= 1

    else:
        damage = 2 if player.weapon == "Rifle" else 1
        speed = 1250 if player.weapon == "Rifle" else 1000

        bullets.append(
            Bullet(*player.rect.center, target, damage, speed)
        )

        if player.weapon == "Rifle":
            player.ammo["Rifle"] -= 1


def switch_weapon(key):
    global banner_text, banner_until
    new_weapon = player.weapon
    if key == pygame.K_1:
        new_weapon = "Pistol"
    elif key == pygame.K_2 and wave >= 2:
        new_weapon = "Rifle"
    elif key == pygame.K_3 and wave >= 3:
        new_weapon = "Shotgun"

    if new_weapon != player.weapon:
        player.weapon = new_weapon
        banner_text = f"{new_weapon.upper()} EQUIPPED"
        banner_until = pygame.time.get_ticks() + 1800
        play_sound("click")


def damage_player(amount):
    now = pygame.time.get_ticks() / 1000

    if now - player.last_damage < DAMAGE_COOLDOWN:
        return

    player.last_damage = now
    player.health = max(0, player.health - amount)
    play_sound("hurt")


def end_game(won):
    global state, game_over_reason, record_beaten

    state = "win" if won else "gameover"
    game_over_reason = "YOU SURVIVED" if won else "YOU DIED"

    if won:
        play_sound("victory")
    else:
        play_sound("game_over")

    old_high = high_score
    save_high_score()
    record_beaten = score > old_high
    stop_music()


def kill_enemy(enemy):
    global score, kills

    if enemy not in enemies:
        return

    enemies.remove(enemy)
    kills += 1
    score += 500 if enemy.boss else 100
    play_sound("zombie_death")

    if enemy.boss or random.random() < 0.22:
        kind = (
            "health" if random.random() < 0.34
            else random.choice(["ammo", "rapid"])
        )
        powerups.append(
            PowerUp(enemy.rect.centerx, enemy.rect.centery, kind)
        )


# ============================================================
# HUD AND OVERLAYS
# HUD LAYOUT PRESERVED
# ============================================================
def draw_hud(surface):
    # Helper to draw a semi-transparent panel
    def draw_panel(x, y, w, h):
        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        panel.fill((10, 13, 12, 170))
        surface.blit(panel, (x, y))
        pygame.draw.rect(
            surface, (83, 91, 78), (x, y, w, h), 3, border_radius=8
        )

    # Top left: health
    draw_panel(35, 30, 430, 112)

    draw_text_left(
        surface, "HEALTH", ui_font, WHITE, (55, 42)
    )

    pygame.draw.rect(
        surface, (43, 20, 23),
        (55, 92, 380, 24), border_radius=5
    )

    health_width = int(376 * player.health / MAX_HEALTH)

    if health_width > 0:
        health_color = (
            GREEN if player.health > 50
            else YELLOW if player.health > 25
            else RED
        )
        pygame.draw.rect(
            surface, health_color,
            (57, 94, health_width, 20), border_radius=4
        )

    draw_text_left(
        surface, f"{player.health}/{MAX_HEALTH}",
        small_font, WHITE, (330, 48)
    )

    # Top center: wave
    draw_panel(WIDTH // 2 - 160, 28, 320, 90)

    draw_text(
        surface, f"WAVE {wave}/{WAVE_GOAL}",
        ui_font, WHITE, (WIDTH // 2, 58)
    )
    draw_text(
        surface, f"SCORE {score}",
        small_font, YELLOW, (WIDTH // 2, 91)
    )

    # Top right: kills and high score
    draw_panel(WIDTH - 350, 30, 315, 112)

    draw_text_left(
        surface, f"KILLS: {kills}",
        small_font, WHITE, (WIDTH - 325, 48)
    )
    draw_text_left(
        surface, f"RECORD: {high_score}",
        small_font, YELLOW, (WIDTH - 325, 88)
    )

    # Bottom left: weapon and ammunition
    weapon_ammo = (
        "UNLIMITED" if player.weapon == "Pistol"
        else player.ammo[player.weapon]
    )

    draw_panel(35, HEIGHT - 125, 400, 85)

    draw_text_left(
        surface, f"WEAPON: {player.weapon.upper()}",
        small_font, WHITE, (55, HEIGHT - 112)
    )
    draw_text_left(
        surface, f"AMMO: {weapon_ammo}",
        small_font, YELLOW, (55, HEIGHT - 76)
    )

    # Bottom center: controls
    draw_text(
        surface,
        "WASD / ARROWS: MOVE    MOUSE: AIM & SHOOT    "
        "1 / 2 / 3: WEAPON    ESC / P: PAUSE",
        small_font, (208, 211, 194),
        (WIDTH // 2, HEIGHT - 45), False
    )

    # Buff timer (rapid fire) above controls
    now = pygame.time.get_ticks() / 1000
    if hasattr(player, "rapid_until") and player.rapid_until > now:
        secs_left = int(player.rapid_until - now) + 1
        draw_text(
            surface, f"RAPID FIRE: {secs_left}s",
            small_font, GREEN, (WIDTH // 2, HEIGHT - 80), False
        )


def draw_banner(surface):
    if pygame.time.get_ticks() < banner_until and banner_text:
        box = pygame.Rect(
            WIDTH // 2 - 450, HEIGHT // 2 - 70, 900, 140
        )

        overlay = pygame.Surface(
            (box.width, box.height), pygame.SRCALPHA
        )
        overlay.fill((8, 10, 10, 220))
        surface.blit(overlay, box.topleft)

        pygame.draw.rect(
            surface, (180, 54, 47),
            box, 4, border_radius=8
        )

        draw_text(
            surface, banner_text, heading_font,
            WHITE, box.center
        )


def draw_wave_countdown(surface):
    if (
        wave_break_timer <= 0
        or wave >= WAVE_GOAL
        or enemies_to_spawn > 0
        or enemies
    ):
        return

    countdown = max(1, math.ceil(WAVE_BREAK - wave_break_timer))
    box = pygame.Rect(WIDTH // 2 - 300, HEIGHT // 2 - 145, 600, 290)
    overlay = pygame.Surface((box.width, box.height), pygame.SRCALPHA)
    overlay.fill((8, 10, 10, 220))
    surface.blit(overlay, box.topleft)
    pygame.draw.rect(surface, (119, 52, 48), box, 4, border_radius=8)

    draw_text(
        surface, "NEXT WAVE IN",
        ui_font, WHITE, (WIDTH // 2, box.top + 65)
    )
    draw_text(
        surface, str(countdown),
        title_font, YELLOW, (WIDTH // 2, box.centery + 25)
    )


def draw_panel(surface, heading, lines, buttons, mouse_pos):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 190))
    surface.blit(overlay, (0, 0))

    panel = pygame.Rect(560, 170, 800, 760)

    pygame.draw.rect(
        surface, (14, 18, 17), panel, border_radius=14
    )
    pygame.draw.rect(
        surface, (119, 52, 48), panel, 4, border_radius=14
    )

    draw_text(
        surface, heading, title_font,
        WHITE, (WIDTH // 2, 270)
    )

    for i, line in enumerate(lines):
        draw_text(
            surface, line, ui_font, (205, 207, 192),
            (WIDTH // 2, 380 + i * 58)
        )

    for button in buttons:
        button.draw(surface, mouse_pos)


def draw_menu(surface, mouse_pos):
    surface.blit(arena_cache, (0, 0))

    shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 155))
    surface.blit(shade, (0, 0))

    draw_text(
        surface, "DEADLAST", title_font,
        (190, 53, 48), (WIDTH // 2, 235)
    )
    draw_text(
        surface, "SURVIVE THE OUTBREAK", heading_font,
        WHITE, (WIDTH // 2, 340)
    )
    draw_text(
        surface, "TEN WAVES. NO RESCUE IS COMING.",
        ui_font, (174, 180, 162), (WIDTH // 2, 405)
    )

    for button in menu_buttons:
        button.draw(surface, mouse_pos)

    draw_text(
        surface, f"HIGH SCORE: {high_score}",
        ui_font, YELLOW, (WIDTH // 2, 815)
    )
    draw_text(
        surface, "A PIXEL-ART ZOMBIE SURVIVAL GAME",
        small_font, (143, 151, 137),
        (WIDTH // 2, 870), False
    )


def draw_howto(surface, mouse_pos):
    surface.blit(arena_cache, (0, 0))

    draw_panel(surface, "HOW TO PLAY", [
        "WASD or ARROW KEYS - Move around the arena",
        "MOUSE - Aim your weapon and shoot",
        "1 - Pistol (unlimited ammunition)",
        "2 - Rifle (unlocks at Wave 2)",
        "3 - Shotgun (unlocks at Wave 3)",
        "Collect green health, yellow ammo and blue rapid-fire drops",
        "Every fifth wave has a boss. Survive all ten waves!",
        "Press ESC or P to pause during gameplay",
    ], [howto_back_button], mouse_pos)


def draw_pause(surface, mouse_pos):
    draw_panel(surface, "PAUSED", [
        "Take a breath. The dead are still out there.",
        "Press ESC or P to return to the fight.",
    ], pause_buttons, mouse_pos)


def draw_end_screen(surface, mouse_pos, won):
    surface.blit(arena_cache, (0, 0))

    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 185))
    surface.blit(overlay, (0, 0))

    heading = "YOU SURVIVED" if won else "YOU DIED"
    color = GREEN if won else RED

    draw_text(
        surface, heading, title_font,
        color, (WIDTH // 2, 280)
    )
    draw_text(
        surface, f"FINAL SCORE: {score}",
        heading_font, WHITE, (WIDTH // 2, 405)
    )
    draw_text(
        surface, f"ZOMBIES KILLED: {kills}",
        ui_font, WHITE, (WIDTH // 2, 475)
    )
    draw_text(
        surface, f"HIGH SCORE: {high_score}",
        ui_font, YELLOW, (WIDTH // 2, 530)
    )

    if record_beaten:
        draw_text(
            surface, "NEW HIGH SCORE!",
            heading_font, YELLOW, (WIDTH // 2, 590)
        )

    for button in end_buttons:
        button.draw(surface, mouse_pos)


def draw_options(surface, mouse_pos, music_slider, sfx_slider):
    surface.blit(arena_cache, (0, 0))

    shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 170))
    surface.blit(shade, (0, 0))

    draw_text(
        surface, "OPTIONS", title_font,
        WHITE, (WIDTH // 2, 200)
    )

    # Music volume slider
    music_slider.draw(surface, mouse_pos, "MUSIC")
    # SFX volume slider
    sfx_slider.draw(surface, mouse_pos, "SFX")

    # Fullscreen toggle text
    fs_text = "FULLSCREEN: ON" if fullscreen else "FULLSCREEN: OFF"
    draw_text(
        surface, fs_text, ui_font,
        YELLOW, (WIDTH // 2, 640)
    )
    draw_text(
        surface, "(press F11 to toggle)", small_font,
        (174, 180, 162), (WIDTH // 2, 680)
    )

    options_back_button.draw(surface, mouse_pos)


def draw_credits(surface, mouse_pos):
    surface.blit(arena_cache, (0, 0))

    shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 170))
    surface.blit(shade, (0, 0))

    draw_text(
        surface, "CREDITS", title_font,
        WHITE, (WIDTH // 2, 200)
    )

    credits_lines = [
        "DEADLAST",
        "A zombie survival game",
        "",
        "Programming & Design: You",
        "Engine: Pygame",
        "",
        "Music:",
        "  menu_music.mp3",
        "  gameplay_music.mp3",
        "",
        "Sound Effects:",
        "  Gunshot, player_hurt, ui_click,",
        "  victory, zombie_death, game_over",
        "",
        "Thank you for playing!",
    ]
    for i, line in enumerate(credits_lines):
        draw_text(
            surface, line, ui_font,
            (205, 207, 192), (WIDTH // 2, 320 + i * 42)
        )

    credits_back_button.draw(surface, mouse_pos)


def draw_highscores(surface, mouse_pos):
    surface.blit(arena_cache, (0, 0))

    shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 170))
    surface.blit(shade, (0, 0))

    draw_text(
        surface, "HIGH SCORES", title_font,
        WHITE, (WIDTH // 2, 200)
    )

    # Display the current high score
    try:
        saved = HIGH_SCORE_FILE.read_text(encoding="utf-8").strip()
        score_text = saved if saved else "0"
    except OSError:
        score_text = "0"

    draw_text(
        surface, f"BEST SCORE: {score_text}",
        ui_font, YELLOW, (WIDTH // 2, 340)
    )

    draw_text(
        surface, "Survive the outbreak and beat your record!",
        small_font, (174, 180, 162), (WIDTH // 2, 390)
    )

    highscores_back_button.draw(surface, mouse_pos)


def draw_transition(surface):
    """Draw a fading overlay during state transitions."""
    if transition_state is None:
        return
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, transition_alpha))
    surface.blit(overlay, (0, 0))


# ============================================================
# MAIN LOOP
# ============================================================
reset_game()
state = "menu"
play_music("menu_music.mp3")

# Volume sliders (created once, updated in options screen)
music_slider = Slider((WIDTH // 2 - 200, 420, 400, 24), 0.0, 1.0, music_volume)
sfx_slider = Slider((WIDTH // 2 - 200, 520, 400, 24), 0.0, 1.0, sfx_volume)

running = True

while running:
    dt = min(clock.tick(FPS) / 1000.0, 0.04)

    # Get the current window size.
    window_w, window_h = window.get_size()

    # Convert mouse coordinates to native 1920 x 1080 coordinates.
    mouse_pos = pygame.mouse.get_pos()
    scale_x = WIDTH / max(1, window_w)
    scale_y = HEIGHT / max(1, window_h)

    world_mouse = (
        int(mouse_pos[0] * scale_x),
        int(mouse_pos[1] * scale_y)
    )

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.VIDEORESIZE:
            # Keep the game windowed and resizable (ignore in fullscreen).
            if not fullscreen:
                window = pygame.display.set_mode(
                    event.size,
                    pygame.RESIZABLE
                )

        elif event.type == pygame.KEYDOWN:
            # F11 toggles fullscreen from any state
            if event.key == pygame.K_F11:
                toggle_fullscreen()

            if state == "playing":
                if event.key in (pygame.K_ESCAPE, pygame.K_p):
                    state = "paused"
                    play_sound("click")

                elif event.key in (
                    pygame.K_1, pygame.K_2, pygame.K_3
                ):
                    switch_weapon(event.key)

            elif state == "paused":
                if event.key in (pygame.K_ESCAPE, pygame.K_p):
                    state = "playing"
                    play_sound("click")

            elif state == "howto" and event.key == pygame.K_ESCAPE:
                state = "menu"

            elif state in ("options", "credits", "highscores") and event.key == pygame.K_ESCAPE:
                state = "menu"
                play_sound("click")

            elif state in ("win", "gameover") and event.key == pygame.K_r:
                reset_game()
                state = "playing"
                play_music("gameplay_music.mp3")

        elif (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
        ):
            # Recalculate using the latest window size.
            window_w, window_h = window.get_size()
            scale_x = WIDTH / max(1, window_w)
            scale_y = HEIGHT / max(1, window_h)

            pos = (
                int(event.pos[0] * scale_x),
                int(event.pos[1] * scale_y)
            )

            if state == "menu":
                for i, button in enumerate(menu_buttons):
                    if button.clicked(pos):
                        play_sound("click")

                        if i == 0:  # START GAME
                            # Begin fade transition -> playing
                            transition_state = "fade_out"
                            transition_next_state = "playing"
                            transition_alpha = 0

                        elif i == 1:  # OPTIONS
                            state = "options"

                        elif i == 2:  # HOW TO PLAY
                            state = "howto"

                        elif i == 3:  # CREDITS
                            state = "credits"

                        elif i == 4:  # HIGH SCORES
                            state = "highscores"

                        else:  # QUIT
                            running = False

            elif state == "options":
                # Let sliders handle their own events
                music_slider.handle_event(event)
                sfx_slider.handle_event(event)
                # Apply volume changes immediately
                music_volume = music_slider.value
                sfx_volume = sfx_slider.value
                for s in sounds.values():
                    if s:
                        s.set_volume(sfx_volume)
                if mixer_ready:
                    pygame.mixer.music.set_volume(music_volume)
                save_settings()

                if options_back_button.clicked(pos):
                    play_sound("click")
                    state = "menu"

            elif state == "credits":
                if credits_back_button.clicked(pos):
                    play_sound("click")
                    state = "menu"

            elif state == "highscores":
                if highscores_back_button.clicked(pos):
                    play_sound("click")
                    state = "menu"

            elif state == "howto":
                if howto_back_button.clicked(pos):
                    play_sound("click")
                    state = "menu"

            elif state == "paused":
                if pause_buttons[0].clicked(pos):
                    play_sound("click")
                    state = "playing"

                elif pause_buttons[1].clicked(pos):
                    play_sound("click")
                    state = "menu"
                    play_music("menu_music.mp3")

            elif state in ("win", "gameover"):
                if end_buttons[0].clicked(pos):
                    play_sound("click")
                    reset_game()
                    state = "playing"

                elif end_buttons[1].clicked(pos):
                    play_sound("click")
                    state = "menu"
                    play_music("menu_music.mp3")

        elif event.type == pygame.MOUSEMOTION:
            if state == "options":
                music_slider.handle_event(event)
                sfx_slider.handle_event(event)
                music_volume = music_slider.value
                sfx_volume = sfx_slider.value
                for s in sounds.values():
                    if s:
                        s.set_volume(sfx_volume)
                if mixer_ready:
                    pygame.mixer.music.set_volume(music_volume)
                save_settings()

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if state == "options":
                music_slider.handle_event(event)
                sfx_slider.handle_event(event)

    # ========================================================
    # GAMEPLAY UPDATE
    # ========================================================
    if state == "playing":
        keys = pygame.key.get_pressed()
        direction = pygame.Vector2(0, 0)

        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            direction.x -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            direction.x += 1
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            direction.y -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            direction.y += 1

        if direction.length_squared() > 0:
            direction = direction.normalize()
            move_player(
                direction.x * PLAYER_SPEED * dt,
                direction.y * PLAYER_SPEED * dt
            )

        if pygame.mouse.get_pressed()[0]:
            # Use the current mouse location in native coordinates.
            mouse_x, mouse_y = pygame.mouse.get_pos()
            window_w, window_h = window.get_size()

            world_mouse = (
                int(mouse_x * WIDTH / max(1, window_w)),
                int(mouse_y * HEIGHT / max(1, window_h))
            )

            fire_weapon(world_mouse)

        # Spawn zombies
        spawn_timer -= dt

        if enemies_to_spawn > 0 and spawn_timer <= 0:
            enemies.append(spawn_enemy(False))
            enemies_to_spawn -= 1
            spawn_timer = max(0.20, 0.90 - wave * 0.06)

        # Update bullets and check collisions
        for bullet in bullets[:]:
            bullet.update(dt)

            if not bullet.alive:
                bullets.remove(bullet)
                continue

            hit_enemy = None

            bullet_rect = pygame.Rect(
                int(bullet.pos.x - 5),
                int(bullet.pos.y - 5),
                10, 10
            )

            for enemy in enemies:
                if bullet_rect.colliderect(enemy.rect):
                    enemy.hp -= bullet.damage
                    bullet.alive = False
                    hit_enemy = enemy
                    break

            if not bullet.alive and bullet in bullets:
                bullets.remove(bullet)

            if hit_enemy and hit_enemy.hp <= 0:
                kill_enemy(hit_enemy)

        # Zombies chase and attack the player
        for enemy in enemies[:]:
            to_player = pygame.Vector2(
                player.rect.centerx - enemy.rect.centerx,
                player.rect.centery - enemy.rect.centery
            )

            if to_player.length_squared() > 0:
                move = to_player.normalize() * enemy.speed * dt
                old_x, old_y = enemy.rect.x, enemy.rect.y

                enemy.rect.x += round(move.x)

                for obstacle in obstacles:
                    if enemy.rect.colliderect(obstacle):
                        enemy.rect.x = old_x
                        break

                enemy.rect.y += round(move.y)

                for obstacle in obstacles:
                    if enemy.rect.colliderect(obstacle):
                        enemy.rect.y = old_y
                        break

            if enemy.rect.colliderect(player.rect):
                damage_player(enemy.damage)

        # Power-ups
        for powerup in powerups[:]:
            if player.rect.colliderect(powerup.rect):
                if powerup.kind == "health":
                    player.health = min(
                        MAX_HEALTH, player.health + 35
                    )

                elif powerup.kind == "ammo":
                    player.ammo["Rifle"] += 45
                    player.ammo["Shotgun"] += 12

                elif powerup.kind == "rapid":
                    player.rapid_until = (
                        pygame.time.get_ticks() / 1000 + 7
                    )

                powerups.remove(powerup)
                play_sound("click")

        # Wave completion and break
        if enemies_to_spawn == 0 and len(enemies) == 0:
            wave_break_timer += dt

            if wave_break_timer >= WAVE_BREAK:
                wave_break_timer = 0

                if wave >= WAVE_GOAL:
                    end_game(True)
                else:
                    wave += 1
                    begin_wave()
        else:
            wave_break_timer = 0

        if player.health <= 0:
            end_game(False)

        # Save a new high score during gameplay
        if score > high_score:
            high_score = score

            try:
                HIGH_SCORE_FILE.write_text(
                    str(high_score), encoding="utf-8"
                )
            except OSError:
                pass

    # ========================================================
    # TRANSITION / FADE UPDATE
    # ========================================================
    if transition_state == "fade_out":
        transition_alpha += transition_speed * dt
        if transition_alpha >= 255:
            transition_alpha = 255
            # Switch to the target state, then fade in
            state = transition_next_state
            if transition_next_state == "playing":
                reset_game()
                play_music("gameplay_music.mp3")
            transition_state = "fade_in"

    elif transition_state == "fade_in":
        transition_alpha -= transition_speed * dt
        if transition_alpha <= 0:
            transition_alpha = 0
            transition_state = None
            transition_next_state = None

    # ========================================================
    # RENDER TO THE NATIVE 1920 x 1080 CANVAS
    # ========================================================
    screen.blit(arena_cache, (0, 0))

    if state == "menu":
        draw_menu(screen, world_mouse)

    elif state == "howto":
        draw_howto(screen, world_mouse)

    elif state == "options":
        draw_options(screen, world_mouse, music_slider, sfx_slider)

    elif state == "credits":
        draw_credits(screen, world_mouse)

    elif state == "highscores":
        draw_highscores(screen, world_mouse)

    elif state in ("playing", "paused"):
        for powerup in powerups:
            powerup.draw(screen)

        for bullet in bullets:
            bullet.draw(screen)

        for enemy in enemies:
            enemy.draw(screen)

        if player:
            player.draw(screen, world_mouse)

        draw_hud(screen)
        draw_banner(screen)

        if state == "playing":
            draw_wave_countdown(screen)

        if state == "paused":
            draw_pause(screen, world_mouse)

    elif state == "win":
        draw_end_screen(screen, world_mouse, True)

    elif state == "gameover":
        draw_end_screen(screen, world_mouse, False)

    # Draw fade transition overlay on top of everything
    draw_transition(screen)

    # ========================================================
    # SCALE THE COMPLETE FRAME TO THE WINDOW
    # ========================================================
    # HUD layout is unchanged; the entire canvas scales together.
    frame = pygame.transform.smoothscale(
        screen,
        window.get_size()
    )

    window.blit(frame, (0, 0))
    pygame.display.flip()

pygame.quit()
sys.exit()