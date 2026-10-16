
import pygame
import random
import sys

pygame.init()

# Window settings
WIDTH = 900
HEIGHT = 600

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("DEADLAST")

clock = pygame.time.Clock()
FPS = 60

# Colors
BLACK = (15, 15, 20)
WHITE = (240, 240, 240)
GREEN = (70, 220, 100)
RED = (230, 65, 65)
GRAY = (45, 45, 55)
YELLOW = (255, 220, 80)

# Fonts
title_font = pygame.font.Font(None, 64)
ui_font = pygame.font.Font(None, 32)
message_font = pygame.font.Font(None, 44)

# Game settings
PLAYER_SIZE = 30
PLAYER_SPEED = 5
ENEMY_SIZE = 25
ENEMY_SPEED = 2
MAX_HEALTH = 100
SURVIVAL_TIME = 30

def reset_game():
    global player, enemies, health, start_time
    global game_state, last_damage_time

    player = pygame.Rect(
        WIDTH // 2 - PLAYER_SIZE // 2,
        HEIGHT // 2 - PLAYER_SIZE // 2,
        PLAYER_SIZE,
        PLAYER_SIZE
    )

    enemies = []
    for _ in range(5):
        spawn_enemy()

    health = MAX_HEALTH
    start_time = pygame.time.get_ticks()
    last_damage_time = 0
    game_state = "playing"


def spawn_enemy():
    # Spawn enemies near the edges of the arena
    side = random.choice(["top", "bottom", "left", "right"])

    if side == "top":
        x = random.randint(0, WIDTH - ENEMY_SIZE)
        y = 0
    elif side == "bottom":
        x = random.randint(0, WIDTH - ENEMY_SIZE)
        y = HEIGHT - ENEMY_SIZE
    elif side == "left":
        x = 0
        y = random.randint(0, HEIGHT - ENEMY_SIZE)
    else:
        x = WIDTH - ENEMY_SIZE
        y = random.randint(0, HEIGHT - ENEMY_SIZE)

    enemies.append(pygame.Rect(x, y, ENEMY_SIZE, ENEMY_SIZE))


def draw_text(text, font, color, x, y, centered=False):
    image = font.render(text, True, color)

    if centered:
        position = image.get_rect(center=(x, y))
        screen.blit(image, position)
    else:
        screen.blit(image, (x, y))


def move_player():
    keys = pygame.key.get_pressed()

    dx = 0
    dy = 0

    if keys[pygame.K_w] or keys[pygame.K_UP]:
        dy -= PLAYER_SPEED
    if keys[pygame.K_s] or keys[pygame.K_DOWN]:
        dy += PLAYER_SPEED
    if keys[pygame.K_a] or keys[pygame.K_LEFT]:
        dx -= PLAYER_SPEED
    if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
        dx += PLAYER_SPEED

    # Normalize diagonal movement so it isn't faster
    if dx != 0 and dy != 0:
        dx *= 0.7071
        dy *= 0.7071

    player.x += round(dx)
    player.y += round(dy)

    # Keep the player inside the arena
    player.clamp_ip(screen.get_rect())


def move_enemies():
    for enemy in enemies:
        dx = player.centerx - enemy.centerx
        dy = player.centery - enemy.centery

        distance = max(1, (dx * dx + dy * dy) ** 0.5)

        enemy.x += round(dx / distance * ENEMY_SPEED)
        enemy.y += round(dy / distance * ENEMY_SPEED)


def draw_health_bar():
    bar_x = 20
    bar_y = 55
    bar_width = 200
    bar_height = 20

    pygame.draw.rect(
        screen, GRAY,
        (bar_x, bar_y, bar_width, bar_height)
    )

    current_width = int(bar_width * max(0, health) / MAX_HEALTH)

    health_color = GREEN if health > 30 else RED

    pygame.draw.rect(
        screen, health_color,
        (bar_x, bar_y, current_width, bar_height)
    )

    pygame.draw.rect(
        screen, WHITE,
        (bar_x, bar_y, bar_width, bar_height), 2
    )

    draw_text(
        f"Health: {max(0, health)}",
        ui_font, WHITE, bar_x, bar_y - 28
    )


def draw_game():
    screen.fill(BLACK)

    # Draw arena border
    pygame.draw.rect(
        screen, GRAY,
        (5, 5, WIDTH - 10, HEIGHT - 10), 3
    )

    # Draw player and enemies
    pygame.draw.rect(screen, GREEN, player, border_radius=6)

    for enemy in enemies:
        pygame.draw.rect(screen, RED, enemy, border_radius=5)

    # Display health and survival time
    draw_health_bar()

    elapsed = (pygame.time.get_ticks() - start_time) // 1000
    remaining = max(0, SURVIVAL_TIME - elapsed)

    draw_text(
        f"Time: {remaining}s",
        ui_font, YELLOW, WIDTH - 130, 20
    )

    draw_text(
        f"Enemies: {len(enemies)}",
        ui_font, WHITE, WIDTH - 160, 55
    )

    return remaining


def draw_end_screen():
    # Dark overlay
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 190))
    screen.blit(overlay, (0, 0))

    if game_state == "won":
        heading = "YOU SURVIVED!"
        heading_color = GREEN
    else:
        heading = "YOU DIED"
        heading_color = RED

    draw_text(
        heading, title_font, heading_color,
        WIDTH // 2, HEIGHT // 2 - 60, centered=True
    )

    draw_text(
        "Press R to restart",
        ui_font, WHITE,
        WIDTH // 2, HEIGHT // 2 + 10, centered=True
    )

    draw_text(
        "Press ESC to quit",
        ui_font, WHITE,
        WIDTH // 2, HEIGHT // 2 + 50, centered=True
    )


# Start a new game
reset_game()

running = True

while running:
    clock.tick(FPS)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if game_state != "playing":
                    running = False

            if event.key == pygame.K_r and game_state != "playing":
                reset_game()

    if game_state == "playing":
        move_player()
        move_enemies()

        # Damage the player when touched, with a short cooldown
        now = pygame.time.get_ticks()

        if now - last_damage_time >= 500:
            for enemy in enemies:
                if player.colliderect(enemy):
                    health -= 10
                    last_damage_time = now
                    break

        remaining = draw_game()

        if health <= 0:
            game_state = "lost"
        elif remaining <= 0:
            game_state = "won"

        # Add more enemies as the game progresses
        elapsed = (pygame.time.get_ticks() - start_time) // 1000

        if elapsed > 0 and elapsed % 5 == 0:
            if len(enemies) < 15 and elapsed != getattr(
                reset_game, "last_spawn_time", -1
            ):
                spawn_enemy()
                reset_game.last_spawn_time = elapsed

    else:
        draw_game()
        draw_end_screen()

    pygame.display.flip()
    

pygame.quit()
sys.exit()
