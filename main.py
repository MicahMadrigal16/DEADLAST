from array import array
import heapq
import os
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


def window_to_canvas(position, window_size):
    return (
        int(position[0] * WIDTH / max(1, window_size[0])),
        int(position[1] * HEIGHT / max(1, window_size[1]))
    )


# Internal canvas is always 1920 x 1080; the window may be resized or borderless fullscreen.
screen = pygame.Surface((WIDTH, HEIGHT))
damage_overlay_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
pygame.display.set_caption(TITLE)
clock = pygame.time.Clock()

# Fullscreen state (toggled in Options / by pressing F11)
fullscreen = True

# A zero-sized borderless mode uses the current desktop resolution without
# switching the display mode.
# (will be adjusted after load_settings() reads saved preference below)
window = pygame.display.set_mode((0, 0), pygame.NOFRAME)

# Paths for normal Python and packaged EXE versions
RESOURCE_DIR = Path(__file__).resolve().parent

if getattr(sys, "frozen", False):
    LEGACY_DATA_DIR = Path(sys.executable).resolve().parent
    if sys.platform == "win32":
        data_root = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        BASE_DIR = (
            Path(data_root) / TITLE if data_root
            else Path.home() / "AppData" / "Local" / TITLE
        )
    else:
        data_root = os.environ.get("XDG_DATA_HOME")
        BASE_DIR = (
            Path(data_root) / TITLE.lower() if data_root
            else Path.home() / ".local" / "share" / TITLE.lower()
        )
else:
    BASE_DIR = RESOURCE_DIR
    LEGACY_DATA_DIR = BASE_DIR

ASSET_DIR = RESOURCE_DIR / "assets"
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

# ============================================================
# GAME ICON
# ============================================================
ICON_FILE = ASSET_DIR / "images" / "icon.png"
if ICON_FILE.exists():
    try:
        _icon = pygame.image.load(str(ICON_FILE))
        pygame.display.set_icon(_icon)
    except pygame.error:
        _icon = None
else:
    _icon = None

if _icon is None:
    _icon = pygame.Surface((32, 32), pygame.SRCALPHA)
    _icon.fill((0, 0, 0, 0))  # transparent fallback
    pygame.draw.circle(_icon, RED, (10, 16), 10)
    pygame.draw.circle(_icon, (8, 10, 12), (10, 16), 6)
    pygame.draw.rect(_icon, RED, (10, 6, 16, 20))
    pygame.draw.rect(_icon, RED, (20, 14, 6, 6))
    pygame.display.set_icon(_icon)

# Fonts
title_font = pygame.font.Font(None, 150)
heading_font = pygame.font.Font(None, 90)
button_font = pygame.font.Font(None, 54)
ui_font = pygame.font.Font(None, 42)
small_font = pygame.font.Font(None, 30)
tiny_font = pygame.font.Font(None, 24)
section_font = pygame.font.Font(None, 44)
body_font = pygame.font.Font(None, 34)
small_ui_font = pygame.font.Font(None, 26)
tiny_ui_font = pygame.font.Font(None, 22)

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

    mixer_settings = pygame.mixer.get_init()
    if mixer_settings and mixer_settings[1] == -16:
        sample_rate, _, channels = mixer_settings
        sample_count = int(sample_rate * 0.16)
        samples = array("h")
        for index in range(sample_count):
            envelope = 1 - index / sample_count
            sample = int(
                12000 * envelope
                * math.sin(2 * math.pi * 880 * index / sample_rate)
            )
            samples.extend([sample] * channels)
        sounds["countdown"] = pygame.mixer.Sound(buffer=samples.tobytes())
        sounds["countdown"].set_volume(sfx_volume)


def load_settings():
    global music_volume, sfx_volume, fullscreen, music_enabled, sound_enabled
    try:
        settings_path = SETTINGS_FILE
        legacy_path = LEGACY_DATA_DIR / "settings.txt"
        if not settings_path.exists() and legacy_path != settings_path and legacy_path.exists():
            settings_path = legacy_path
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return

    if not isinstance(data, dict):
        return

    def volume_setting(name, default):
        try:
            value = float(data.get(name, default))
        except (TypeError, ValueError, OverflowError):
            return default
        if not math.isfinite(value):
            return default
        return max(0.0, min(1.0, value))

    music_volume = volume_setting("music_volume", 0.7)
    sfx_volume = volume_setting("sfx_volume", 0.8)
    fullscreen_value = data.get("fullscreen", False)
    music_enabled_value = data.get("music_enabled", True)
    sound_enabled_value = data.get("sound_enabled", True)
    fullscreen = fullscreen_value if isinstance(fullscreen_value, bool) else False
    music_enabled = music_enabled_value if isinstance(music_enabled_value, bool) else True
    sound_enabled = sound_enabled_value if isinstance(sound_enabled_value, bool) else True

    # Apply loaded sfx volume to existing sounds.
    for sound in sounds.values():
        if sound:
            sound.set_volume(sfx_volume)


def save_settings():
    data = {
        "music_volume": music_volume,
        "sfx_volume": sfx_volume,
        "fullscreen": fullscreen,
        "music_enabled": music_enabled,
        "sound_enabled": sound_enabled,
    }
    try:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(json.dumps(data, allow_nan=False), encoding="utf-8")
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
            window = pygame.display.set_mode((0, 0), pygame.NOFRAME)
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
# ARENA  (layout regenerated each wave)
# ============================================================
TILE_SIZE = 64

# Fixed border fencing (never changes)
fence_segments = []
for _fx in range(0, WIDTH, 100):
    fence_segments.append((_fx, 18, 80, 18))
    fence_segments.append((_fx, HEIGHT - 36, 80, 18))
for _fy in range(0, HEIGHT, 100):
    fence_segments.append((18, _fy, 18, 80))
    fence_segments.append((WIDTH - 36, _fy, 18, 80))

# --- 10 hand-crafted obstacle + barrel layouts (one per wave) ---
_WAVE_LAYOUTS = [
    # Wave 1 - scattered crates, original feel
    dict(
        obs=[(220,180,150,65),(490,160,75,155),(800,210,190,55),
             (1240,160,145,90),(1530,290,90,165),(250,660,105,150),
             (610,800,190,65),(980,830,85,145),(1330,720,190,70),
             (850,500,90,90),(1660,760,135,70),(430,430,90,55),
             (1120,400,150,65),(700,580,70,130),(1480,520,70,120)],
        bar=[(410,360),(1110,240),(1710,550),(450,900),
             (1030,680),(1450,890),(180,480),(870,340),
             (1260,570),(620,280),(1600,180),(1030,950)],
        tint=(27,32,30),
    ),
    # Wave 2 - centre cross formation, bloodier
    dict(
        obs=[(880,80,160,60),(880,940,160,60),(80,500,60,160),
             (1780,500,60,160),(860,480,200,120),(300,200,120,80),
             (1500,200,120,80),(300,750,120,80),(1500,750,120,80),
             (600,350,80,80),(1240,350,80,80),(600,680,80,80),
             (1240,680,80,80),(750,200,100,60),(1070,200,100,60)],
        bar=[(200,300),(1720,300),(200,780),(1720,780),
             (960,300),(960,780),(450,540),(1470,540),
             (700,130),(1220,130),(700,950),(1220,950)],
        tint=(32,22,22),
    ),
    # Wave 3 - corridor maze, tight lanes
    dict(
        obs=[(150,100,300,55),(700,100,300,55),(1300,100,300,55),
             (150,280,55,200),(450,280,55,200),(750,280,55,200),
             (1050,280,55,200),(1350,280,55,200),(1650,280,55,200),
             (150,600,300,55),(700,600,300,55),(1300,600,300,55),
             (150,780,55,200),(750,780,55,200),(1350,780,55,200)],
        bar=[(490,190),(1090,190),(1690,190),(490,700),
             (1090,700),(1690,700),(300,950),(960,450),(1620,950)],
        tint=(22,28,22),
    ),
    # Wave 4 - barrel cluster / industrial chaos
    dict(
        obs=[(100,100,200,100),(600,80,140,180),(1100,80,140,180),
             (1600,100,200,100),(100,820,200,100),(600,820,140,180),
             (1100,820,140,180),(1600,820,200,100),(820,420,280,240),
             (400,450,130,130),(1390,450,130,130),(400,300,80,80),
             (1440,300,80,80),(400,700,80,80),(1440,700,80,80)],
        bar=[(220,350),(220,700),(1700,350),(1700,700),
             (550,500),(1370,500),(740,200),(1180,200),
             (740,880),(1180,880),(960,200),(960,880)],
        tint=(28,24,18),
    ),
    # Wave 5 - BOSS wave: open arena, perimeter cover
    dict(
        obs=[(80,80,160,80),(560,80,160,80),(1200,80,160,80),
             (1680,80,160,80),(80,920,160,80),(560,920,160,80),
             (1200,920,160,80),(1680,920,160,80),(80,450,80,180),
             (1760,450,80,180),(400,430,90,90),(1430,430,90,90),
             (850,150,220,70),(850,860,220,70),(700,480,60,120)],
        bar=[(280,300),(1640,300),(280,780),(1640,780),
             (960,350),(960,730),(550,200),(1370,200),
             (550,880),(1370,880),(200,540),(1720,540)],
        tint=(35,18,18),
    ),
    # Wave 6 - scattered rubble, many small blocks
    dict(
        obs=[(200,150,80,80),(500,130,80,80),(800,170,80,80),
             (1100,130,80,80),(1400,150,80,80),(1700,170,80,80),
             (200,870,80,80),(500,850,80,80),(800,890,80,80),
             (1100,850,80,80),(1400,870,80,80),(1700,890,80,80),
             (350,450,80,80),(700,500,80,80),(1050,460,80,80),
             (1400,500,80,80),(550,700,80,80),(1250,700,80,80)],
        bar=[(960,540),(400,300),(1520,300),(400,750),(1520,750),
             (140,540),(1780,540),(650,420),(1270,420),
             (650,660),(1270,660),(960,200)],
        tint=(24,30,24),
    ),
    # Wave 7 - L-shaped blockades
    dict(
        obs=[(150,100,300,60),(150,100,60,260),(1470,100,300,60),
             (1710,100,60,260),(150,920,300,60),(150,700,60,220),
             (1470,920,300,60),(1710,700,60,220),(650,300,200,60),
             (650,300,60,200),(1070,300,200,60),(1270,300,60,200),
             (650,720,200,60),(650,560,60,160),(1070,720,200,60)],
        bar=[(500,540),(1420,540),(500,200),(1420,200),
             (500,870),(1420,870),(960,450),(200,450),
             (1720,450),(960,200),(960,880),(700,600)],
        tint=(20,25,32),
    ),
    # Wave 8 - diamond ring + pillars
    dict(
        obs=[(860,60,200,80),(200,350,80,360),(1640,350,80,360),
             (860,940,200,80),(400,160,80,80),(1440,160,80,80),
             (400,840,80,80),(1440,840,80,80),(700,460,80,80),
             (1140,460,80,80),(700,560,80,80),(1140,560,80,80),
             (860,300,200,60),(860,720,200,60),(600,120,120,60)],
        bar=[(960,540),(550,350),(1370,350),(550,730),(1370,730),
             (300,560),(1620,560),(960,130),(960,950),
             (750,200),(1170,200),(750,880),(1170,880)],
        tint=(18,26,30),
    ),
    # Wave 9 - asymmetric fortress ruins
    dict(
        obs=[(100,100,500,60),(100,100,60,400),(100,440,300,60),
             (1320,100,500,60),(1760,100,60,400),(1520,440,300,60),
             (500,600,60,400),(500,940,400,60),(1360,600,60,400),
             (960,80,120,120),(700,380,80,80),(1140,380,80,80),
             (760,560,200,80),(800,760,160,80),(400,260,80,80)],
        bar=[(700,200),(1220,200),(350,750),(1570,750),
             (960,350),(500,500),(1420,500),(960,760),
             (200,600),(1720,600),(700,900),(1220,900)],
        tint=(30,20,28),
    ),
    # Wave 10 - FINAL BOSS: grand hall, wide lanes
    dict(
        obs=[(60,60,420,60),(60,60,60,420),(1440,60,420,60),
             (1800,60,60,420),(60,960,420,60),(60,600,60,360),
             (1440,960,420,60),(1800,600,60,360),(800,400,320,280),
             (300,430,100,100),(1520,430,100,100),(300,570,60,60),
             (1560,570,60,60),(700,160,80,80),(1140,160,80,80)],
        bar=[(550,300),(1370,300),(550,780),(1370,780),
             (200,200),(1720,200),(200,880),(1720,880),
             (960,200),(960,880),(400,540),(1520,540)],
        tint=(38,14,14),
    ),
]

# Mutable arena data (rebuilt each wave)
floor_tiles = []
cracks      = []
bloodstains = []
obstacles   = []
barrels     = []
_arena_floor_tint = (27, 32, 30)
_enemy_navigation_cache = {}

# Blur transition state
arena_transition_timer = 0.0   # counts down from ARENA_BLUR_DURATION
ARENA_BLUR_DURATION    = 0.7


