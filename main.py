import pygame
import math

# Initialize pygame
pygame.init()

WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Mouse Aiming")
clock = pygame.time.Clock()

# Colors
GREEN = (0, 255, 0)
WHITE = (255, 255, 255)


class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()

        # Create a simple ship/tank body
        self.original_image = pygame.Surface((60, 40), pygame.SRCALPHA)
        pygame.draw.rect(self.original_image, GREEN, (0, 0, 60, 40))

        # Front indicator
        pygame.draw.rect(self.original_image, (0, 200, 0), (45, 10, 15, 20))

        self.image = self.original_image.copy()
        self.rect = self.image.get_rect(center=(WIDTH // 2, HEIGHT // 2))

    def update(self):
        mouse_x, mouse_y = pygame.mouse.get_pos()

        dx = mouse_x - self.rect.centerx
        dy = mouse_y - self.rect.centery

        # Calculate angle toward mouse
        angle = -math.degrees(math.atan2(dy, dx))

        old_center = self.rect.center

        self.image = pygame.transform.rotate(
            self.original_image,
            angle
        )

        self.rect = self.image.get_rect(center=old_center)


# Sprite setup
all_sprites = pygame.sprite.Group()
player = Player()
all_sprites.add(player)

running = True

while running:
    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Update
    all_sprites.update()

    # Draw
    screen.fill(WHITE)
    all_sprites.draw(screen)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
