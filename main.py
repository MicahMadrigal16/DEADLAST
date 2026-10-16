
import pygame
import sys

pygame.init()

WIDTH = 900
HEIGHT = 600

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("DEADLAST")

clock = pygame.time.Clock()

BLACK = (15, 15, 20)
WHITE = (240, 240, 240)

running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.fill(BLACK)

    font = pygame.font.Font(None, 64)
    title = font.render("DEADLAST", True, WHITE)
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 250))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