def generate_arena(wave_num):
    """Rebuild all mutable arena data for the given wave (1-10)."""
    global floor_tiles, cracks, bloodstains, obstacles, barrels
    global _arena_floor_tint, arena_transition_timer

    layout = _WAVE_LAYOUTS[(wave_num - 1) % len(_WAVE_LAYOUTS)]
    _arena_floor_tint = layout["tint"]
    _enemy_navigation_cache.clear()

    # Seeded random so the same wave always looks the same
    rng = random.Random(wave_num * 9371)

    floor_tiles = [
        (x, y, rng.randint(0, 3))
        for y in range(0, HEIGHT, TILE_SIZE)
        for x in range(0, WIDTH, TILE_SIZE)
    ]

    # Blood count scales with wave
    blood_count = min(65 + wave_num * 8, 140)
    bloodstains = [
        (rng.randint(30, WIDTH - 30),
         rng.randint(30, HEIGHT - 30),
         rng.randint(8, 30))
        for _ in range(blood_count)
    ]

    # Crack density scales with wave
    crack_count = min(180 + wave_num * 10, 280)
    cracks = [
        (rng.randint(20, WIDTH - 20),
         rng.randint(20, HEIGHT - 20),
         rng.randint(12, 50),
         rng.choice([-1, 1]))
        for _ in range(crack_count)
    ]

    obstacles = [pygame.Rect(*r) for r in layout["obs"]]
    barrels   = list(layout["bar"])

    # Start blur transition
    arena_transition_timer = ARENA_BLUR_DURATION

    # Rebuild the static cache
    draw_arena(arena_cache)



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
    r0, g0, b0 = _arena_floor_tint
    surface.fill((r0, g0, b0))

    for x, y, variation in floor_tiles:
        shade_r = max(0, min(255, r0 + 4 + variation * 3))
        shade_g = max(0, min(255, g0 + 5 + variation * 3))
        shade_b = max(0, min(255, b0 + 1 + variation * 2))
        pygame.draw.rect(
            surface,
            (shade_r, shade_g, shade_b),
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
# ARENA CACHE (rebuilt each wave via generate_arena)
# ============================================================
arena_cache = pygame.Surface((WIDTH, HEIGHT))
generate_arena(1)   # initialise wave-1 layout + draw into cache
arena_transition_timer = 0.0  # no blur on very first load


# ============================================================
# BUTTONS / MENUS
# ============================================================
class Button:
    def __init__(self, rect, text):
        self.rect = pygame.Rect(rect)
        self.text = text

    def draw(self, surface, mouse_pos):
        hovered = self.rect.collidepoint(mouse_pos)
        r = self.rect
        c = 12  # chamfer corner cut

        # 8-point chamfered polygon for outer plate
        pts = [
            (r.left + c, r.top), (r.right - c, r.top),
            (r.right, r.top + c), (r.right, r.bottom - c),
            (r.right - c, r.bottom), (r.left + c, r.bottom),
            (r.left, r.bottom - c), (r.left, r.top + c),
        ]

        # 1. Heavy drop shadow
        shadow_pts = [(p[0] + 6, p[1] + 7) for p in pts]
        pygame.draw.polygon(surface, (4, 4, 5), shadow_pts)

        # 2. Outer metal base plate
        fill_col = (48, 32, 32) if hovered else (32, 32, 34)
        pygame.draw.polygon(surface, fill_col, pts)

        # 3. Outer rim (double beveled metal border)
        border_col = (200, 48, 40) if hovered else (72, 75, 80)
        pygame.draw.polygon(surface, border_col, pts, 2)

        # Highlight along top-left edges
        pygame.draw.line(surface, (235, 90, 80) if hovered else (120, 125, 132),
                         (r.left + c, r.top + 1), (r.right - c, r.top + 1), 1)
        pygame.draw.line(surface, (235, 90, 80) if hovered else (120, 125, 132),
                         (r.left + 1, r.top + c), (r.left + 1, r.bottom - c), 1)

        # Dark groove along bottom-right edges
        pygame.draw.line(surface, (12, 12, 14),
                         (r.left + c, r.bottom - 1), (r.right - c, r.bottom - 1), 1)
        pygame.draw.line(surface, (12, 12, 14),
                         (r.right - 1, r.top + c), (r.right - 1, r.bottom - c), 1)

        # 4. Inner recessed steel plate (with inner chamfer)
        ir = r.inflate(-12, -12)
        ic = 8
        ipts = [
            (ir.left + ic, ir.top), (ir.right - ic, ir.top),
            (ir.right, ir.top + ic), (ir.right, ir.bottom - ic),
            (ir.right - ic, ir.bottom), (ir.left + ic, ir.bottom),
            (ir.left, ir.bottom - ic), (ir.left, ir.top + ic),
        ]
        inner_fill = (38, 20, 20) if hovered else (22, 22, 24)
        pygame.draw.polygon(surface, inner_fill, ipts)
        inner_border = (120, 32, 26) if hovered else (45, 47, 50)
        pygame.draw.polygon(surface, inner_border, ipts, 1)

        # Subtle brushed-steel horizontal grain
        for y_off in range(ir.top + 6, ir.bottom - 4, 8):
            g_col = (48, 26, 26) if hovered else (28, 28, 31)
            pygame.draw.line(surface, g_col, (ir.left + 6, y_off), (ir.right - 6, y_off), 1)

        # 5. Prominent Silver/Steel Bolts (Rivets) in 4 Corners
        ox, oy = 18, 16
        bolts = [
            (r.left + ox, r.top + oy),
            (r.right - ox, r.top + oy),
            (r.left + ox, r.bottom - oy),
            (r.right - ox, r.bottom - oy),
        ]
        for bx, by in bolts:
            # Dark outer socket
            pygame.draw.circle(surface, (8, 8, 10), (bx, by), 6)
            # Bolt metal head
            b_head = (95, 60, 55) if hovered else (82, 85, 90)
            pygame.draw.circle(surface, b_head, (bx, by), 5)
            # Rim ring
            pygame.draw.circle(surface, (135, 140, 148), (bx, by), 5, 1)
            # Bright top-left glint
            pygame.draw.circle(surface, (210, 215, 225), (bx - 1, by - 1), 2)
            # Center slot / cross
            pygame.draw.line(surface, (18, 18, 20), (bx - 2, by), (bx + 2, by), 1)
            pygame.draw.line(surface, (18, 18, 20), (bx, by - 2), (bx, by + 2), 1)

        # 6. Button text (blood red embossed)
        text_col = (245, 60, 45) if hovered else (185, 32, 25)

        # Deep bottom shadow
        shadow_img = button_font.render(self.text, True, (6, 1, 1))
        surface.blit(shadow_img, shadow_img.get_rect(center=(r.centerx + 2, r.centery + 3)))

        # Dark bevel depth
        depth_img = button_font.render(self.text, True, (24, 3, 3))
        surface.blit(depth_img, depth_img.get_rect(center=(r.centerx + 1, r.centery + 1)))

        # Hover red aura / glow
        if hovered:
            glow_img = button_font.render(self.text, True, (180, 30, 22))
            glow_img.set_alpha(80)
            for gox, goy in [(-2, 0), (2, 0), (0, -2), (0, 2), (-1, -1), (1, 1)]:
                surface.blit(glow_img, glow_img.get_rect(center=(r.centerx + gox, r.centery + goy)))

        # Main text
        main_t = button_font.render(self.text, True, text_col)
        surface.blit(main_t, main_t.get_rect(center=r.center))

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

    def handle_event(self, event, position=None):
        position = event.pos if position is None else position

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(position):
                self.dragging = True
                self._set_from_mouse(position)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._set_from_mouse(position)

    def _set_from_mouse(self, pos):
        rel = max(0, min(1, (pos[0] - self.rect.x) / self.rect.w))
        self.value = self.min_val + rel * (self.max_val - self.min_val)

    def draw(self, surface, mouse_pos, label, focused=False):
        if focused:
            pygame.draw.rect(
                surface, (206, 176, 82), self.rect.inflate(16, 16),
                1, border_radius=8
            )

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
        if label:
            draw_text_left(
                surface, f"{label}: {pct}%", ui_font, WHITE,
                (self.rect.x, self.rect.y - 30)
            )


# ============================================================
# MENU BACKGROUND — animated horror background
# ============================================================
class MenuBackground:
    """Dark concrete-tile background with blood splatters (red horror theme)."""
    TILE_W = 160
    TILE_H = 120

    def __init__(self):
        self.tile_surf  = self._make_tiles()
        self.blood_surf = self._make_blood()
        self.vignette   = self._make_vignette()
        self.smoke      = [self._new_smoke(anywhere=True) for _ in range(14)]

    def _make_tiles(self):
        surf = pygame.Surface((WIDTH, HEIGHT))
        surf.fill((16, 15, 16))
        rng = random.Random(88)
        for ty in range(0, HEIGHT, self.TILE_H):
            for tx in range(0, WIDTH, self.TILE_W):
                c = 22 + rng.randint(0, 8)
                pygame.draw.rect(surf, (c, c - 1, c - 1),
                                 (tx + 1, ty + 1, self.TILE_W - 2, self.TILE_H - 2))
                # Grunge noise
                for _ in range(rng.randint(3, 6)):
                    gx = tx + rng.randint(4, self.TILE_W - 14)
                    gy = ty + rng.randint(4, self.TILE_H - 14)
                    pygame.draw.ellipse(surf, (max(0, c - 7), max(0, c - 8), max(0, c - 8)),
                                        (gx, gy, rng.randint(10, 30), rng.randint(4, 10)))
        # Seam grooves
        for ty in range(0, HEIGHT + self.TILE_H, self.TILE_H):
            pygame.draw.line(surf, (8, 8, 9), (0, ty), (WIDTH, ty), 2)
            pygame.draw.line(surf, (38, 37, 40), (0, ty + 2), (WIDTH, ty + 2), 1)
        for tx in range(0, WIDTH + self.TILE_W, self.TILE_W):
            pygame.draw.line(surf, (8, 8, 9), (tx, 0), (tx, HEIGHT), 2)
            pygame.draw.line(surf, (38, 37, 40), (tx + 2, 0), (tx + 2, HEIGHT), 1)
        return surf

    def _make_blood(self):
        surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        rng = random.Random(2025)

        # Splatter clusters matching reference image
        clusters = [
            # Top-left corner & border
            (0, 0, 240, 35), (100, 150, 180, 25), (40, 320, 160, 20),
            # Top-right corner
            (WIDTH, 0, 220, 28), (WIDTH - 120, 140, 160, 22),
            # Bottom-left corner
            (0, HEIGHT, 260, 35), (120, HEIGHT - 100, 190, 24),
            # Bottom-right corner & right border
            (WIDTH, HEIGHT, 270, 38), (WIDTH - 80, HEIGHT - 220, 180, 25),
            (WIDTH - 30, HEIGHT // 2, 170, 22), (20, HEIGHT // 2 + 100, 160, 20),
            # Faint stains behind title
            (WIDTH // 2 - 240, 160, 130, 12), (WIDTH // 2 + 260, 170, 140, 12),
        ]

        for cx, cy, rad, count in clusters:
            for _ in range(count):
                bx = cx + rng.randint(-rad, rad)
                by = cy + rng.randint(-rad // 2, rad // 2)
                br = rng.randint(8, max(12, rad // 4))
                a = rng.randint(90, 195)
                r_col = rng.randint(110, 160)
                # Main blood blotch
                pygame.draw.ellipse(surf, (r_col, rng.randint(8, 16), rng.randint(6, 12), a),
                                    (bx - br, by - br // 2, br * 2, br))
                # Satellite fine spray
                for _ in range(rng.randint(4, 9)):
                    sx = bx + rng.randint(-br * 2, br * 2)
                    sy = by + rng.randint(-br * 2, br * 2)
                    sr = rng.randint(1, 4)
                    pygame.draw.circle(surf, (r_col - 10, 6, 6, a - 30), (sx, sy), sr)
                # Drip lines
                if rng.random() < 0.35:
                    drip_len = rng.randint(18, 55)
                    pygame.draw.line(surf, (r_col, 8, 6, a - 25), (bx, by), (bx, by + drip_len), rng.randint(2, 3))
                    pygame.draw.circle(surf, (r_col, 8, 6, a), (bx, by + drip_len), rng.randint(3, 4))

        # Fine blood mist across the edges
        for _ in range(250):
            ex = rng.choice([rng.randint(0, 320), rng.randint(WIDTH - 320, WIDTH)])
            ey = rng.randint(0, HEIGHT)
            pygame.draw.circle(surf, (rng.randint(100, 150), 8, 8, rng.randint(40, 110)), (ex, ey), rng.randint(1, 3))

        return surf

    def _make_vignette(self):
        surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        steps = 100
        for i in range(steps):
            a = max(0, 245 - i * 3)
            ew = i * (WIDTH // steps)
            eh = i * (HEIGHT // steps)
            pygame.draw.rect(surf, (0, 0, 0, a),
                             (ew // 2, eh // 2, WIDTH - ew, HEIGHT - eh), 30)
        return surf

    def _new_smoke(self, anywhere=False):
        life = random.uniform(6, 12)
        return {
            'x': random.randint(-80, WIDTH + 80),
            'y': random.randint(-40, HEIGHT // 3) if anywhere else random.randint(-60, -20),
            'r': random.randint(120, 260),
            'dx': random.uniform(-14, 14),
            'dy': random.uniform(-10, -3),
            'alpha': random.randint(8, 22),
            'life': life,
            'max_life': life,
        }

    def update(self, dt):
        for p in self.smoke:
            p['x'] += p['dx'] * dt
            p['y'] += p['dy'] * dt
            p['life'] -= dt
            if p['life'] <= 0:
                p.update(self._new_smoke())

    def draw(self, surface):
        surface.blit(self.tile_surf, (0, 0))
        surface.blit(self.blood_surf, (0, 0))
        # Subtle smoke cloud at top
        smoke_surf = pygame.Surface((WIDTH, HEIGHT // 2), pygame.SRCALPHA)
        for p in self.smoke:
            if p['max_life'] > 0:
                t = max(0.0, p['life'] / p['max_life'])
                a = int(p['alpha'] * t)
                sy = int(p['y'])
                if -p['r'] < sy < (HEIGHT // 2) + p['r']:
                    pygame.draw.circle(smoke_surf, (10, 9, 9, a), (int(p['x']), sy), p['r'])
        surface.blit(smoke_surf, (0, 0))
        surface.blit(self.vignette, (0, 0))


# ── Horror-themed menu button layout (480×72, centred column from y=400) ──
menu_buttons = [
    Button((WIDTH//2 - 220, 360, 440, 66), "Start"),
    Button((WIDTH//2 - 220, 438, 440, 66), "Options"),
    Button((WIDTH//2 - 220, 516, 440, 66), "How to Play"),
    Button((WIDTH//2 - 220, 594, 440, 66), "Credits"),
    Button((WIDTH//2 - 220, 672, 440, 66), "High Scores"),
    Button((WIDTH//2 - 220, 750, 440, 66), "Exit"),
]

howto_back_button      = Button((WIDTH//2 - 200, 980, 400, 64), "BACK")

options_back_button    = Button((WIDTH//2 - 200, 820, 400, 64), "BACK")
options_music_button = Button((1280, 364, 280, 56), "MUSIC: ON")
options_sfx_button = Button((1280, 504, 280, 56), "SFX: ON")
options_fullscreen_button = Button(
    (WIDTH // 2 - 220, 642, 440, 58), "FULLSCREEN: ON"
)
credits_back_button    = Button((WIDTH//2 - 200, 925, 400, 64), "BACK")
highscores_back_button = Button((WIDTH//2 - 200, 750, 400, 64), "BACK")

# Animated menu background instance
menu_bg = MenuBackground()

pause_buttons = [
    Button((760, 520, 400, 78), "RESUME"),
    Button((760, 620, 400, 78), "OPTIONS"),
    Button((760, 720, 400, 78), "MAIN MENU"),
]

end_buttons = [
    Button((WIDTH//2 - 200, 690, 400, 64), "PLAY AGAIN"),
    Button((WIDTH//2 - 200, 770, 400, 64), "MAIN MENU"),
]

INTERMISSION_CARD_WIDTH = 350
INTERMISSION_CARD_HEIGHT = 390
INTERMISSION_CARD_GAP = 22
INTERMISSION_CARD_TOP = 350
INTERMISSION_CARD_LEFT = (
    WIDTH - (4 * INTERMISSION_CARD_WIDTH + 3 * INTERMISSION_CARD_GAP)
) // 2
intermission_buy_buttons = [
    Button((
        INTERMISSION_CARD_LEFT + index * (INTERMISSION_CARD_WIDTH + INTERMISSION_CARD_GAP) + 85,
        INTERMISSION_CARD_TOP + 305,
        180,
        58,
    ), "BUY")
    for index in range(4)
]
intermission_continue_button = Button(
    (WIDTH // 2 - 170, 810, 340, 64), "CONTINUE"
)


# ============================================================
# GAME OBJECTS
# ============================================================
class Particle:
    def __init__(self, position, velocity, color, lifetime, radius):
        self.position = pygame.Vector2(position)
        self.velocity = pygame.Vector2(velocity)
        self.color = color
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.radius = radius

    def update(self, dt):
        self.position += self.velocity * dt
        self.velocity *= max(0.0, 1.0 - 4.5 * dt)
        self.lifetime -= dt

    def draw(self, surface):
        if self.lifetime <= 0:
            return

        fade = min(1.0, self.lifetime / self.max_lifetime)
        color = tuple(round(channel * fade) for channel in self.color)
        radius = max(1, round(self.radius * min(1.0, fade * 1.4)))
        pygame.draw.circle(
            surface,
            color,
            (round(self.position.x), round(self.position.y)),
            radius,
        )


class Player:
    def __init__(self):
        self.rect = pygame.Rect(945, 520, 42, 52)
        self.health = MAX_HEALTH
        self.last_damage = 0
        self.rapid_until = 0
        self.fire_rate_level = 0
        self.move_speed_level = 0
        self.weapon = "Pistol"
        self.muzzle_flash_timer = 0.0
        self.muzzle_flash_angle = 0.0
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

        if self.muzzle_flash_timer > 0:
            flash_direction = pygame.Vector2(
                math.cos(self.muzzle_flash_angle),
                math.sin(self.muzzle_flash_angle),
            )
            flash_side = pygame.Vector2(-flash_direction.y, flash_direction.x)
            muzzle = pygame.Vector2(x, y) + flash_direction * 48
            flash_tip = muzzle + flash_direction * 23
            flash_points = [
                muzzle + flash_side * 7,
                flash_tip,
                muzzle - flash_side * 7,
                muzzle + flash_direction * 4,
            ]
            pygame.draw.polygon(
                surface,
                (255, 165, 46),
                [tuple(round(value) for value in point) for point in flash_points],
            )
            pygame.draw.circle(
                surface, (255, 241, 171),
                (round(muzzle.x), round(muzzle.y)), 5
            )

        if damage_flash_timer > 0:
            pygame.draw.rect(
                surface, (255, 94, 72), self.rect.inflate(12, 12),
                3, border_radius=7
            )


ENEMY_ARCHETYPES = {
    "shambler": {
        "size": 44, "health": 1.0, "speed": 1.0,
        "damage": 1.0, "score": 100,
        "salvage": 10,
        "colors": ((63, 88, 58), (100, 115, 65), (228, 64, 48)),
    },
    "runner": {
        "size": 36, "health": 0.75, "speed": 1.55,
        "damage": 0.8, "score": 125,
        "salvage": 12,
        "colors": ((67, 103, 48), (144, 153, 69), (255, 132, 42)),
    },
    "brute": {
        "size": 60, "health": 2.0, "speed": 0.65,
        "damage": 1.5, "score": 175,
        "salvage": 18,
        "colors": ((91, 56, 45), (129, 76, 56), (242, 79, 48)),
    },
    "armored": {
        "size": 50, "health": 1.45, "speed": 0.85,
        "damage": 1.15, "score": 200,
        "salvage": 20,
        "colors": ((54, 68, 70), (98, 112, 95), (239, 190, 70)),
    },
}


def draw_zombie_sprite(surface, rect, kind, facing=None):
    """Draw the shared in-game zombie sprite at the given rectangle."""
    x, y = rect.center
    scale = rect.width / 44
    body_color, head_color, eye_color = ENEMY_ARCHETYPES[kind]["colors"]
    body = pygame.Rect(
        x - round(19 * scale), y - round(12 * scale),
        round(38 * scale), round(35 * scale),
    )
    head = pygame.Rect(
        x - round(15 * scale), y - round(25 * scale),
        round(30 * scale), round(23 * scale),
    )
    pygame.draw.ellipse(
        surface, (12, 14, 13),
        (x - round(28 * scale), rect.bottom - round(3 * scale),
         round(58 * scale), round(19 * scale))
    )
    pygame.draw.rect(
        surface, body_color, body, border_radius=max(2, round(4 * scale))
    )
    pygame.draw.rect(
        surface, head_color, head, border_radius=max(2, round(4 * scale))
    )
    pygame.draw.rect(
        surface, eye_color,
        (x - round(10 * scale), y - round(18 * scale),
         max(2, round(6 * scale)), max(2, round(5 * scale)))
    )
    pygame.draw.rect(
        surface, eye_color,
        (x + round(4 * scale), y - round(18 * scale),
         max(2, round(6 * scale)), max(2, round(5 * scale)))
    )
    pygame.draw.rect(
        surface, (30, 25, 23),
        (x - round(9 * scale), y - round(2 * scale),
         round(18 * scale), max(2, round(5 * scale)))
    )

    if kind == "armored":
        forward = facing if facing is not None else pygame.Vector2(1, 0)
        sideways = pygame.Vector2(-forward.y, forward.x)
        shield_center = pygame.Vector2(x, y) + forward * (12 * scale)
        shield_start = shield_center - sideways * (14 * scale)
        shield_end = shield_center + sideways * (14 * scale)
        shield_start = tuple(round(value) for value in shield_start)
        shield_end = tuple(round(value) for value in shield_end)
        pygame.draw.line(
            surface, (30, 38, 40), shield_start, shield_end,
            max(7, round(10 * scale))
        )
        pygame.draw.line(
            surface, (155, 166, 164), shield_start, shield_end,
            max(3, round(5 * scale))
        )


class Enemy:
    def __init__(self, x, y, wave, boss=False, kind="shambler"):
        self.boss = boss
        self.kind = "boss" if boss else kind
        self.boss_wave = wave if boss else None

        if boss:
            if wave == 5:
                size = 92
                self.boss_name = "THE CHARGER"
                self.max_hp = 85
                self.speed = 132
                self.damage = 21
                self.score_value = 900
                self.salvage_value = 80
            else:
                size = 108
                self.boss_name = "THE WARDEN"
                self.max_hp = 200
                self.speed = 145
                self.damage = 25
                self.score_value = 2200
                self.salvage_value = 150

            self.boss_phase = 1
            self.boss_state = "approach"
            self.boss_state_timer = 0.0
            self.boss_attack_cooldown = 1.4
            self.boss_attack_direction = pygame.Vector2(1, 0)
            self.boss_attack_target = pygame.Vector2(0, 0)
            self.boss_slam_pending = False
            self.boss_summon_pending = False
            self.boss_phase_pending = False
            self.boss_slam_flash_timer = 0.0
            self.boss_slam_damage = 32
            self.boss_slam_radius = 205
        else:
            stats = ENEMY_ARCHETYPES[kind]
            size = stats["size"]
            self.max_hp = max(1, round(wave * stats["health"]))
            base_speed = min(90 + (wave - 1) * 10, 180)
            self.speed = base_speed * stats["speed"]
            base_damage = 8 + wave // 2
            self.damage = max(1, round(base_damage * stats["damage"]))
            self.score_value = stats["score"]
            self.salvage_value = stats["salvage"]

        self.rect = pygame.Rect(x, y, size, size)
        self.hp = self.max_hp
        self.facing = pygame.Vector2(1, 0)
        self.front_damage_multiplier = 0.55 if kind == "armored" and not boss else 1.0
        self.burst_phase = random.uniform(0, 2.4)
        self.charge_timer = 0.0
        self.charge_cooldown = random.uniform(1.2, 2.0)
        self.hit_flash_until = 0.0

    def boss_movement(self, dt, direction, player_position, player_distance):
        """Return the boss velocity and advance its attack state machine."""
        if not self.boss:
            return pygame.Vector2()

        self.boss_slam_flash_timer = max(0.0, self.boss_slam_flash_timer - dt)

        if (
            self.boss_wave == 10
            and self.boss_phase == 1
            and self.hp <= self.max_hp * 0.5
        ):
            self.boss_phase = 2
            self.boss_state = "phase_shift"
            self.boss_state_timer = 1.05
            self.boss_attack_cooldown = 1.0
            self.boss_slam_damage = 36
            self.boss_slam_radius = 225
            self.boss_summon_pending = True
            self.boss_phase_pending = True

        if self.boss_state == "phase_shift":
            self.boss_state_timer -= dt
            if self.boss_state_timer <= 0:
                self.boss_state = "approach"
            return pygame.Vector2()

        if self.boss_state == "approach":
            self.boss_attack_cooldown = max(
                0.0, self.boss_attack_cooldown - dt
            )

            if (
                self.boss_wave == 5
                and self.boss_attack_cooldown <= 0
                and player_distance <= 680
            ):
                if direction.length_squared() > 0:
                    self.boss_attack_direction = direction.normalize()
                    self.facing.update(self.boss_attack_direction)
                self.boss_state = "charge_windup"
                self.boss_state_timer = 0.78
                self.boss_attack_cooldown = 3.6
                return pygame.Vector2()

            if (
                self.boss_wave == 10
                and self.boss_attack_cooldown <= 0
                and player_distance <= 650
            ):
                self.boss_attack_target.update(player_position)
                self.boss_state = "slam_windup"
                self.boss_state_timer = 0.98 if self.boss_phase == 1 else 0.72
                self.boss_attack_cooldown = (
                    4.2 if self.boss_phase == 1 else 2.9
                )
                return pygame.Vector2()

            speed = self.speed * (1.42 if self.boss_phase == 2 else 1.0)
            if direction.length_squared() == 0:
                return pygame.Vector2()
            return direction.normalize() * speed

        if self.boss_state == "charge_windup":
            self.boss_state_timer -= dt
            if self.boss_state_timer <= 0:
                self.boss_state = "charge"
                self.boss_state_timer = 0.64
            return pygame.Vector2()

        if self.boss_state == "charge":
            self.boss_state_timer -= dt
            if self.boss_state_timer <= 0:
                self.boss_state = "recovery"
                self.boss_state_timer = 0.95
                return pygame.Vector2()
            return self.boss_attack_direction * 560

        if self.boss_state == "slam_windup":
            self.boss_state_timer -= dt
            if self.boss_state_timer <= 0:
                self.boss_state = "slam_recovery"
                self.boss_state_timer = 0.72 if self.boss_phase == 1 else 0.52
                self.boss_slam_pending = True
                self.boss_slam_flash_timer = 0.34
            return pygame.Vector2()

        if self.boss_state in ("recovery", "slam_recovery"):
            self.boss_state_timer -= dt
            if self.boss_state_timer <= 0:
                self.boss_state = "approach"
            return pygame.Vector2()

        return pygame.Vector2()

    def interrupt_boss_charge(self):
        if self.boss and self.boss_state == "charge":
            self.boss_state = "recovery"
            self.boss_state_timer = 0.9

    def movement_speed(self, dt, player_distance):
        if self.kind == "runner":
            self.burst_phase = (self.burst_phase + dt) % 2.4
            speed_factor = 1.8 if self.burst_phase < 0.65 else 0.78
            return min(self.speed * speed_factor, 250)

        if self.kind == "brute":
            if self.charge_timer > 0:
                self.charge_timer = max(0.0, self.charge_timer - dt)
                return min(self.speed * 2.0, 225)

            self.charge_cooldown = max(0.0, self.charge_cooldown - dt)
            if player_distance < 360 and self.charge_cooldown == 0:
                self.charge_timer = 0.55
                self.charge_cooldown = 3.0
                return min(self.speed * 2.0, 225)

        return self.speed

    def update_facing(self, direction, dt):
        if direction.length_squared() == 0:
            return

        target_angle = math.atan2(direction.y, direction.x)
        current_angle = math.atan2(self.facing.y, self.facing.x)
        angle_delta = (target_angle - current_angle + math.pi) % (2 * math.pi) - math.pi
        turn_rate = 2.0 if self.kind == "armored" else 10.0
        max_turn = turn_rate * dt
        angle = current_angle + max(-max_turn, min(max_turn, angle_delta))
        self.facing.update(math.cos(angle), math.sin(angle))

    def damage_from_bullet(self, bullet):
        damage = float(bullet.damage)
        blocked_by_armor = False
        if self.kind == "armored":
            incoming_direction = -bullet.velocity.normalize()
            if self.facing.dot(incoming_direction) > 0.45:
                damage *= self.front_damage_multiplier
                blocked_by_armor = True
        return damage, blocked_by_armor

    def draw(self, surface):
        x, y = self.rect.center

        if self.boss:
            center = pygame.Vector2(x, y)
            if self.boss_state == "charge_windup":
                charge_end = tuple(round(value) for value in (
                    center + self.boss_attack_direction * 440
                ))
                pygame.draw.line(
                    surface, (86, 28, 22), (x, y), charge_end, 86
                )
                pygame.draw.line(
                    surface, (229, 91, 43), (x, y), charge_end, 7
                )
                pygame.draw.circle(
                    surface, (255, 184, 77),
                    (round(x), round(y)), 61, 4,
                )

            if self.boss_state == "slam_windup":
                elapsed = 1.0 - self.boss_state_timer / (
                    0.72 if self.boss_phase == 2 else 0.98
                )
                radius = round(
                    70 + (self.boss_slam_radius - 70)
                    * max(0.0, min(1.0, elapsed))
                )
                target = (
                    round(self.boss_attack_target.x),
                    round(self.boss_attack_target.y),
                )
                pygame.draw.circle(surface, (91, 20, 24), target, radius, 10)
                pygame.draw.circle(surface, (231, 65, 48), target, radius, 3)
                pygame.draw.line(
                    surface, (231, 65, 48),
                    (target[0] - 17, target[1]),
                    (target[0] + 17, target[1]), 3,
                )
                pygame.draw.line(
                    surface, (231, 65, 48),
                    (target[0], target[1] - 17),
                    (target[0], target[1] + 17), 3,
                )

            if self.boss_slam_flash_timer > 0:
                target = (
                    round(self.boss_attack_target.x),
                    round(self.boss_attack_target.y),
                )
                flash_radius = round(
                    self.boss_slam_radius
                    * (0.55 + 0.45 * self.boss_slam_flash_timer / 0.34)
                )
                pygame.draw.circle(
                    surface, (255, 114, 55), target, flash_radius, 13
                )

            if self.boss_wave == 5:
                pygame.draw.ellipse(
                    surface, (12, 14, 13),
                    (x - 63, self.rect.bottom - 5, 128, 32)
                )
                body = pygame.Rect(x - 43, y - 31, 86, 78)
                head = pygame.Rect(x - 34, y - 55, 68, 42)
                pygame.draw.rect(surface, (70, 35, 27), body, border_radius=9)
                pygame.draw.rect(surface, (137, 61, 39), head, border_radius=8)
                pygame.draw.polygon(
                    surface, (47, 29, 26),
                    [(x - 30, y - 43), (x - 52, y - 66), (x - 15, y - 51)],
                )
                pygame.draw.polygon(
                    surface, (47, 29, 26),
                    [(x + 30, y - 43), (x + 52, y - 66), (x + 15, y - 51)],
                )
                pygame.draw.rect(surface, (190, 84, 44), (x - 47, y - 20, 18, 35))
                pygame.draw.rect(surface, (190, 84, 44), (x + 29, y - 20, 18, 35))
                eye_color = (255, 192, 71) if self.boss_state == "charge_windup" else (244, 79, 48)
                pygame.draw.rect(surface, eye_color, (x - 21, y - 43, 13, 9))
                pygame.draw.rect(surface, eye_color, (x + 8, y - 43, 13, 9))
                pygame.draw.rect(surface, (34, 22, 20), (x - 19, y - 13, 38, 12))
            else:
                enraged = self.boss_phase == 2
                body_color = (81, 59, 46) if not enraged else (111, 42, 34)
                armor_color = (65, 83, 76) if not enraged else (139, 49, 39)
                eye_color = (245, 190, 69) if not enraged else (255, 66, 43)
                pygame.draw.ellipse(
                    surface, (12, 14, 13),
                    (x - 73, self.rect.bottom - 6, 146, 36)
                )
                pygame.draw.rect(
                    surface, body_color,
                    (x - 49, y - 37, 98, 88), border_radius=11,
                )
                pygame.draw.rect(
                    surface, armor_color,
                    (x - 43, y - 62, 86, 48), border_radius=10,
                )
                pygame.draw.polygon(
                    surface, (37, 48, 46),
                    [(x - 37, y - 52), (x - 47, y - 84), (x - 17, y - 63)],
                )
                pygame.draw.polygon(
                    surface, (37, 48, 46),
                    [(x + 37, y - 52), (x + 47, y - 84), (x + 17, y - 63)],
                )
                pygame.draw.rect(surface, (42, 48, 42), (x - 63, y - 26, 24, 50))
                pygame.draw.rect(surface, (42, 48, 42), (x + 39, y - 26, 24, 50))
                pygame.draw.rect(surface, eye_color, (x - 27, y - 50, 16, 10))
                pygame.draw.rect(surface, eye_color, (x + 11, y - 50, 16, 10))
                pygame.draw.rect(surface, (25, 26, 23), (x - 23, y - 15, 46, 13))
                pygame.draw.line(
                    surface, eye_color, (x - 30, y + 7), (x + 30, y + 7), 5
                )

        else:
            draw_zombie_sprite(surface, self.rect, self.kind, self.facing)

        if not self.boss:
            bar_w = 54
            bar_h = 7
            bar_y = self.rect.top - 15
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

        if pygame.time.get_ticks() / 1000 < self.hit_flash_until:
            pygame.draw.rect(
                surface, (255, 238, 190), self.rect,
                3, border_radius=5
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
        score_path = HIGH_SCORE_FILE
        legacy_path = LEGACY_DATA_DIR / "highscore.txt"
        if not score_path.exists() and legacy_path != score_path and legacy_path.exists():
            score_path = legacy_path
        return int(score_path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return 0


high_score = load_high_score()
game_start_high_score = high_score

state = "menu"
player = None
enemies = []
bullets = []
powerups = []
particles = []
damage_flash_timer = 0.0
wave = 1
score = 0
kills = 0
salvage_points = 0
enemies_to_spawn = 0
spawn_timer = 0
wave_break_timer = 0
banner_text = ""
banner_until = 0
record_beaten = False
game_over_reason = "GAME OVER"


def spawn_particles(
    position, count, colors, speed_range, lifetime_range, radius_range
):
    for _ in range(count):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(*speed_range)
        velocity = (math.cos(angle) * speed, math.sin(angle) * speed)
        particles.append(Particle(
            position,
            velocity,
            random.choice(colors),
            random.uniform(*lifetime_range),
            random.uniform(*radius_range),
        ))

    if len(particles) > 220:
        del particles[:len(particles) - 220]

# Transition / fade state
transition_state = None      # None, "fade_out", "fade_in"
transition_alpha = 0
transition_next_state = None
transition_speed = 450       # alpha per second
start_countdown_timer = 0
start_countdown_started = False
# arena_transition_timer is defined in the ARENA section above


def save_high_score():
    global high_score

    if score > high_score:
        high_score = score
        try:
            HIGH_SCORE_FILE.parent.mkdir(parents=True, exist_ok=True)
            HIGH_SCORE_FILE.write_text(str(high_score), encoding="utf-8")
        except OSError:
            pass


ENEMY_NAV_CELL_SIZE = 40


def enemy_navigation_cell(position):
    columns = WIDTH // ENEMY_NAV_CELL_SIZE
    rows = HEIGHT // ENEMY_NAV_CELL_SIZE
    return (
        min(columns - 1, max(
            0, round((position[0] - ENEMY_NAV_CELL_SIZE // 2)
                     / ENEMY_NAV_CELL_SIZE)
        )),
        min(rows - 1, max(
            0, round((position[1] - ENEMY_NAV_CELL_SIZE // 2)
                     / ENEMY_NAV_CELL_SIZE)
        )),
    )


def enemy_navigation_field(enemy_size, player_position):
    columns = WIDTH // ENEMY_NAV_CELL_SIZE
    rows = HEIGHT // ENEMY_NAV_CELL_SIZE
    target_cell = (
        min(columns - 1, max(0, int(player_position[0] // ENEMY_NAV_CELL_SIZE))),
        min(rows - 1, max(0, int(player_position[1] // ENEMY_NAV_CELL_SIZE))),
    )
    cached = _enemy_navigation_cache.get(enemy_size)

    if cached and cached[0] == target_cell:
        return cached[1], cached[2]

    if cached:
        walkable, neighbors = cached[2], cached[3]
    else:
        clearance_obstacles = [
            obstacle.inflate(enemy_size, enemy_size)
            for obstacle in obstacles
        ]
        walkable = set()
        for column in range(columns):
            for row in range(rows):
                center = (
                    column * ENEMY_NAV_CELL_SIZE + ENEMY_NAV_CELL_SIZE // 2,
                    row * ENEMY_NAV_CELL_SIZE + ENEMY_NAV_CELL_SIZE // 2,
                )
                if (
                    center[0] >= enemy_size // 2
                    and center[0] <= WIDTH - enemy_size // 2
                    and center[1] >= enemy_size // 2
                    and center[1] <= HEIGHT - enemy_size // 2
                    and not any(
                        obstacle.collidepoint(center)
                        for obstacle in clearance_obstacles
                    )
                ):
                    walkable.add((column, row))

        neighbors = {}
        for column, row in walkable:
            adjacent = []
            start = (
                column * ENEMY_NAV_CELL_SIZE + ENEMY_NAV_CELL_SIZE // 2,
                row * ENEMY_NAV_CELL_SIZE + ENEMY_NAV_CELL_SIZE // 2,
            )
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    destination = (column + dx, row + dy)
                    if destination not in walkable:
                        continue
                    if dx and dy and (
                        (column + dx, row) not in walkable
                        or (column, row + dy) not in walkable
                    ):
                        continue
                    end = (
                        destination[0] * ENEMY_NAV_CELL_SIZE
                        + ENEMY_NAV_CELL_SIZE // 2,
                        destination[1] * ENEMY_NAV_CELL_SIZE
                        + ENEMY_NAV_CELL_SIZE // 2,
                    )
                    if any(
                        obstacle.clipline(start, end)
                        for obstacle in clearance_obstacles
                    ):
                        continue
                    adjacent.append((
                        destination,
                        math.sqrt(2) if dx and dy else 1,
                    ))
            neighbors[(column, row)] = adjacent

    goal = min(
        walkable,
        key=lambda cell: (
            cell[0] * ENEMY_NAV_CELL_SIZE + ENEMY_NAV_CELL_SIZE // 2
            - player_position[0]
        ) ** 2 + (
            cell[1] * ENEMY_NAV_CELL_SIZE + ENEMY_NAV_CELL_SIZE // 2
            - player_position[1]
        ) ** 2,
    )
    distances = {goal: 0}
    frontier = [(0, goal)]

    while frontier:
        distance, cell = heapq.heappop(frontier)
        if distance != distances[cell]:
            continue
        for adjacent, step_cost in neighbors[cell]:
            new_distance = distance + step_cost
            if new_distance < distances.get(adjacent, float("inf")):
                distances[adjacent] = new_distance
                heapq.heappush(frontier, (new_distance, adjacent))

    _enemy_navigation_cache[enemy_size] = (
        target_cell, distances, walkable, neighbors
    )
    return distances, walkable


def enemy_direction_to_player(enemy, player_position):
    start = enemy.rect.center
    direction = pygame.Vector2(
        player_position[0] - start[0],
        player_position[1] - start[1],
    )
    clearance_obstacles = [
        obstacle.inflate(enemy.rect.width, enemy.rect.height)
        for obstacle in obstacles
    ]

    if not any(
        obstacle.clipline(start, player_position)
        for obstacle in clearance_obstacles
    ):
        return direction

    distances, walkable = enemy_navigation_field(
        enemy.rect.width, player_position
    )
    current = enemy_navigation_cell(start)
    options = []
    for column in range(max(0, current[0] - 3),
                         min(WIDTH // ENEMY_NAV_CELL_SIZE, current[0] + 4)):
        for row in range(max(0, current[1] - 3),
                         min(HEIGHT // ENEMY_NAV_CELL_SIZE, current[1] + 4)):
            cell = (column, row)
            if cell not in walkable or cell not in distances:
                continue
            waypoint_position = (
                column * ENEMY_NAV_CELL_SIZE + ENEMY_NAV_CELL_SIZE // 2,
                row * ENEMY_NAV_CELL_SIZE + ENEMY_NAV_CELL_SIZE // 2,
            )
            if any(
                obstacle.clipline(start, waypoint_position)
                for obstacle in clearance_obstacles
            ):
                continue
            waypoint_distance = math.dist(start, waypoint_position)
            options.append((
                distances[cell] + waypoint_distance / ENEMY_NAV_CELL_SIZE,
                waypoint_distance,
                waypoint_position,
            ))

    if not options:
        return direction

    _, _, waypoint_position = min(options)
    return pygame.Vector2(
        waypoint_position[0] - start[0],
        waypoint_position[1] - start[1],
    )


def choose_enemy_kind():
    kinds = ["shambler"]
    weights = [60]

    if wave >= 2:
        kinds.append("runner")
        weights.append(24)
    if wave >= 3:
        kinds.append("brute")
        weights.append(18)
    if wave >= 4:
        kinds.append("armored")
        weights.append(14)

    return random.choices(kinds, weights=weights, k=1)[0]


def spawn_enemy(boss=False):
    kind = "shambler" if boss else choose_enemy_kind()
    if boss:
        enemy_size = 92 if wave == 5 else 108
    else:
        enemy_size = ENEMY_ARCHETYPES[kind]["size"]

    player_position = player.rect.center if player else (WIDTH // 2, HEIGHT // 2)
    distances, walkable = enemy_navigation_field(
        enemy_size, player_position
    )

    def candidate_is_valid(x, y, minimum_player_distance=320,
                           avoid_nearby_enemies=True,
                           allow_enemy_overlap=False):
        rect = pygame.Rect(x, y, enemy_size, enemy_size)
        clear_rect = rect.inflate(48, 48)
        if (
            clear_rect.left < 35
            or clear_rect.top < 35
            or clear_rect.right > WIDTH - 35
            or clear_rect.bottom > HEIGHT - 35
        ):
            return False

        center = rect.center
        if any(
            obstacle.colliderect(clear_rect)
            or obstacle.inflate(enemy_size, enemy_size).collidepoint(center)
            for obstacle in obstacles
        ):
            return False

        if player:
            if rect.colliderect(player.rect):
                return False
            if math.dist(center, player.rect.center) < minimum_player_distance:
                return False

        if not allow_enemy_overlap:
            for other in enemies:
                if rect.colliderect(other.rect):
                    return False
                if (
                    avoid_nearby_enemies
                    and math.dist(center, other.rect.center)
                    < (enemy_size + other.rect.width) / 2 + 24
                ):
                    return False

        cell = enemy_navigation_cell(center)
        return cell in walkable and cell in distances

    edge_margin = max(64, enemy_size // 2 + 24)
    min_x = edge_margin
    max_x = WIDTH - enemy_size - edge_margin
    min_y = edge_margin
    max_y = HEIGHT - enemy_size - edge_margin

    for _ in range(160):
        side = random.randint(0, 3)

        if side == 0:
            x, y = random.randint(min_x, max_x), min_y
        elif side == 1:
            x, y = random.randint(min_x, max_x), max_y
        elif side == 2:
            x, y = min_x, random.randint(min_y, max_y)
        else:
            x, y = max_x, random.randint(min_y, max_y)

        if candidate_is_valid(x, y):
            return Enemy(x, y, wave, boss, kind)

    # If random edge spots are crowded, try safe reachable navigation cells
    # from farthest to nearest. This avoids the old unchecked fixed-point spawn.
    fallback_cells = sorted(
        distances,
        key=lambda cell: (
            cell[0] * ENEMY_NAV_CELL_SIZE + ENEMY_NAV_CELL_SIZE // 2
            - player_position[0]
        ) ** 2 + (
            cell[1] * ENEMY_NAV_CELL_SIZE + ENEMY_NAV_CELL_SIZE // 2
            - player_position[1]
        ) ** 2,
        reverse=True,
    )
    fallback_passes = (
        (220, False),
        (0, False),
        (0, True),
    )
    for minimum_player_distance, allow_enemy_overlap in fallback_passes:
        for column, row in fallback_cells:
            center_x = column * ENEMY_NAV_CELL_SIZE + ENEMY_NAV_CELL_SIZE // 2
            center_y = row * ENEMY_NAV_CELL_SIZE + ENEMY_NAV_CELL_SIZE // 2
            x = center_x - enemy_size // 2
            y = center_y - enemy_size // 2
            if candidate_is_valid(
                x, y, minimum_player_distance,
                avoid_nearby_enemies=False,
                allow_enemy_overlap=allow_enemy_overlap,
            ):
                return Enemy(x, y, wave, boss, kind)

    raise RuntimeError("Unable to find a safe, reachable enemy spawn point")


def reset_game():
    global player, enemies, bullets, powerups, particles
    global damage_flash_timer
    global wave, score, kills, salvage_points, enemies_to_spawn, spawn_timer
    global wave_break_timer, banner_text, banner_until, record_beaten
    global game_start_high_score

    player = Player()
    enemies = []
    bullets = []
    powerups = []
    particles = []
    damage_flash_timer = 0.0
    wave = 1
    score = 0
    kills = 0
    salvage_points = 0
    enemies_to_spawn = 0
    spawn_timer = 0
    wave_break_timer = 0
    banner_text = "WAVE 1"
    banner_until = pygame.time.get_ticks() + 2200
    record_beaten = False
    game_start_high_score = high_score

    begin_wave()


def begin_wave():
    global enemies_to_spawn, spawn_timer, banner_text, banner_until

    # Regenerate arena layout + trigger blur transition
    generate_arena(wave)

    if wave == 5:
        enemies_to_spawn = 8
    elif wave == 10:
        enemies_to_spawn = 12
    else:
        enemies_to_spawn = min(5 + wave * 2, 28)
    spawn_timer = 0.4
    banner_text = f"WAVE {wave}"
    banner_until = pygame.time.get_ticks() + 2200

    if wave % 5 == 0:
        boss = spawn_enemy(True)
        enemies.append(boss)
        banner_text = boss.boss_name


def continue_to_next_wave():
    global wave, state, wave_break_timer
    wave += 1
    wave_break_timer = 0
    begin_wave()
    state = "playing"


def intermission_options():
    return [
        {
            "id": "medical",
            "title": "FIELD DRESSING",
            "description": ("Restore up to 40 health.", "Cannot exceed max health."),
            "detail": "Useful after a rough wave.",
            "cost": 35,
            "available": player.health < MAX_HEALTH,
            "status": "HEALTH FULL",
        },
        {
            "id": "ammo",
            "title": "AMMO CACHE",
            "description": ("+45 rifle rounds.", "+12 shotgun shells."),
            "detail": "Stored ammo stays with you.",
            "cost": 30,
            "available": True,
            "status": "",
        },
        {
            "id": "fire_rate",
            "title": "WEAPON TUNING",
            "description": ("Reduce firing cooldowns 10%.", "Stacks up to 3 levels."),
            "detail": f"CURRENT LEVEL: {player.fire_rate_level}/3",
            "cost": 60 + player.fire_rate_level * 25,
            "available": player.fire_rate_level < 3,
            "status": "MAX LEVEL",
        },
        {
            "id": "mobility",
            "title": "MOVEMENT TRAINING",
            "description": ("Move 8% faster.", "Stacks up to 3 levels."),
            "detail": f"CURRENT LEVEL: {player.move_speed_level}/3",
            "cost": 50 + player.move_speed_level * 25,
            "available": player.move_speed_level < 3,
            "status": "MAX LEVEL",
        },
    ]


def select_intermission_upgrade(index):
    global salvage_points
    options = intermission_options()
    if not 0 <= index < len(options):
        return False

    option = options[index]
    if not option["available"] or salvage_points < option["cost"]:
        return False

    salvage_points -= option["cost"]
    if option["id"] == "medical":
        player.health = min(MAX_HEALTH, player.health + 40)
    elif option["id"] == "ammo":
        player.ammo["Rifle"] += 45
        player.ammo["Shotgun"] += 12
    elif option["id"] == "fire_rate":
        player.fire_rate_level += 1
    elif option["id"] == "mobility":
        player.move_speed_level += 1

    continue_to_next_wave()
    return True


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

    delay *= 1.0 - 0.1 * player.fire_rate_level

    if now - player.last_shot < delay:
        return

    if (
        player.weapon != "Pistol"
        and player.ammo[player.weapon] <= 0
    ):
        return

    player.last_shot = now
    player.muzzle_flash_timer = 0.065
    player.muzzle_flash_angle = math.atan2(
        target[1] - player.rect.centery,
        target[0] - player.rect.centerx,
    )
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
    global damage_flash_timer
    now = pygame.time.get_ticks() / 1000

    if now - player.last_damage < DAMAGE_COOLDOWN:
        return

    player.last_damage = now
    player.health = max(0, player.health - amount)
    damage_flash_timer = 0.22
    spawn_particles(
        player.rect.center, 6,
        ((255, 79, 57), (190, 34, 31), (255, 174, 91)),
        (45, 135), (0.18, 0.34), (2, 4),
    )
    play_sound("hurt")


def end_game(won):
    global state, game_over_reason, record_beaten

    state = "win" if won else "gameover"
    game_over_reason = "YOU SURVIVED" if won else "YOU DIED"

    if won:
        play_sound("victory")
    else:
        play_sound("game_over")

    record_beaten = score > game_start_high_score
    save_high_score()
    stop_music()


def kill_enemy(enemy):
    global score, kills, salvage_points

    if enemy not in enemies:
        return

    if enemy.boss:
        death_colors = ((230, 57, 45), (151, 37, 35), (255, 167, 73))
    else:
        death_colors = (
            ENEMY_ARCHETYPES[enemy.kind]["colors"][0],
            (154, 42, 39),
            (220, 75, 52),
        )
    spawn_particles(
        enemy.rect.center, 18 if enemy.boss else 10,
        death_colors, (60, 245), (0.24, 0.52), (2, 5),
    )
    enemies.remove(enemy)
    kills += 1
    score += enemy.score_value
    salvage_points += enemy.salvage_value
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
        panel.fill((10, 13, 12, 105))
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
    draw_panel(WIDTH // 2 - 160, 28, 320, 116)

    draw_text(
        surface, f"WAVE {wave}/{WAVE_GOAL}",
        ui_font, WHITE, (WIDTH // 2, 52)
    )
    draw_text(
        surface, f"SCORE {score}",
        small_font, YELLOW, (WIDTH // 2, 82)
    )
    draw_text(
        surface, f"SCRAP {salvage_points}",
        tiny_font, (190, 175, 115), (WIDTH // 2, 108)
    )

    boss = next((enemy for enemy in enemies if enemy.boss), None)
    if boss:
        boss_panel = pygame.Rect(WIDTH // 2 - 300, 155, 600, 72)
        draw_panel(
            boss_panel.x, boss_panel.y, boss_panel.width, boss_panel.height
        )
        pygame.draw.rect(
            surface, (158, 48, 38), boss_panel, 3, border_radius=8
        )
        draw_text_left(
            surface, boss.boss_name, small_font, WHITE,
            (boss_panel.left + 20, boss_panel.top + 9),
        )
        if boss.boss_wave == 10 and boss.boss_phase == 2:
            draw_text_left(
                surface, "PHASE II", small_ui_font, (255, 93, 61),
                (boss_panel.right - 112, boss_panel.top + 13),
            )

        health_rect = pygame.Rect(
            boss_panel.left + 18, boss_panel.top + 39,
            boss_panel.width - 36, 19,
        )
        pygame.draw.rect(surface, (55, 19, 20), health_rect, border_radius=5)
        health_width = int(
            health_rect.width * max(0, boss.hp) / boss.max_hp
        )
        if health_width > 0:
            pygame.draw.rect(
                surface, (205, 49, 39),
                (health_rect.x, health_rect.y, health_width, health_rect.height),
                border_radius=5,
            )
        draw_text(
            surface, f"{max(0, math.ceil(boss.hp))} / {boss.max_hp} HP",
            tiny_ui_font, WHITE, health_rect.center,
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
        surface, "SUPPLY CHOICE IN",
        ui_font, WHITE, (WIDTH // 2, box.top + 65)
    )
    draw_text(
        surface, str(countdown),
        title_font, YELLOW, (WIDTH // 2, box.centery + 25)
    )


def draw_start_countdown(surface):
    if not start_countdown_started or start_countdown_timer <= 0:
        return

    # \u2500\u2500 Full-screen dark overlay (blackout / blur effect) \u2500\u2500
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 195))
    surface.blit(overlay, (0, 0))

    num = math.ceil(start_countdown_timer)
    # Pulse: number breathes once per second
    frac = start_countdown_timer - (num - 1)
    pulse = 1.0 + 0.08 * math.sin(frac * math.pi)

    # Glow ring behind the number
    glow_r = int(130 * pulse)
    glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
    pygame.draw.circle(glow_surf, (30, 80, 10, 60),
                       (glow_r, glow_r), glow_r)
    pygame.draw.circle(glow_surf, (50, 130, 15, 40),
                       (glow_r, glow_r), int(glow_r * 0.7))
    surface.blit(glow_surf, (WIDTH // 2 - glow_r, HEIGHT // 2 - glow_r))

    # Shadow
    shadow_s = title_font.render(str(num), True, (8, 18, 4))
    surface.blit(shadow_s, shadow_s.get_rect(
        center=(WIDTH // 2 + 6, HEIGHT // 2 + 8)))

    # Main number in lime-green horror colour
    num_s = title_font.render(str(num), True, (139, 195, 74))
    surface.blit(num_s, num_s.get_rect(center=(WIDTH // 2, HEIGHT // 2)))

    # Label above
    draw_text(surface, "GET READY", ui_font,
              (100, 155, 50), (WIDTH // 2, HEIGHT // 2 - 130))

    # Thin rule + drips below number for atmosphere
    pygame.draw.line(surface, (40, 65, 15),
                     (WIDTH // 2 - 260, HEIGHT // 2 + 112),
                     (WIDTH // 2 + 260, HEIGHT // 2 + 112), 1)
    for drip_x in [WIDTH // 2 - 20, WIDTH // 2, WIDTH // 2 + 20]:
        pygame.draw.rect(surface, (30, 55, 10),
                         (drip_x, HEIGHT // 2 + 113, 2, 18))



def draw_metal_panel(surface, rect, chamfer=16, border_color=(72, 76, 82), fill_color=(20, 20, 22), draw_bolts=True):
    r = pygame.Rect(rect)
    c = chamfer
    pts = [
        (r.left + c, r.top), (r.right - c, r.top),
        (r.right, r.top + c), (r.right, r.bottom - c),
        (r.right - c, r.bottom), (r.left + c, r.bottom),
        (r.left, r.bottom - c), (r.left, r.top + c),
    ]

    # Drop shadow
    shadow_pts = [(p[0] + 6, p[1] + 7) for p in pts]
    pygame.draw.polygon(surface, (4, 4, 5), shadow_pts)

    # Base fill
    pygame.draw.polygon(surface, fill_color, pts)

    # Outer border
    pygame.draw.polygon(surface, border_color, pts, 2)

    # Top-left highlight & bottom-right shadow
    pygame.draw.line(surface, (110, 115, 124), (r.left + c, r.top + 1), (r.right - c, r.top + 1), 1)
    pygame.draw.line(surface, (110, 115, 124), (r.left + 1, r.top + c), (r.left + 1, r.bottom - c), 1)
    pygame.draw.line(surface, (10, 10, 12), (r.left + c, r.bottom - 1), (r.right - c, r.bottom - 1), 1)
    pygame.draw.line(surface, (10, 10, 12), (r.right - 1, r.top + c), (r.right - 1, r.bottom - c), 1)

    # 4 Corner Bolts
    if draw_bolts:
        ox, oy = 22, 20
        bolts = [
            (r.left + ox, r.top + oy),
            (r.right - ox, r.top + oy),
            (r.left + ox, r.bottom - oy),
            (r.right - ox, r.bottom - oy),
        ]
        for bx, by in bolts:
            pygame.draw.circle(surface, (8, 8, 10), (bx, by), 6)
            pygame.draw.circle(surface, (82, 86, 92), (bx, by), 5)
            pygame.draw.circle(surface, (135, 140, 148), (bx, by), 5, 1)
            pygame.draw.circle(surface, (210, 215, 225), (bx - 1, by - 1), 2)
            pygame.draw.line(surface, (18, 18, 20), (bx - 2, by), (bx + 2, by), 1)
            pygame.draw.line(surface, (18, 18, 20), (bx, by - 2), (bx, by + 2), 1)


def draw_intermission(surface, mouse_pos):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 190))
    surface.blit(overlay, (0, 0))

    draw_metal_panel(
        surface, (150, 150, WIDTH - 300, 790),
        chamfer=20, border_color=(140, 38, 30), fill_color=(17, 18, 19)
    )
    draw_header_title(surface, "SUPPLY DROP", cy=205)
    draw_text(
        surface, f"WAVE {wave} CLEARED",
        ui_font, WHITE, (WIDTH // 2, 278)
    )
    draw_text(
        surface, f"AVAILABLE SCRAP: {salvage_points}",
        small_font, YELLOW, (WIDTH // 2, 316)
    )

    options = intermission_options()
    for index, option in enumerate(options):
        card = pygame.Rect(
            INTERMISSION_CARD_LEFT + index * (
                INTERMISSION_CARD_WIDTH + INTERMISSION_CARD_GAP
            ),
            INTERMISSION_CARD_TOP,
            INTERMISSION_CARD_WIDTH,
            INTERMISSION_CARD_HEIGHT,
        )
        draw_metal_panel(
            surface, card, chamfer=12,
            border_color=(75, 78, 82), fill_color=(23, 25, 27),
            draw_bolts=False,
        )
        draw_text(
            surface, option["title"], body_font,
            (225, 67, 54), (card.centerx, card.top + 52)
        )
        for line_index, line in enumerate(option["description"]):
            draw_text(
                surface, line, small_ui_font, WHITE,
                (card.centerx, card.top + 126 + line_index * 38)
            )
        draw_text(
            surface, option["detail"], tiny_ui_font,
            (155, 160, 157), (card.centerx, card.top + 224)
        )
        draw_text(
            surface, f"COST: {option['cost']} SCRAP", small_font,
            YELLOW, (card.centerx, card.top + 268)
        )

        if not option["available"]:
            status = option["status"]
            draw_text(
                surface, status, small_font, GRAY,
                (card.centerx, card.bottom - 34)
            )
        elif salvage_points < option["cost"]:
            draw_text(
                surface, f"NEED {option['cost'] - salvage_points} MORE SCRAP",
                tiny_font, GRAY, (card.centerx, card.bottom - 34)
            )
        else:
            intermission_buy_buttons[index].draw(surface, mouse_pos)

    intermission_continue_button.draw(surface, mouse_pos)
    draw_text(
        surface, "Click BUY or press 1-4. Press Enter to continue without buying.",
        small_font, (170, 175, 170), (WIDTH // 2, 900), False
    )


def draw_key_badge(surface, text, center_x, center_y, width=None, min_w=44, h=34, border_color=(90, 95, 102), text_color=(240, 240, 240)):
    rendered = small_ui_font.render(text, True, text_color)
    bw = max(min_w, rendered.get_width() + 16) if width is None else width
    rect = pygame.Rect(center_x - bw // 2, center_y - h // 2, bw, h)

    # Shadow
    pygame.draw.rect(surface, (4, 4, 5), rect.move(2, 3), border_radius=4)
    # Keycap body
    pygame.draw.rect(surface, (32, 34, 38), rect, border_radius=4)
    # Bevel border
    pygame.draw.rect(surface, border_color, rect, 1, border_radius=4)
    # Top edge sheen
    pygame.draw.line(surface, (135, 140, 150), (rect.left + 3, rect.top + 1), (rect.right - 3, rect.top + 1), 1)
    # Bottom shadow
    pygame.draw.line(surface, (14, 14, 16), (rect.left + 3, rect.bottom - 2), (rect.right - 3, rect.bottom - 2), 1)

    surface.blit(rendered, rendered.get_rect(center=rect.center))
    return rect


def draw_header_title(surface, title_text, cy=105):
    cx = WIDTH // 2

    # 1. Red glow passes
    for ox, oy, a in [(-5, -5, 25), (5, -5, 25), (-5, 5, 25), (5, 5, 25),
                      (-7, 0, 35), (7, 0, 35), (0, -7, 35), (0, 7, 35),
                      (-3, 0, 50), (3, 0, 50), (0, -3, 50), (0, 3, 50)]:
        glow_s = heading_font.render(title_text, True, (135, 12, 10))
        glow_s.set_alpha(a)
        surface.blit(glow_s, glow_s.get_rect(center=(cx + ox, cy + oy)))

    # 2. 3D shadow
    for offset in range(6, 0, -1):
        sh_img = heading_font.render(title_text, True, (12 + offset * 2, 2, 2))
        surface.blit(sh_img, sh_img.get_rect(center=(cx + offset, cy + offset)))

    # 3. Main crimson text
    main_img = heading_font.render(title_text, True, (210, 32, 24))
    surface.blit(main_img, main_img.get_rect(center=(cx, cy)))

    # 4. Top glint
    top_bevel = heading_font.render(title_text, True, (250, 95, 85))
    top_bevel.set_alpha(85)
    surface.blit(top_bevel, top_bevel.get_rect(center=(cx, cy - 2)))

    # 5. Distressed horizontal scratches
    t_w = heading_font.size(title_text)[0] // 2
    rnd = random.Random(hash(title_text) & 0xFFFF)
    for _ in range(7):
        sx = cx + rnd.randint(-t_w + 10, t_w - 40)
        sy = cy + rnd.randint(-18, 18)
        sw = rnd.randint(18, 45)
        pygame.draw.line(surface, (16, 2, 2), (sx, sy), (sx + sw, sy), 1)
        pygame.draw.line(surface, (240, 75, 65), (sx, sy + 1), (sx + sw - 4, sy + 1), 1)

    # 6. Tapered divider wings
    tw = t_w + 35
    wing_len = 260
    # Left wing
    pygame.draw.polygon(surface, (85, 95, 75),
                        [(cx - tw - wing_len, cy), (cx - tw, cy - 3), (cx - tw, cy + 3)])
    pygame.draw.line(surface, (135, 148, 120), (cx - tw - wing_len, cy), (cx - tw, cy - 1), 1)
    # Right wing
    pygame.draw.polygon(surface, (85, 95, 75),
                        [(cx + tw + wing_len, cy), (cx + tw, cy - 3), (cx + tw, cy + 3)])
    pygame.draw.line(surface, (135, 148, 120), (cx + tw, cy - 1), (cx + tw + wing_len, cy), 1)


def _horror_screen_base(surface, title_text, title_y=230):
    """Shared horror-styled background + panel for all sub-screens."""
    menu_bg.draw(surface)
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 165))
    surface.blit(overlay, (0, 0))

    # Chamfered panel
    px, py, pw, ph = 510, 130, 900, 820
    c = 18
    pts = [
        (px + c, py), (px + pw - c, py),
        (px + pw, py + c), (px + pw, py + ph - c),
        (px + pw - c, py + ph), (px + c, py + ph),
        (px, py + ph - c), (px, py + c),
    ]
    pygame.draw.polygon(surface, (18, 16, 17), pts)
    pygame.draw.polygon(surface, (110, 30, 24), pts, 2)

    # Accent strips
    pygame.draw.rect(surface, (45, 14, 12), (px + 20, py + 18, pw - 40, 3))
    pygame.draw.rect(surface, (45, 14, 12), (px + 20, py + ph - 21, pw - 40, 3))

    # Corner L-brackets on the panel
    for cx2, cy2, dx2, dy2 in [
        (px + 14, py + 14, 1, 1), (px + pw - 14, py + 14, -1, 1),
        (px + 14, py + ph - 14, 1, -1), (px + pw - 14, py + ph - 14, -1, -1),
    ]:
        pygame.draw.line(surface, (140, 36, 28),
                         (cx2, cy2), (cx2 + dx2 * 26, cy2), 2)
        pygame.draw.line(surface, (140, 36, 28),
                         (cx2, cy2), (cx2, cy2 + dy2 * 26), 2)

    # Title glow passes
    for ox, oy in [(-2, -2), (2, -2), (-2, 2), (2, 2)]:
        gs = heading_font.render(title_text, True, (90, 14, 12))
        gs.set_alpha(50)
        surface.blit(gs, gs.get_rect(center=(WIDTH // 2 + ox, title_y + oy)))
    draw_text(surface, title_text, heading_font,
              (18, 4, 4), (WIDTH // 2 + 4, title_y + 5))
    draw_text(surface, title_text, heading_font,
              (210, 36, 28), (WIDTH // 2, title_y))

    # Horizontal rule + drips under title
    rule_y = title_y + 52
    pygame.draw.line(surface, (110, 30, 24),
                     (px + 60, rule_y), (px + pw - 60, rule_y), 1)
    import random as _rnd2
    _rnd2.seed(hash(title_text) & 0xFFFF)
    for _ in range(6):
        drip_x = WIDTH // 2 + _rnd2.randint(-200, 200)
        drip_h = _rnd2.randint(8, 22)
        pygame.draw.rect(surface, (60, 12, 10), (drip_x, rule_y, 2, drip_h))
    _rnd2.seed()


def draw_panel(surface, heading, lines, buttons, mouse_pos):
    _horror_screen_base(surface, heading)

    for i, line in enumerate(lines):
        draw_text(
            surface, line, ui_font, (200, 205, 195),
            (WIDTH // 2, 345 + i * 56)
        )

    for button in buttons:
        button.draw(surface, mouse_pos)


def draw_menu(surface, mouse_pos):
    # -- Concrete-tile horror background --
    menu_bg.draw(surface)
    cx = WIDTH // 2
    ty = 190

    # 1. Atmospheric blood-red glow behind title
    for ox, oy, a in [(-6, -6, 25), (6, -6, 25), (-6, 6, 25), (6, 6, 25),
                      (-10, 0, 35), (10, 0, 35), (0, -10, 35), (0, 10, 35),
                      (-4, 0, 55), (4, 0, 55), (0, -4, 55), (0, 4, 55)]:
        glow_s = title_font.render("DEADLAST", True, (140, 14, 10))
        glow_s.set_alpha(a)
        surface.blit(glow_s, glow_s.get_rect(center=(cx + ox, ty + oy)))

    # 2. Heavy 3D dark shadow
    for offset in range(9, 0, -1):
        sh_col = (12 + offset * 2, 2, 2)
        sh_img = title_font.render("DEADLAST", True, sh_col)
        surface.blit(sh_img, sh_img.get_rect(center=(cx + offset, ty + offset)))

    # 3. Main letter surface (crimson red)
    main_img = title_font.render("DEADLAST", True, (195, 26, 20))
    surface.blit(main_img, main_img.get_rect(center=(cx, ty)))

    # 4. Top metallic bevel glint
    top_bevel = title_font.render("DEADLAST", True, (245, 85, 75))
    top_bevel.set_alpha(90)
    surface.blit(top_bevel, top_bevel.get_rect(center=(cx, ty - 2)))

    # 5. Distressed horizontal metallic slashes across title
    import random as _rnd_t
    _rnd_t.seed(101)
    for _ in range(10):
        sx = cx + _rnd_t.randint(-280, 220)
        sy = ty + _rnd_t.randint(-40, 40)
        sw = _rnd_t.randint(30, 85)
        pygame.draw.line(surface, (16, 2, 2), (sx, sy), (sx + sw, sy), 1)
        pygame.draw.line(surface, (235, 70, 60), (sx, sy + 1), (sx + sw - 6, sy + 1), 1)
    _rnd_t.seed()

    # -- Subtitle with tapered horizontal wings --
    sy = 278
    # Left tapered wing
    pygame.draw.polygon(surface, (85, 95, 75),
                        [(cx - 440, sy), (cx - 190, sy - 3), (cx - 190, sy + 3)])
    pygame.draw.line(surface, (135, 148, 120), (cx - 440, sy), (cx - 190, sy - 1), 1)

    # Right tapered wing
    pygame.draw.polygon(surface, (85, 95, 75),
                        [(cx + 440, sy), (cx + 190, sy - 3), (cx + 190, sy + 3)])
    pygame.draw.line(surface, (135, 148, 120), (cx + 190, sy - 1), (cx + 440, sy), 1)

    # Subtitle text
    draw_text(surface, "THE LAST OUTBREAK", ui_font, (10, 12, 8), (cx + 2, sy + 2), shadow=False)
    draw_text(surface, "THE LAST OUTBREAK", ui_font, (135, 148, 120), (cx, sy), shadow=False)

    # -- Buttons (NO icons below!) --
    for button in menu_buttons:
        button.draw(surface, mouse_pos)

    draw_text(
        surface, "Developed by: Micah Madrigal", tiny_font,
        (165, 170, 155), (cx, HEIGHT - 32), shadow=False
    )

def draw_howto(surface, mouse_pos):
    menu_bg.draw(surface)

    # Dark atmospheric overlay
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    surface.blit(overlay, (0, 0))

    # Header Title
    draw_header_title(surface, "HOW TO PLAY", cy=100)

    # Main Master Panel (Metal Armor-Plate)
    pw, ph = 1420, 790
    px = (WIDTH - pw) // 2
    py = 170
    draw_metal_panel(surface, (px, py, pw, ph), chamfer=18, border_color=(140, 38, 30), fill_color=(18, 18, 20))

    # ── MODULE 1: SURVIVOR CONTROLS (Top sub-panel) ──
    m1_rect = pygame.Rect(px + 30, py + 25, pw - 60, 185)
    draw_metal_panel(surface, m1_rect, chamfer=10, border_color=(60, 64, 70), fill_color=(24, 25, 28), draw_bolts=False)

    sec1_title = section_font.render("SURVIVOR CONTROLS", True, (215, 45, 35))
    surface.blit(sec1_title, (m1_rect.left + 24, m1_rect.top + 16))
    pygame.draw.line(surface, (95, 25, 20), (m1_rect.left + 24, m1_rect.top + 52), (m1_rect.right - 24, m1_rect.top + 52), 1)

    # Movement Controls
    row_y1 = m1_rect.top + 85
    draw_key_badge(surface, "W", m1_rect.left + 48, row_y1, width=38)
    draw_key_badge(surface, "A", m1_rect.left + 90, row_y1, width=38)
    draw_key_badge(surface, "S", m1_rect.left + 132, row_y1, width=38)
    draw_key_badge(surface, "D", m1_rect.left + 174, row_y1, width=38)

    slash = small_ui_font.render("or", True, (130, 135, 140))
    surface.blit(slash, (m1_rect.left + 204, row_y1 - 10))

    draw_key_badge(surface, "ARROW KEYS", m1_rect.left + 295, row_y1, width=130)

    mv_label = body_font.render("MOVE SURVIVOR", True, (240, 240, 240))
    surface.blit(mv_label, (m1_rect.left + 385, row_y1 - 12))
    mv_sub = small_ui_font.render("Move freely in eight directions", True, (145, 150, 155))
    surface.blit(mv_sub, (m1_rect.left + 385, row_y1 + 18))

    # Combat & Pause Controls
    row_y2 = m1_rect.top + 148
    draw_key_badge(surface, "MOUSE AIM & CLICK", m1_rect.left + 130, row_y2, width=195, text_color=(250, 80, 70), border_color=(150, 40, 32))
    sht_label = body_font.render("FIRE WEAPON", True, (240, 240, 240))
    surface.blit(sht_label, (m1_rect.left + 245, row_y2 - 12))
    sht_sub = small_ui_font.render("Precise cursor aiming with fast projectiles", True, (145, 150, 155))
    surface.blit(sht_sub, (m1_rect.left + 245, row_y2 + 18))

    # Pause on the right side
    draw_key_badge(surface, "ESC", m1_rect.left + 780, row_y1, width=65)
    slash2 = small_ui_font.render("/", True, (130, 135, 140))
    surface.blit(slash2, (m1_rect.left + 822, row_y1 - 10))
    draw_key_badge(surface, "P", m1_rect.left + 850, row_y1, width=42)
    p_label = body_font.render("PAUSE MENU", True, (240, 240, 240))
    surface.blit(p_label, (m1_rect.left + 890, row_y1 - 12))
    p_sub = small_ui_font.render("Suspend battle & review survival status", True, (145, 150, 155))
    surface.blit(p_sub, (m1_rect.left + 890, row_y1 + 18))

    # Fullscreen key
    draw_key_badge(surface, "F11", m1_rect.left + 800, row_y2, width=65)
    fs_label = body_font.render("FULLSCREEN", True, (240, 240, 240))
    surface.blit(fs_label, (m1_rect.left + 890, row_y2 - 12))
    fs_sub = small_ui_font.render("Toggle borderless / windowed display", True, (145, 150, 155))
    surface.blit(fs_sub, (m1_rect.left + 890, row_y2 + 18))

    # ── MODULE 2: WEAPON ARSENAL (Middle sub-panel) ──
    m2_rect = pygame.Rect(px + 30, py + 225, pw - 60, 225)
    draw_metal_panel(surface, m2_rect, chamfer=10, border_color=(60, 64, 70), fill_color=(24, 25, 28), draw_bolts=False)

    sec2_title = section_font.render("WEAPON ARSENAL", True, (215, 45, 35))
    surface.blit(sec2_title, (m2_rect.left + 24, m2_rect.top + 14))
    pygame.draw.line(surface, (95, 25, 20), (m2_rect.left + 24, m2_rect.top + 48), (m2_rect.right - 24, m2_rect.top + 48), 1)

    # 3 Weapon Cards side-by-side
    card_w = (m2_rect.width - 48 - 32) // 3
    card_h = 150
    card_y = m2_rect.top + 60

    weapons = [
        ("1", "PISTOL", "UNLIMITED AMMO", (245, 190, 60), "Semi-Auto Tactical Sidearm", "Reliable baseline firearm", "Always equipped at Wave 1"),
        ("2", "ASSAULT RIFLE", "UNLOCKED AT WAVE 2", (100, 220, 120), "High-Rate Automatic Rifle", "90 Rounds • High damage per second", "Hold left-click to suppress hordes"),
        ("3", "COMBAT SHOTGUN", "UNLOCKED AT WAVE 3", (235, 75, 60), "Heavy 5-Pellet Cone Spread", "24 Shells • Devastating CQC burst", "Wipes packs & clears clumped swarms"),
    ]

    for idx, (key_num, w_name, w_badge, b_col, w_type, w_desc1, w_desc2) in enumerate(weapons):
        cx_card = m2_rect.left + 24 + idx * (card_w + 16)
        c_rect = pygame.Rect(cx_card, card_y, card_w, card_h)
        # Inset weapon card plate
        pygame.draw.rect(surface, (16, 17, 19), c_rect, border_radius=6)
        pygame.draw.rect(surface, (50, 54, 60), c_rect, 1, border_radius=6)

        # Key badge + Weapon Name
        draw_key_badge(surface, key_num, c_rect.left + 26, c_rect.top + 24, width=34, text_color=(250, 80, 70), border_color=(140, 40, 35))
        w_t = body_font.render(w_name, True, (245, 245, 245))
        surface.blit(w_t, (c_rect.left + 54, c_rect.top + 10))

        # Status Badge (e.g. UNLIMITED AMMO or UNLOCKED AT WAVE 2)
        bg_t = tiny_ui_font.render(w_badge, True, b_col)
        surface.blit(bg_t, (c_rect.left + 54, c_rect.top + 38))

        # Details
        pygame.draw.line(surface, (38, 40, 44), (c_rect.left + 16, c_rect.top + 64), (c_rect.right - 16, c_rect.top + 64), 1)
        d1 = small_ui_font.render(w_type, True, (200, 205, 210))
        surface.blit(d1, (c_rect.left + 16, c_rect.top + 74))
        d2 = tiny_ui_font.render(w_desc1, True, (145, 150, 155))
        surface.blit(d2, (c_rect.left + 16, c_rect.top + 100))
        d3 = tiny_ui_font.render(w_desc2, True, (115, 120, 125))
        surface.blit(d3, (c_rect.left + 16, c_rect.top + 122))

    # MODULE 3: ZOMBIE FIELD GUIDE AND SUPPLY DROPS
    m3_rect = pygame.Rect(px + 30, py + 465, pw - 60, 295)
    draw_metal_panel(surface, m3_rect, chamfer=10, border_color=(60, 64, 70), fill_color=(24, 25, 28), draw_bolts=False)

    sec3_title = section_font.render("ZOMBIE THREAT GUIDE", True, (215, 45, 35))
    surface.blit(sec3_title, (m3_rect.left + 24, m3_rect.top + 14))
    pygame.draw.line(surface, (95, 25, 20), (m3_rect.left + 24, m3_rect.top + 48), (m3_rect.right - 24, m3_rect.top + 48), 1)

    zombie_profiles = [
        (
            "shambler", "SHAMBLER", "W1+", (100, 130, 75),
            "Steady chaser.", "No special move.",
        ),
        (
            "runner", "RUNNER", "W2+", (235, 132, 55),
            "Fast burst attacks.", "Low health; keep moving.",
        ),
        (
            "brute", "BRUTE", "W3+", (175, 75, 55),
            "Slow and very tough.", "Charges nearby.",
        ),
        (
            "armored", "ARMORED", "W4+", (205, 176, 76),
            "Shielded from the front.", "Flank to hit harder.",
        ),
    ]
    zombie_gap = 12
    zombie_card_w = (m3_rect.width - 48 - zombie_gap * 3) // 4
    zombie_card_y = m3_rect.top + 60

    for idx, (kind, name, unlock, accent, detail_one, detail_two) in enumerate(zombie_profiles):
        card_x = m3_rect.left + 24 + idx * (zombie_card_w + zombie_gap)
        card = pygame.Rect(card_x, zombie_card_y, zombie_card_w, 96)
        pygame.draw.rect(surface, (16, 17, 19), card, border_radius=6)
        pygame.draw.rect(surface, (50, 54, 60), card, 1, border_radius=6)

        sprite_size = ENEMY_ARCHETYPES[kind]["size"]
        sprite_rect = pygame.Rect(0, 0, sprite_size, sprite_size)
        sprite_rect.center = (card.left + 44, card.centery - 5)
        preview_radius = sprite_size // 2 + 8
        pygame.draw.circle(
            surface, (28, 31, 29), sprite_rect.center, preview_radius
        )
        pygame.draw.circle(
            surface, accent, sprite_rect.center, preview_radius, 2
        )
        draw_zombie_sprite(surface, sprite_rect, kind)

        text_x = card.left + 94
        surface.blit(small_font.render(name, True, WHITE), (text_x, card.top + 7))
        unlock_image = tiny_ui_font.render(unlock, True, accent)
        surface.blit(unlock_image, (card.right - unlock_image.get_width() - 12, card.top + 12))
        surface.blit(tiny_ui_font.render(detail_one, True, (190, 195, 190)), (text_x, card.top + 44))
        surface.blit(tiny_ui_font.render(detail_two, True, (145, 150, 150)), (text_x, card.top + 68))

    drops = [
        ("+", (75, 185, 85), "FIELD DRESSING", "Restores up to 35 health"),
        ("A", (235, 190, 75), "AMMO CACHE", "+45 rifle ammo, +12 shotgun"),
        ("R", (85, 165, 235), "RAPID-FIRE STIM", "Faster firing for 7 seconds"),
    ]
    d_card_w = (m3_rect.width - 48 - 24) // 3
    d_card_y = m3_rect.top + 164

    for idx, (icon_char, icon_col, d_name, d_effect) in enumerate(drops):
        dx_card = m3_rect.left + 24 + idx * (d_card_w + 12)
        d_rect = pygame.Rect(dx_card, d_card_y, d_card_w, 66)
        pygame.draw.rect(surface, (16, 17, 19), d_rect, border_radius=6)
        pygame.draw.rect(surface, (50, 54, 60), d_rect, 1, border_radius=6)

        ibox = pygame.Rect(d_rect.left + 12, d_rect.top + 13, 40, 40)
        pygame.draw.rect(surface, icon_col, ibox, border_radius=4)
        draw_text(surface, icon_char, body_font, (10, 12, 10), ibox.center, False)
        surface.blit(body_font.render(d_name, True, WHITE), (d_rect.left + 64, d_rect.top + 4))
        surface.blit(tiny_ui_font.render(d_effect, True, icon_col), (d_rect.left + 64, d_rect.top + 36))

    w_ribbon = pygame.Rect(m3_rect.left + 24, m3_rect.top + 239, m3_rect.width - 48, 44)
    pygame.draw.rect(surface, (36, 16, 16), w_ribbon, border_radius=6)
    pygame.draw.rect(surface, (165, 42, 34), w_ribbon, 1, border_radius=6)
    draw_text(
        surface,
        "BOSSES: WAVE 5 CHARGER - DODGE ITS DASH LANE | WAVE 10 WARDEN - ESCAPE THE MARKED SLAM",
        tiny_ui_font, (245, 80, 70), (w_ribbon.centerx, w_ribbon.top + 11), False,
    )
    draw_text(
        surface,
        "BETWEEN WAVES: BUY WITH 1-4 OR CLICK | ENTER: CONTINUE WITHOUT BUYING",
        tiny_ui_font, (210, 185, 135), (w_ribbon.centerx, w_ribbon.top + 32), False,
    )

    # Back button
    howto_back_button.draw(surface, mouse_pos)


def draw_pause(surface, mouse_pos):
    draw_panel(surface, "PAUSED", [
        "The dead are still out there...",
        "Catch your breath. Then fight back.",
        "Press ESC or P to resume.",
    ], pause_buttons, mouse_pos)


def draw_end_screen(surface, mouse_pos, won):
    # Horror background + dark overlay
    menu_bg.draw(surface)
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 170))
    surface.blit(overlay, (0, 0))

    heading = "YOU SURVIVED" if won else "YOU DIED"
    title_col = (139, 195, 74) if won else (200, 50, 40)

    # Panel
    px, py, pw, ph = 610, 160, 700, 760
    c = 16
    pts = [
        (px + c, py), (px + pw - c, py),
        (px + pw, py + c), (px + pw, py + ph - c),
        (px + pw - c, py + ph), (px + c, py + ph),
        (px, py + ph - c), (px, py + c),
    ]
    pygame.draw.polygon(surface, (10, 16, 7), pts)
    border_col = (50, 100, 20) if won else (110, 30, 25)
    pygame.draw.polygon(surface, border_col, pts, 2)
    pygame.draw.rect(surface, (22, 38, 10), (px + 20, py + 18, pw - 40, 3))
    pygame.draw.rect(surface, (22, 38, 10), (px + 20, py + ph - 21, pw - 40, 3))

    # Corner brackets
    bc = (80, 130, 30) if won else (160, 50, 40)
    for cx2, cy2, dx2, dy2 in [
        (px + 14, py + 14, 1, 1), (px + pw - 14, py + 14, -1, 1),
        (px + 14, py + ph - 14, 1, -1), (px + pw - 14, py + ph - 14, -1, -1),
    ]:
        pygame.draw.line(surface, bc, (cx2, cy2), (cx2 + dx2 * 26, cy2), 2)
        pygame.draw.line(surface, bc, (cx2, cy2), (cx2, cy2 + dy2 * 26), 2)

    # Title glow + shadow + main
    for ox, oy in [(-2, -2), (2, -2), (-2, 2), (2, 2)]:
        gs = heading_font.render(heading, True, title_col)
        gs.set_alpha(45)
        surface.blit(gs, gs.get_rect(center=(WIDTH // 2 + ox, 258 + oy)))
    draw_text(surface, heading, heading_font,
              (8, 18, 4), (WIDTH // 2 + 4, 262))
    draw_text(surface, heading, heading_font,
              title_col, (WIDTH // 2, 258))

    # Rule + drips
    rule_y = 306
    pygame.draw.line(surface, border_col,
                     (px + 60, rule_y), (px + pw - 60, rule_y), 1)
    drip_col = (50, 90, 20) if won else (90, 18, 14)
    for drip_x in [WIDTH//2 - 120, WIDTH//2 - 40, WIDTH//2 + 60, WIDTH//2 + 130]:
        pygame.draw.rect(surface, drip_col, (drip_x, rule_y, 2, 18))

    # Stats
    draw_text(surface, f"FINAL SCORE: {score}",
              heading_font, (200, 230, 140), (WIDTH // 2, 370))
    draw_text(surface, f"ZOMBIES KILLED: {kills}",
              ui_font, (175, 215, 130), (WIDTH // 2, 450))
    draw_text(surface, f"HIGH SCORE: {high_score}",
              ui_font, (220, 195, 80), (WIDTH // 2, 510))

    if record_beaten:
        # Flashing new-record badge
        flash = abs(math.sin(pygame.time.get_ticks() / 500)) > 0.5
        badge_col = (220, 195, 80) if flash else (150, 130, 40)
        draw_text(surface, "-- NEW HIGH SCORE! --",
                  heading_font, badge_col, (WIDTH // 2, 575))

    # Flavour line
    flavour = "The infection has been contained... for now." if won \
              else "The dead reclaim what was yours."
    draw_text(surface, flavour, small_font,
              (100, 140, 60), (WIDTH // 2, 640))

    for button in end_buttons:
        button.draw(surface, mouse_pos)


def draw_options(surface, mouse_pos, music_slider, sfx_slider):
    _horror_screen_base(surface, "OPTIONS")

    # Section label: Music
    draw_text(surface, "MUSIC VOLUME", ui_font,
              (100, 155, 50), (WIDTH // 2, 350))
    music_slider.draw(
        surface, mouse_pos, "", focused=options_slider_focus == 0
    )
    draw_text(
        surface, f"{round(music_slider.value * 100)}%", small_font,
        WHITE, (1205, music_slider.rect.centery), False
    )
    options_music_button.text = f"MUSIC: {'ON' if music_enabled else 'OFF'}"
    options_music_button.draw(surface, mouse_pos)

    # Section label: SFX
    draw_text(surface, "SFX VOLUME", ui_font,
              (100, 155, 50), (WIDTH // 2, 490))
    sfx_slider.draw(
        surface, mouse_pos, "", focused=options_slider_focus == 1
    )
    draw_text(
        surface, f"{round(sfx_slider.value * 100)}%", small_font,
        WHITE, (1205, sfx_slider.rect.centery), False
    )
    options_sfx_button.text = f"SFX: {'ON' if sound_enabled else 'OFF'}"
    options_sfx_button.draw(surface, mouse_pos)

    # Separator
    pygame.draw.line(surface, (50, 80, 18),
                     (WIDTH // 2 - 300, 625), (WIDTH // 2 + 300, 625), 1)

    # Fullscreen toggle
    options_fullscreen_button.text = (
        f"FULLSCREEN: {'ON' if fullscreen else 'OFF'}"
    )
    options_fullscreen_button.draw(surface, mouse_pos)
    draw_text(surface, "F11 also toggles display mode", small_font,
              (125, 135, 110), (WIDTH // 2, 720), False)
    draw_text(
        surface, "TAB selects a slider  •  LEFT / RIGHT adjusts  •  HOME / END sets min / max",
        tiny_ui_font, (125, 135, 110), (WIDTH // 2, 758), False
    )
    draw_text(
        surface, "M toggles music  •  N toggles sound effects  •  ESC returns",
        tiny_ui_font, (125, 135, 110), (WIDTH // 2, 782), False
    )

    options_back_button.draw(surface, mouse_pos)


def draw_credits(surface, mouse_pos):
    menu_bg.draw(surface)

    # Dark atmospheric overlay
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    surface.blit(overlay, (0, 0))

    # Header Title
    draw_header_title(surface, "CREDITS", cy=100)

    # Master Armor-Plate Panel
    pw, ph = 1200, 720
    px = (WIDTH - pw) // 2
    py = 170
    draw_metal_panel(surface, (px, py, pw, ph), chamfer=18, border_color=(140, 38, 30), fill_color=(18, 18, 20))

    # ── HEADER BRANDING PLAQUE ──
    hdr_rect = pygame.Rect(px + 30, py + 25, pw - 60, 130)
    draw_metal_panel(surface, hdr_rect, chamfer=10, border_color=(60, 64, 70), fill_color=(24, 25, 28), draw_bolts=False)

    for offset in range(4, 0, -1):
        sh = heading_font.render("DEADLAST", True, (15 + offset * 2, 2, 2))
        surface.blit(sh, sh.get_rect(center=(hdr_rect.centerx + offset, hdr_rect.top + 46 + offset)))
    gt = heading_font.render("DEADLAST", True, (220, 35, 28))
    surface.blit(gt, gt.get_rect(center=(hdr_rect.centerx, hdr_rect.top + 46)))
    top_glint = heading_font.render("DEADLAST", True, (255, 110, 100))
    top_glint.set_alpha(75)
    surface.blit(top_glint, top_glint.get_rect(center=(hdr_rect.centerx, hdr_rect.top + 44)))

    game_sub = body_font.render("THE LAST OUTBREAK  •  2D ZOMBIE SURVIVAL HORROR", True, (140, 150, 125))
    surface.blit(game_sub, game_sub.get_rect(center=(hdr_rect.centerx, hdr_rect.top + 96)))

    # ── SECTION 1: PROGRAMMING & DESIGN ──
    s1_rect = pygame.Rect(px + 30, py + 172, pw - 60, 155)
    draw_metal_panel(surface, s1_rect, chamfer=10, border_color=(60, 64, 70), fill_color=(24, 25, 28), draw_bolts=False)

    s1_tag = section_font.render("PROGRAMMING & GAME DESIGN", True, (215, 45, 35))
    surface.blit(s1_tag, (s1_rect.left + 24, s1_rect.top + 16))
    pygame.draw.line(surface, (95, 25, 20), (s1_rect.left + 24, s1_rect.top + 52), (s1_rect.right - 24, s1_rect.top + 52), 1)

    lead_name = body_font.render("Micah Madrigal", True, (245, 245, 245))
    surface.blit(lead_name, (s1_rect.left + 35, s1_rect.top + 68))
    lead_role = small_ui_font.render("Core Engine Architecture, Gameplay Systems, Weapon Mechanics & UI Design", True, (160, 165, 170))
    surface.blit(lead_role, (s1_rect.left + 35, s1_rect.top + 106))

    engine_tag = small_ui_font.render("Powered by Pygame (SDL2)", True, (135, 145, 120))
    surface.blit(engine_tag, (s1_rect.right - engine_tag.get_width() - 35, s1_rect.top + 68))

    # ── SECTION 2: AUDIO & SOUNDSCAPE ──
    s2_rect = pygame.Rect(px + 30, py + 344, pw - 60, 180)
    draw_metal_panel(surface, s2_rect, chamfer=10, border_color=(60, 64, 70), fill_color=(24, 25, 28), draw_bolts=False)

    s2_tag = section_font.render("AUDIO & SOUNDSCAPE", True, (215, 45, 35))
    surface.blit(s2_tag, (s2_rect.left + 24, s2_rect.top + 16))
    pygame.draw.line(surface, (95, 25, 20), (s2_rect.left + 24, s2_rect.top + 52), (s2_rect.right - 24, s2_rect.top + 52), 1)

    # Music line
    draw_key_badge(surface, "MUSIC", s2_rect.left + 65, s2_rect.top + 80, width=80, text_color=(235, 190, 75))
    m_txt1 = body_font.render("menu_music.mp3", True, (240, 240, 240))
    surface.blit(m_txt1, (s2_rect.left + 120, s2_rect.top + 66))
    m_slash = small_ui_font.render("•", True, (130, 135, 140))
    surface.blit(m_slash, (s2_rect.left + 360, s2_rect.top + 70))
    m_txt2 = body_font.render("gameplay_music.mp3", True, (240, 240, 240))
    surface.blit(m_txt2, (s2_rect.left + 390, s2_rect.top + 66))
    m_desc = small_ui_font.render("Dynamic tension score transitioning from briefing to relentless arena combat", True, (145, 150, 155))
    surface.blit(m_desc, (s2_rect.left + 120, s2_rect.top + 100))

    # SFX line
    draw_key_badge(surface, "SFX", s2_rect.left + 65, s2_rect.top + 144, width=80, text_color=(100, 220, 120))
    s_txt = small_ui_font.render("Gunshot  •  Player Hurt  •  Zombie Death  •  UI Clicks  •  Victory  •  Game Over", True, (200, 205, 210))
    surface.blit(s_txt, (s2_rect.left + 120, s2_rect.top + 132))

    # ── SECTION 3: SURVIVOR COMMENDATION ──
    s3_rect = pygame.Rect(px + 30, py + 540, pw - 60, 155)
    draw_metal_panel(surface, s3_rect, chamfer=10, border_color=(60, 64, 70), fill_color=(24, 25, 28), draw_bolts=False)

    thx_title = body_font.render("THANK YOU FOR PLAYING DEADLAST", True, (245, 245, 245))
    surface.blit(thx_title, thx_title.get_rect(center=(s3_rect.centerx, s3_rect.top + 34)))

    thx_line1 = small_ui_font.render("Survive the outbreak. Aim for the head. Leave no zombie standing.", True, (215, 60, 50))
    surface.blit(thx_line1, thx_line1.get_rect(center=(s3_rect.centerx, s3_rect.top + 72)))

    thx_line2 = tiny_ui_font.render("Created with passion for classic horror action & twin-stick survival arcade games.", True, (140, 145, 150))
    surface.blit(thx_line2, thx_line2.get_rect(center=(s3_rect.centerx, s3_rect.top + 106)))

    # Back button
    credits_back_button.draw(surface, mouse_pos)


def draw_highscores(surface, mouse_pos):
    _horror_screen_base(surface, "HIGH SCORES")

    score_text = str(high_score)

    # Score trophy area
    draw_text(surface, "BEST SCORE", ui_font,
              (100, 155, 50), (WIDTH // 2, 340))
    draw_text(surface, score_text, title_font,
              (220, 195, 80), (WIDTH // 2, 430))

    # Separator
    pygame.draw.line(surface, (50, 80, 18),
                     (WIDTH // 2 - 260, 505), (WIDTH // 2 + 260, 505), 1)

    draw_text(surface, "Can you beat the dead count?",
              ui_font, (130, 175, 80), (WIDTH // 2, 548))
    draw_text(surface, "Survive all 10 waves. Leave no zombie standing.",
              small_font, (80, 110, 45), (WIDTH // 2, 595))

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
music_slider = Slider((WIDTH // 2 - 200, 390, 400, 24), 0.0, 1.0, music_volume)
sfx_slider = Slider((WIDTH // 2 - 200, 530, 400, 24), 0.0, 1.0, sfx_volume)
options_slider_focus = 0
options_return_state = "menu"
volume_settings_dirty = False


def sync_volume_settings(persist=False):
    global music_volume, sfx_volume
    music_volume = music_slider.value
    sfx_volume = sfx_slider.value

    for sound in sounds.values():
        if sound:
            sound.set_volume(sfx_volume)
    if mixer_ready:
        pygame.mixer.music.set_volume(music_volume)

    if persist:
        save_settings()


def toggle_music_setting():
    global music_enabled
    music_enabled = not music_enabled
    if music_enabled:
        track = (
            "gameplay_music.mp3"
            if (
                state in ("playing", "paused", "countdown", "intermission")
                or (state == "options" and options_return_state == "paused")
            )
            else "menu_music.mp3"
        )
        play_music(track)
    else:
        stop_music()
    save_settings()
    play_sound("click")


def toggle_sfx_setting():
    global sound_enabled
    sound_enabled = not sound_enabled
    save_settings()
    if sound_enabled:
        play_sound("click")
    elif mixer_ready:
        pygame.mixer.stop()

running = True

while running:
    dt = min(clock.tick(FPS) / 1000.0, 0.04)

    world_mouse = window_to_canvas(pygame.mouse.get_pos(), window.get_size())

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

            elif state == "intermission":
                if event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                    if select_intermission_upgrade(event.key - pygame.K_1):
                        play_sound("click")
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    continue_to_next_wave()
                    play_sound("click")

            elif state == "paused":
                if event.key in (pygame.K_ESCAPE, pygame.K_p):
                    state = "playing"
                    play_sound("click")

            elif state == "howto" and event.key == pygame.K_ESCAPE:
                state = "menu"

            elif state == "options":
                if event.key == pygame.K_ESCAPE:
                    state = options_return_state
                    play_sound("click")
                elif event.key == pygame.K_TAB:
                    options_slider_focus = 1 - options_slider_focus
                    play_sound("click")
                elif event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                    slider = music_slider if options_slider_focus == 0 else sfx_slider
                    step = 0.05 if event.key == pygame.K_RIGHT else -0.05
                    slider.value = max(
                        slider.min_val,
                        min(slider.max_val, slider.value + step),
                    )
                    sync_volume_settings(persist=True)
                elif event.key == pygame.K_HOME:
                    slider = music_slider if options_slider_focus == 0 else sfx_slider
                    slider.value = slider.min_val
                    sync_volume_settings(persist=True)
                elif event.key == pygame.K_END:
                    slider = music_slider if options_slider_focus == 0 else sfx_slider
                    slider.value = slider.max_val
                    sync_volume_settings(persist=True)
                elif event.key == pygame.K_m:
                    toggle_music_setting()
                elif event.key == pygame.K_n:
                    toggle_sfx_setting()

            elif state in ("credits", "highscores") and event.key == pygame.K_ESCAPE:
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
            pos = window_to_canvas(
                event.pos,
                window.get_size()
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
                            options_return_state = "menu"
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
                previous_values = (music_slider.value, sfx_slider.value)
                music_slider.handle_event(event, pos)
                sfx_slider.handle_event(event, pos)
                if (music_slider.value, sfx_slider.value) != previous_values:
                    sync_volume_settings()
                    volume_settings_dirty = True
                if music_slider.rect.collidepoint(pos):
                    options_slider_focus = 0
                elif sfx_slider.rect.collidepoint(pos):
                    options_slider_focus = 1

                if options_music_button.clicked(pos):
                    toggle_music_setting()
                elif options_sfx_button.clicked(pos):
                    toggle_sfx_setting()
                elif options_fullscreen_button.clicked(pos):
                    play_sound("click")
                    toggle_fullscreen()
                elif options_back_button.clicked(pos):
                    play_sound("click")
                    state = options_return_state

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
                    options_return_state = "paused"
                    options_slider_focus = 0
                    state = "options"

                elif pause_buttons[2].clicked(pos):
                    play_sound("click")
                    state = "menu"
                    play_music("menu_music.mp3")

            elif state == "intermission":
                button_handled = False
                for index, button in enumerate(intermission_buy_buttons):
                    if button.clicked(pos):
                        button_handled = True
                        if select_intermission_upgrade(index):
                            play_sound("click")
                        break

                if (
                    not button_handled
                    and intermission_continue_button.clicked(pos)
                ):
                    continue_to_next_wave()
                    play_sound("click")

            elif state in ("win", "gameover"):
                if end_buttons[0].clicked(pos):
                    play_sound("click")
                    reset_game()
                    state = "playing"
                    play_music("gameplay_music.mp3")

                elif end_buttons[1].clicked(pos):
                    play_sound("click")
                    state = "menu"
                    play_music("menu_music.mp3")

        elif event.type == pygame.MOUSEMOTION:
            if state == "options":
                pos = window_to_canvas(
                    event.pos,
                    window.get_size()
                )
                previous_values = (music_slider.value, sfx_slider.value)
                music_slider.handle_event(event, pos)
                sfx_slider.handle_event(event, pos)
                if (music_slider.value, sfx_slider.value) != previous_values:
                    sync_volume_settings()
                    volume_settings_dirty = True

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            pos = window_to_canvas(event.pos, window.get_size())
            music_slider.handle_event(event, pos)
            sfx_slider.handle_event(event, pos)
            if volume_settings_dirty:
                save_settings()
                volume_settings_dirty = False

    # ========================================================
    # GAMEPLAY UPDATE
    # ========================================================
    if state != "paused":
        damage_flash_timer = max(0.0, damage_flash_timer - dt)
        if player:
            player.muzzle_flash_timer = max(
                0.0, player.muzzle_flash_timer - dt
            )
        for particle in particles[:]:
            particle.update(dt)
            if particle.lifetime <= 0:
                particles.remove(particle)

    # Tick arena blur-transition
    if arena_transition_timer > 0:
        arena_transition_timer = max(0.0, arena_transition_timer - dt)

    if state == "countdown" and transition_state is None:
        if not start_countdown_started:
            if pygame.time.get_ticks() >= banner_until:
                start_countdown_started = True
                play_sound("countdown")
        else:
            previous_number = math.ceil(start_countdown_timer)
            start_countdown_timer = max(0, start_countdown_timer - dt)
            if start_countdown_timer > 0 and math.ceil(start_countdown_timer) < previous_number:
                play_sound("countdown")
            if start_countdown_timer == 0:
                state = "playing"

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
            move_speed = PLAYER_SPEED * (1.0 + 0.08 * player.move_speed_level)
            move_player(
                direction.x * move_speed * dt,
                direction.y * move_speed * dt
            )

        if pygame.mouse.get_pressed()[0]:
            # Use the current mouse location in native coordinates.
            world_mouse = window_to_canvas(
                pygame.mouse.get_pos(),
                window.get_size()
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
                    damage, blocked_by_armor = enemy.damage_from_bullet(bullet)
                    enemy.hp -= damage
                    enemy.hit_flash_until = pygame.time.get_ticks() / 1000 + 0.09
                    if blocked_by_armor:
                        impact_colors = (
                            (255, 222, 117),
                            (255, 249, 205),
                            (137, 167, 171),
                        )
                    else:
                        impact_colors = (
                            (233, 75, 55),
                            (172, 38, 36),
                            (255, 151, 93),
                        )
                    spawn_particles(
                        bullet.pos, 6, impact_colors,
                        (70, 230), (0.14, 0.31), (2, 4),
                    )
                    bullet.alive = False
                    hit_enemy = enemy
                    break

            if not bullet.alive and bullet in bullets:
                bullets.remove(bullet)

            if hit_enemy and hit_enemy.hp <= 0:
                kill_enemy(hit_enemy)

        # Zombies chase and attack the player
        for enemy in enemies[:]:
            player_distance = math.dist(enemy.rect.center, player.rect.center)
            direction = enemy_direction_to_player(
                enemy, player.rect.center
            )

            if enemy.boss:
                move_velocity = enemy.boss_movement(
                    dt, direction, player.rect.center, player_distance
                )

                if enemy.boss_phase_pending:
                    enemy.boss_phase_pending = False
                    banner_text = "THE WARDEN ENRAGES!"
                    banner_until = pygame.time.get_ticks() + 1100

                if enemy.boss_summon_pending:
                    enemy.boss_summon_pending = False
                    for _ in range(3):
                        enemies.append(spawn_enemy(False))

                if enemy.boss_slam_pending:
                    enemy.boss_slam_pending = False
                    target = enemy.boss_attack_target
                    closest_x = max(
                        player.rect.left, min(target.x, player.rect.right)
                    )
                    closest_y = max(
                        player.rect.top, min(target.y, player.rect.bottom)
                    )
                    if math.dist(
                        (closest_x, closest_y), target
                    ) <= enemy.boss_slam_radius:
                        damage_player(enemy.boss_slam_damage)
                    spawn_particles(
                        target, 24,
                        ((255, 109, 51), (206, 47, 36), (255, 193, 86)),
                        (75, 310), (0.18, 0.48), (3, 7),
                    )

                if (
                    enemy.boss_state == "approach"
                    and direction.length_squared() > 0
                ):
                    enemy.update_facing(direction, dt)
            else:
                move_speed = enemy.movement_speed(dt, player_distance)
                if direction.length_squared() > 0:
                    enemy.update_facing(direction, dt)
                    move_velocity = direction.normalize() * move_speed
                else:
                    move_velocity = pygame.Vector2()

            if move_velocity.length_squared() > 0:
                move = move_velocity * dt
                old_x, old_y = enemy.rect.x, enemy.rect.y
                blocked = False

                enemy.rect.x += round(move.x)

                for obstacle in obstacles:
                    if enemy.rect.colliderect(obstacle):
                        enemy.rect.x = old_x
                        blocked = True
                        break

                enemy.rect.y += round(move.y)

                for obstacle in obstacles:
                    if enemy.rect.colliderect(obstacle):
                        enemy.rect.y = old_y
                        blocked = True
                        break

                if blocked:
                    enemy.interrupt_boss_charge()

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
                    state = "intermission"
        else:
            wave_break_timer = 0

        if player.health <= 0:
            end_game(False)

        # Save a new high score during gameplay
        if score > high_score:
            save_high_score()

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
                state = "countdown"
                start_countdown_timer = 3
                start_countdown_started = False
                play_music("gameplay_music.mp3")
            transition_state = "fade_in"

    elif transition_state == "fade_in":
        transition_alpha -= transition_speed * dt
        if transition_alpha <= 0:
            transition_alpha = 0
            transition_state = None
            transition_next_state = None

    # Update menu background animation
    if state == "menu":
        menu_bg.update(dt)

    # ========================================================
    # RENDER TO THE NATIVE 1920 x 1080 CANVAS
    # ========================================================
    # Arena background: apply pixelated blur during wave transition
    if arena_transition_timer > 0 and state in ("playing", "countdown", "paused"):
        blur_factor = arena_transition_timer / ARENA_BLUR_DURATION  # 1->0
        # Scale down then back up to simulate blur
        scale_div = max(2, int(8 * blur_factor))   # 8 -> 2
        small = pygame.transform.scale(
            arena_cache, (WIDTH // scale_div, HEIGHT // scale_div))
        blurred = pygame.transform.scale(small, (WIDTH, HEIGHT))
        screen.blit(blurred, (0, 0))
        # Dark vignette that fades away with the blur
        dark = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dark.fill((0, 0, 0, int(160 * blur_factor)))
        screen.blit(dark, (0, 0))
    else:
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

    elif state in ("playing", "paused", "countdown", "intermission"):
        for powerup in powerups:
            powerup.draw(screen)

        for bullet in bullets:
            bullet.draw(screen)

        for enemy in enemies:
            enemy.draw(screen)

        if player:
            player.draw(screen, world_mouse)

        for particle in particles:
            particle.draw(screen)

        if damage_flash_timer > 0:
            damage_alpha = round(72 * min(1.0, damage_flash_timer / 0.22))
            damage_overlay_surface.fill((130, 14, 14, damage_alpha))
            screen.blit(damage_overlay_surface, (0, 0))

        draw_hud(screen)
        draw_banner(screen)

        if state == "countdown":
            draw_start_countdown(screen)

        if state == "playing":
            draw_wave_countdown(screen)

        if state == "paused":
            draw_pause(screen, world_mouse)

        if state == "intermission":
            draw_intermission(screen, world_mouse)

    elif state == "win":
        draw_end_screen(screen, world_mouse, True)

    elif state == "gameover":
        draw_end_screen(screen, world_mouse, False)

    # Draw fade transition overlay on top of everything
    draw_transition(screen)

    # ========================================================
    # SCALE THE COMPLETE FRAME TO THE WINDOW
    # ========================================================
    # Fill the entire window, stretching the canvas to fit its aspect ratio.
    frame = pygame.transform.smoothscale(screen, window.get_size())
    window.blit(frame, (0, 0))
    pygame.display.flip()

pygame.quit()
sys.exit()
