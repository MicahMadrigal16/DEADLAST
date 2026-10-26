from array import array
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

# ============================================================
# GAME ICON (procedural, no external .ico file needed)
# ============================================================
_icon = pygame.Surface((32, 32), pygame.SRCALPHA)
_icon.fill((0, 0, 0, 0))  # transparent background
# Blood-red "D" shape for DEADLAST
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
        fill   = (38, 60, 18)   if hovered else (14, 22, 8)
        border = (139, 195, 74) if hovered else (60, 95, 22)
        text_c = (220, 240, 160) if hovered else (155, 210, 90)

        # Chamfered-corner polygon (clip 8px at each corner)
        c = 8
        r = self.rect
        pts = [
            (r.left + c, r.top), (r.right - c, r.top),
            (r.right, r.top + c), (r.right, r.bottom - c),
            (r.right - c, r.bottom), (r.left + c, r.bottom),
            (r.left, r.bottom - c), (r.left, r.top + c),
        ]
        pygame.draw.polygon(surface, fill, pts)
        pygame.draw.polygon(surface, border, pts, 2)

        # Directional sheen on left 35%
        sheen_surf = pygame.Surface((int(r.w * 0.35), r.h), pygame.SRCALPHA)
        sheen_surf.fill((200, 255, 120, 18))
        surface.blit(sheen_surf, (r.left, r.top))

        # Hover drip at bottom center
        if hovered:
            drip_x = r.centerx - 1
            drip_y = r.bottom
            pygame.draw.rect(surface, (139, 195, 74), (drip_x, drip_y, 3, 14))

        draw_text(
            surface, self.text, button_font, text_c,
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


# ============================================================
# MENU BACKGROUND — animated horror background
# ============================================================
class MenuBackground:
    """Layered animated horror background for the main menu."""

    def __init__(self):
        # -- Fog puffs --
        self.fog_puffs = []
        for _ in range(18):
            self.fog_puffs.append(self._new_fog(spawn_anywhere=True))

        # -- Zombie silhouettes --
        self.zombies = []
        for i in range(5):
            self.zombies.append({
                'x': random.randint(0, WIDTH),
                'y': int(HEIGHT * 0.92),
                'scale': random.uniform(0.7, 1.3),
                'speed': random.uniform(18, 45),
                'phase': random.uniform(0, math.pi * 2),
                'opacity': random.randint(120, 160),
                't': random.uniform(0, math.pi * 2),
            })

        # -- Pre-render cracked wall surface --
        self.wall_surf = pygame.Surface((WIDTH, HEIGHT))
        self.wall_surf.fill((16, 24, 10))
        for _ in range(8):
            pts = []
            x = random.randint(0, WIDTH)
            y = random.randint(0, HEIGHT)
            for _s in range(random.randint(6, 14)):
                x += random.randint(-120, 120)
                y += random.randint(-80, 80)
                pts.append((x, y))
            if len(pts) >= 2:
                pygame.draw.lines(self.wall_surf, (8, 14, 4), False, pts, 2)
        for _ in range(150):
            x1 = random.randint(0, WIDTH)
            y1 = random.randint(0, HEIGHT)
            x2 = x1 + random.randint(-30, 30)
            y2 = y1 + random.randint(-30, 30)
            pygame.draw.line(self.wall_surf, (12, 18, 7), (x1, y1), (x2, y2), 1)
        self.wall_surf.set_alpha(200)

        # -- Pre-render vignette --
        self.vignette = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for i in range(60):
            ew = WIDTH // 2 + i * 22
            eh = HEIGHT // 2 + i * 12
            ex = WIDTH // 2 - ew // 2
            ey = HEIGHT // 2 - eh // 2
            a = max(0, 170 - i * 3)
            pygame.draw.ellipse(self.vignette, (0, 0, 0, a),
                                (ex, ey, ew, eh), 28)

        # -- Flickering light blobs state --
        self.light_timer = 0.0
        self.light_alphas = [random.randint(18, 55) for _ in range(3)]
        self.light_positions = [
            (int(WIDTH * 0.12), int(HEIGHT * 0.18)),
            (int(WIDTH * 0.25), int(HEIGHT * 0.08)),
            (int(WIDTH * 0.05), int(HEIGHT * 0.45)),
        ]

    # ------------------------------------------------------------------
    def _new_fog(self, spawn_anywhere=False):
        life = random.uniform(3.0, 8.0)
        return {
            'x': random.randint(-120, WIDTH + 120),
            'y': random.randint(0, HEIGHT) if spawn_anywhere else HEIGHT + random.randint(0, 80),
            'r': random.randint(60, 180),
            'dx': random.uniform(-18, 18),
            'dy': random.uniform(-28, -10),
            'alpha': random.randint(18, 35),
            'life': life,
            'max_life': life,
        }

    # ------------------------------------------------------------------
    def update(self, dt):
        # Fog
        for p in self.fog_puffs:
            p['x'] += p['dx'] * dt
            p['y'] += p['dy'] * dt
            p['life'] -= dt
            if p['life'] <= 0:
                p.update(self._new_fog())

        # Zombies — walk cycle
        for z in self.zombies:
            z['t'] += dt * 2.2
            z['x'] += z['speed'] * dt
            if z['x'] > WIDTH + 120:
                z['x'] = -120
                z['y'] = int(HEIGHT * 0.92) + random.randint(-20, 20)

        # Flicker lights
        self.light_timer += dt
        if self.light_timer > random.uniform(0.08, 0.25):
            self.light_timer = 0.0
            self.light_alphas = [random.randint(18, 55) for _ in range(3)]

    # ------------------------------------------------------------------
    def _draw_zombie(self, surface, x, y, scale, opacity, t):
        """Draw a procedural zombie silhouette onto surface at (x,y)."""
        col = (22, 36, 12)
        zsurf = pygame.Surface((int(80 * scale), int(160 * scale)), pygame.SRCALPHA)
        sw, sh = zsurf.get_size()
        cx = sw // 2
        bob = int(math.sin(t) * 4 * scale)

        # Head
        hr = int(14 * scale)
        pygame.draw.ellipse(zsurf, col + (opacity,),
                            (cx - hr, 2 + bob, hr * 2, hr * 2))

        # Body
        body_top = 2 + hr * 2 + bob
        body_h = int(50 * scale)
        pygame.draw.rect(zsurf, col + (opacity,),
                         (cx - int(12 * scale), body_top,
                          int(24 * scale), body_h))

        # Left arm (raised slightly)
        arm_angle = math.sin(t + 0.5) * 0.3
        al = int(32 * scale)
        arm_end_x = cx - int(12 * scale) - int(al * math.cos(arm_angle + 0.8))
        arm_end_y = body_top + int(al * math.sin(arm_angle + 0.8))
        pygame.draw.line(zsurf, col + (opacity,),
                         (cx - int(12 * scale), body_top + 5),
                         (arm_end_x, arm_end_y), max(1, int(6 * scale)))

        # Right arm (outstretched)
        arm_end_x2 = cx + int(12 * scale) + int(al * math.cos(-arm_angle + 0.4))
        arm_end_y2 = body_top - int(8 * scale) + int(al * math.sin(-arm_angle + 0.4))
        pygame.draw.line(zsurf, col + (opacity,),
                         (cx + int(12 * scale), body_top + 5),
                         (arm_end_x2, arm_end_y2), max(1, int(6 * scale)))

        # Legs
        leg_top = body_top + body_h
        ll = int(48 * scale)
        leg1_x = cx - int(7 * scale) + int(math.sin(t) * 8 * scale)
        leg2_x = cx + int(7 * scale) - int(math.sin(t) * 8 * scale)
        pygame.draw.line(zsurf, col + (opacity,),
                         (cx - int(7 * scale), leg_top),
                         (leg1_x, leg_top + ll), max(1, int(7 * scale)))
        pygame.draw.line(zsurf, col + (opacity,),
                         (cx + int(7 * scale), leg_top),
                         (leg2_x, leg_top + ll), max(1, int(7 * scale)))

        surface.blit(zsurf, (x - sw // 2, y - sh))

    # ------------------------------------------------------------------
    def draw(self, surface):
        # 1. Dark base
        surface.fill((10, 14, 6))

        # 2. Cracked wall texture
        surface.blit(self.wall_surf, (0, 0))

        # 3. Fog puffs
        fog_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for p in self.fog_puffs:
            life_ratio = max(0.0, p['life'] / p['max_life'])
            a = int(p['alpha'] * life_ratio)
            pygame.draw.circle(fog_surf, (60, 90, 20, a),
                               (int(p['x']), int(p['y'])), p['r'])
        surface.blit(fog_surf, (0, 0))

        # 4. Zombie silhouettes
        for z in self.zombies:
            self._draw_zombie(surface, int(z['x']), z['y'],
                               z['scale'], z['opacity'], z['t'])

        # 5. Flickering light blobs (upper-left bias)
        for (lx, ly), la in zip(self.light_positions, self.light_alphas):
            lsurf = pygame.Surface((400, 400), pygame.SRCALPHA)
            pygame.draw.circle(lsurf, (80, 120, 30, la), (200, 200), 200)
            surface.blit(lsurf, (lx - 200, ly - 200))

        # 6. Vignette
        surface.blit(self.vignette, (0, 0))

        # Corner ornaments
        corners = [
            (24, 24),
            (WIDTH - 24, 24),
            (24, HEIGHT - 24),
            (WIDTH - 24, HEIGHT - 24),
        ]
        dirs = [(1, 1), (-1, 1), (1, -1), (-1, -1)]
        for (cx, cy), (dx, dy) in zip(corners, dirs):
            pygame.draw.line(surface, (60, 95, 22),
                             (cx, cy), (cx + dx * 40, cy), 2)
            pygame.draw.line(surface, (60, 95, 22),
                             (cx, cy), (cx, cy + dy * 40), 2)


# ── Horror-themed menu button layout (480×72, centred column from y=400) ──
menu_buttons = [
    Button((WIDTH//2 - 240, 400, 480, 72), "START"),
    Button((WIDTH//2 - 240, 495, 480, 72), "Options"),
    Button((WIDTH//2 - 240, 590, 480, 72), "How To Play"),
    Button((WIDTH//2 - 240, 685, 480, 72), "Credits"),
    Button((WIDTH//2 - 240, 780, 480, 72), "High Scores"),
    Button((WIDTH//2 - 240, 875, 480, 72), "Quit"),
]

howto_back_button      = Button((WIDTH//2 - 200, 880, 400, 64), "BACK")

options_back_button    = Button((WIDTH//2 - 200, 820, 400, 64), "BACK")
credits_back_button    = Button((WIDTH//2 - 200, 860, 400, 64), "BACK")
highscores_back_button = Button((WIDTH//2 - 200, 750, 400, 64), "BACK")

# Animated menu background instance
menu_bg = MenuBackground()

pause_buttons = [
    Button((760, 520, 400, 78), "RESUME"),
    Button((760, 620, 400, 78), "MAIN MENU"),
]

end_buttons = [
    Button((WIDTH//2 - 200, 690, 400, 64), "PLAY AGAIN"),
    Button((WIDTH//2 - 200, 770, 400, 64), "MAIN MENU"),
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
start_countdown_timer = 0
start_countdown_started = False


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
    pygame.draw.polygon(surface, (10, 16, 7), pts)
    pygame.draw.polygon(surface, (50, 80, 18), pts, 2)

    # Accent strips
    pygame.draw.rect(surface, (22, 38, 10), (px + 20, py + 18, pw - 40, 3))
    pygame.draw.rect(surface, (22, 38, 10), (px + 20, py + ph - 21, pw - 40, 3))

    # Corner L-brackets on the panel
    for cx2, cy2, dx2, dy2 in [
        (px + 14, py + 14, 1, 1), (px + pw - 14, py + 14, -1, 1),
        (px + 14, py + ph - 14, 1, -1), (px + pw - 14, py + ph - 14, -1, -1),
    ]:
        pygame.draw.line(surface, (80, 130, 30),
                         (cx2, cy2), (cx2 + dx2 * 26, cy2), 2)
        pygame.draw.line(surface, (80, 130, 30),
                         (cx2, cy2), (cx2, cy2 + dy2 * 26), 2)

    # Title glow passes
    for ox, oy in [(-2, -2), (2, -2), (-2, 2), (2, 2)]:
        gs = heading_font.render(title_text, True, (40, 80, 10))
        gs.set_alpha(50)
        surface.blit(gs, gs.get_rect(center=(WIDTH // 2 + ox, title_y + oy)))
    draw_text(surface, title_text, heading_font,
              (10, 22, 5), (WIDTH // 2 + 4, title_y + 5))
    draw_text(surface, title_text, heading_font,
              (139, 195, 74), (WIDTH // 2, title_y))

    # Horizontal rule + drips under title
    rule_y = title_y + 52
    pygame.draw.line(surface, (50, 80, 18),
                     (px + 60, rule_y), (px + pw - 60, rule_y), 1)
    import random as _rnd2
    _rnd2.seed(hash(title_text) & 0xFFFF)
    for _ in range(6):
        drip_x = WIDTH // 2 + _rnd2.randint(-200, 200)
        drip_h = _rnd2.randint(8, 22)
        pygame.draw.rect(surface, (30, 55, 10), (drip_x, rule_y, 2, drip_h))
    _rnd2.seed()


def draw_panel(surface, heading, lines, buttons, mouse_pos):
    _horror_screen_base(surface, heading)

    for i, line in enumerate(lines):
        draw_text(
            surface, line, ui_font, (175, 215, 130),
            (WIDTH // 2, 345 + i * 56)
        )

    for button in buttons:
        button.draw(surface, mouse_pos)


def draw_menu(surface, mouse_pos):
    # -- Animated horror background --
    menu_bg.draw(surface)

    # -- Title glow (approximate: render offsets in dim colour) --
    for ox, oy in [(-3,-3),(3,-3),(-3,3),(3,3),(-5,0),(5,0),(0,-5),(0,5)]:
        glow_s = title_font.render("DEADLAST", True, (50, 90, 15))
        glow_s.set_alpha(40)
        gr = glow_s.get_rect(center=(WIDTH // 2 + ox, 220 + oy))
        surface.blit(glow_s, gr)

    # -- Title shadow --
    draw_text(surface, "DEADLAST", title_font,
              (14, 30, 6), (WIDTH // 2 + 6, 220 + 8))

    # -- Title --
    draw_text(surface, "DEADLAST", title_font,
              (139, 195, 74), (WIDTH // 2, 220))

    # -- Subtitle --
    draw_text(surface, "THE LAST OUTBREAK", ui_font,
              (100, 140, 60), (WIDTH // 2, 305))

    # -- Title drips --
    import random as _rnd
    _rnd.seed(42)  # deterministic drips
    drip_xs = [WIDTH // 2 + _rnd.randint(-200, 200) for _ in range(10)]
    drip_hs = [_rnd.randint(12, 28) for _ in range(10)]
    _rnd.seed()    # restore randomness
    for dx, dh in zip(drip_xs, drip_hs):
        pygame.draw.rect(surface, (30, 55, 10), (dx, 330, 2, dh))

    # -- Buttons --
    for button in menu_buttons:
        button.draw(surface, mouse_pos)

def draw_howto(surface, mouse_pos):
    draw_panel(surface, "HOW TO PLAY", [
        "Move .............. WASD or ARROW KEYS",
        "Aim and Shoot ..... MOUSE CLICK",
        "Pistol ............ 1  (unlimited ammo)",
        "Rifle ............. 2  (unlocks Wave 2)",
        "Shotgun ........... 3  (unlocks Wave 3)",
        "Drops ............. Health / Ammo / Rapid Fire",
        "Bosses ............ every 5th wave",
        "Goal .............. survive all 10 waves",
        "Pause ............. ESC or P",
    ], [howto_back_button], mouse_pos)


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
    music_slider.draw(surface, mouse_pos, "")

    # Section label: SFX
    draw_text(surface, "SFX VOLUME", ui_font,
              (100, 155, 50), (WIDTH // 2, 490))
    sfx_slider.draw(surface, mouse_pos, "")

    # Separator
    pygame.draw.line(surface, (50, 80, 18),
                     (WIDTH // 2 - 300, 630), (WIDTH // 2 + 300, 630), 1)

    # Fullscreen toggle
    fs_text = "FULLSCREEN: ON" if fullscreen else "FULLSCREEN: OFF"
    fs_col = (139, 195, 74) if fullscreen else (155, 155, 100)
    draw_text(surface, fs_text, ui_font, fs_col, (WIDTH // 2, 660))
    draw_text(surface, "press F11 to toggle", small_font,
              (80, 110, 40), (WIDTH // 2, 700))

    options_back_button.draw(surface, mouse_pos)


def draw_credits(surface, mouse_pos):
    _horror_screen_base(surface, "CREDITS")

    credit_rows = [
        ("DEADLAST", (139, 195, 74), ui_font),
        ("A zombie survival game", (100, 140, 60), small_font),
        ("", None, small_font),
        ("Programming & Design", (130, 175, 80), ui_font),
        ("Micah Madrigal", (175, 215, 130), small_font),
        ("Engine: Pygame", (80, 110, 50), small_font),
        ("", None, small_font),
        ("Music", (130, 175, 80), ui_font),
        ("menu_music.mp3  |  gameplay_music.mp3", (175, 215, 130), small_font),
        ("", None, small_font),
        ("Sound Effects", (130, 175, 80), ui_font),
        ("Gunshot  |  player_hurt  |  ui_click", (175, 215, 130), small_font),
        ("victory  |  zombie_death  |  game_over", (175, 215, 130), small_font),
        ("", None, small_font),
        ("Thank you for playing!", (220, 240, 160), ui_font),
    ]

    y = 308
    for text, col, fnt in credit_rows:
        if text and col:
            draw_text(surface, text, fnt, col, (WIDTH // 2, y))
        y += 38

    credits_back_button.draw(surface, mouse_pos)


def draw_highscores(surface, mouse_pos):
    _horror_screen_base(surface, "HIGH SCORES")

    # Load best score
    try:
        saved = HIGH_SCORE_FILE.read_text(encoding="utf-8").strip()
        score_text = saved if saved else "0"
    except OSError:
        score_text = "0"

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
                music_slider.handle_event(event, pos)
                sfx_slider.handle_event(event, pos)
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
                pos = window_to_canvas(
                    event.pos,
                    window.get_size()
                )
                music_slider.handle_event(event, pos)
                sfx_slider.handle_event(event, pos)
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
                pos = window_to_canvas(
                    event.pos,
                    window.get_size()
                )
                music_slider.handle_event(event, pos)
                sfx_slider.handle_event(event, pos)

    # ========================================================
    # GAMEPLAY UPDATE
    # ========================================================
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
            move_player(
                direction.x * PLAYER_SPEED * dt,
                direction.y * PLAYER_SPEED * dt
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

    elif state in ("playing", "paused", "countdown"):
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

        if state == "countdown":
            draw_start_countdown(screen)

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
    # Fill the entire window, stretching the canvas to fit its aspect ratio.
    frame = pygame.transform.smoothscale(screen, window.get_size())
    window.blit(frame, (0, 0))
    pygame.display.flip()

pygame.quit()
sys.exit()