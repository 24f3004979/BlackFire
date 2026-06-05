import pygame
import math
import random
import os

# Initialize pygame
pygame.init()

# Constants
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
MAP_SIZE = 2000 # Map is MAP_SIZE x MAP_SIZE
TILE_SIZE = 100
FPS = 60

# Colors & Biomes
COLOR_WATER = (30, 80, 160)
COLOR_GRASS = (50, 120, 50)
COLOR_FOREST = (20, 80, 20)
COLOR_ROCK = (100, 100, 110)
COLOR_RIVER_EDGE = (100, 150, 220)
COLOR_HOLE = (10, 10, 15) # Dark abyss

# Game Colors
BULLET_COLOR = (255, 220, 100)
BLOOD_COLOR = (140, 20, 20)
UI_ACCENT = (255, 100, 50)
WHITE = (255, 255, 255)

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("GODFIRE: Forest Survival")
clock = pygame.time.Clock()
font_sm = pygame.font.SysFont("Arial", 18, bold=True)
font_md = pygame.font.SysFont("Arial", 28, bold=True)
font_lg = pygame.font.SysFont("Arial", 64, bold=True)

# --- Asset Management ---

class AssetManager:
    def __init__(self):
        self.images = {}
        self.sounds = {}
        self.placeholder_colors = {
            "player": (70, 90, 70),
            "zombie": (90, 70, 70),
            "ranged": (70, 70, 120),
            "boss": (150, 30, 30),
            "bullet": (255, 220, 50),
            "resource_ammo": (50, 150, 50),
            "resource_upgrade": (200, 200, 50),
            "shield": (100, 200, 255, 150)
        }

    def get_image(self, name, size=(80, 80)):
        if name not in self.images:
            path = os.path.join("assets/images", f"{name}.png")
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    self.images[name] = pygame.transform.scale(img, size)
                except:
                    self.images[name] = self._create_placeholder(name, size)
            else:
                self.images[name] = self._create_placeholder(name, size)
        return self.images[name]

    def _create_placeholder(self, name, size):
        surf = pygame.Surface(size, pygame.SRCALPHA)
        color = self.placeholder_colors.get(name, (200, 200, 200))
        if len(color) == 4: # RGBA
            pygame.draw.circle(surf, color, (size[0]//2, size[1]//2), size[0]//2)
        else:
            pygame.draw.circle(surf, color, (size[0]//2, size[1]//2), size[0]//2)
            pygame.draw.circle(surf, (30, 30, 30), (size[0]//2, size[1]//2), size[0]//4) # "Head"
        return surf

    def play_sound(self, name):
        if name not in self.sounds:
            path = os.path.join("assets/sounds", f"{name}.wav")
            if os.path.exists(path):
                try:
                    self.sounds[name] = pygame.mixer.Sound(path)
                except:
                    self.sounds[name] = None
            else:
                self.sounds[name] = None
        
        if self.sounds[name]:
            self.sounds[name].play()

assets = AssetManager()

# --- Procedural Map Generation ---

class TerrainGenerator:
    def __init__(self, size):
        self.size = size
        self.grid_size = size // TILE_SIZE
        self.noise_grid = []
        self.seed_x = random.uniform(0, 1000)
        self.seed_y = random.uniform(0, 1000)
        self.generate()

    def _noise(self, x, y):
        # Simulated organic noise using layered sine waves
        val = math.sin(x * 0.1 + self.seed_x) * math.cos(y * 0.1 + self.seed_y)
        val += 0.5 * math.sin(x * 0.3 + self.seed_x * 0.5) * math.cos(y * 0.3 + self.seed_y * 0.5)
        val += 0.25 * math.sin(x * 0.7) * math.sin(y * 0.7)
        return (val + 1.75) / 3.5 # Normalize to 0-1 range roughly

    def generate(self):
        self.noise_grid = []
        for y in range(self.grid_size):
            row = []
            for x in range(self.grid_size):
                row.append(self._noise(x, y))
            self.noise_grid.append(row)

    def get_type(self, x, y):
        gx = int(x // TILE_SIZE)
        gy = int(y // TILE_SIZE)
        if 0 <= gx < self.grid_size and 0 <= gy < self.grid_size:
            n = self.noise_grid[gy][gx]
            if n < 0.15: return "HOLE"
            if n < 0.25: return "WATER"
            if n < 0.30: return "RIVER_EDGE"
            if n < 0.70: return "GRASS"
            if n < 0.85: return "FOREST"
            return "ROCK"
        return "ROCK"

# --- Helper Systems ---

class Camera:
    def __init__(self):
        self.offset = pygame.math.Vector2(0, 0)
        self.shake_amount = 0
        self.shake_timer = 0
        self.shake_offset = pygame.math.Vector2(0, 0)

    def shake(self, amount, duration):
        self.shake_amount = amount
        self.shake_timer = duration

    def update(self, target_pos, dt):
        target_offset = target_pos - pygame.math.Vector2(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        self.offset += (target_offset - self.offset) * 0.1
        self.offset.x = max(0, min(MAP_SIZE - SCREEN_WIDTH, self.offset.x))
        self.offset.y = max(0, min(MAP_SIZE - SCREEN_HEIGHT, self.offset.y))

        if self.shake_timer > 0:
            self.shake_timer -= dt
            self.shake_offset = pygame.math.Vector2(random.uniform(-self.shake_amount, self.shake_amount), random.uniform(-self.shake_amount, self.shake_amount))
        else:
            self.shake_offset.update(0, 0)

    def apply(self, pos):
        return pos - self.offset + self.shake_offset

class ParticleManager:
    def __init__(self):
        self.particles = []

    def emit(self, pos, color, speed_range=(2, 5), size_range=(2, 6), life_range=(0.5, 1.0), count=1):
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(*speed_range)
            self.particles.append({
                "pos": pygame.math.Vector2(pos),
                "vel": pygame.math.Vector2(math.cos(angle), math.sin(angle)) * speed,
                "color": color,
                "size": random.uniform(*size_range),
                "life": random.uniform(*life_range),
                "total_life": 0
            })

    def update(self, dt):
        for p in self.particles[:]:
            p["pos"] += p["vel"]
            p["vel"] *= 0.95
            p["total_life"] += dt
            if p["total_life"] >= p["life"]: self.particles.remove(p)

    def draw(self, surface, camera):
        for p in self.particles:
            alpha = int(255 * (1 - p["total_life"] / p["life"]))
            draw_pos = camera.apply(p["pos"])
            s = pygame.Surface((p["size"]*2, p["size"]*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*p["color"][:3], alpha), (p["size"], p["size"]), p["size"])
            surface.blit(s, (draw_pos.x - p["size"], draw_pos.y - p["size"]))

class FloatingText:
    def __init__(self, pos, text, color):
        self.pos = pygame.math.Vector2(pos)
        self.text = text
        self.color = color
        self.life = 1.0
        self.total_life = 0

    def update(self, dt):
        self.pos.y -= 2
        self.total_life += dt
        return self.total_life < self.life

    def draw(self, surface, camera):
        alpha = int(255 * (1 - self.total_life / self.life))
        txt_surf = font_sm.render(self.text, True, self.color)
        txt_surf.set_alpha(alpha)
        surface.blit(txt_surf, camera.apply(self.pos))

# --- Entities ---

class Bullet(pygame.sprite.Sprite):
    def __init__(self, pos, angle, is_enemy=False):
        super().__init__()
        self.pos = pygame.math.Vector2(pos)
        rad = math.radians(-angle)
        self.vel = pygame.math.Vector2(math.cos(rad), math.sin(rad)) * 12
        self.is_enemy = is_enemy
        self.image = assets.get_image("bullet", (24, 24))
        self.rect = self.image.get_rect(center=self.pos)

    def update(self, dt, terrain):
        self.pos += self.vel * dt * 60
        self.rect.center = self.pos
        t_type = terrain.get_type(self.pos.x, self.pos.y)
        if t_type in ["FOREST", "ROCK"]: return "hit_solid"
        if not (0 <= self.pos.x <= MAP_SIZE and 0 <= self.pos.y <= MAP_SIZE): return "kill"
        return None

class Resource(pygame.sprite.Sprite):
    def __init__(self, pos, r_type):
        super().__init__()
        self.pos = pygame.math.Vector2(pos)
        self.r_type = r_type # "ammo" or "upgrade"
        self.image = assets.get_image(f"resource_{r_type}", (30, 30))
        self.rect = self.image.get_rect(center=self.pos)

class GlooWall(pygame.sprite.Sprite):
    def __init__(self, pos, angle):
        super().__init__()
        self.pos = pygame.math.Vector2(pos)
        self.base_image = assets.get_image("shield", (120, 30))
        self.image = pygame.transform.rotate(self.base_image, angle)
        self.rect = self.image.get_rect(center=self.pos)
        self.health = 100
        self.life = 10.0 # seconds

    def update(self, dt):
        self.life -= dt
        return self.life > 0 and self.health > 0

class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.pos = pygame.math.Vector2(MAP_SIZE // 2, MAP_SIZE // 2)
        self.size = (100, 100)
        self.image = assets.get_image("player", self.size)
        self.rect = self.image.get_rect(center=self.pos)
        self.speed = 6
        self.health = 100
        self.ammo = 50
        self.upgrades = 0
        self.dash_cooldown = 0
        self.shield_cooldown = 0
        self.shoot_timer = 0
        self.is_dashing = False
        self.dash_timer = 0
        self.falling = False
        self.scale = 1.0

    def move(self, dx, dy, terrain):
        if self.falling: return
        t_type = terrain.get_type(self.pos.x + dx, self.pos.y + dy)
        
        # Gravity/Hole Check
        if t_type == "HOLE" and not self.is_dashing:
            self.falling = True
            return

        speed_mult = 0.5 if t_type == "WATER" else 1.0
        if t_type not in ["FOREST", "ROCK"]:
            self.pos.x += dx * speed_mult
            self.pos.y += dy * speed_mult
        
        self.pos.x = max(50, min(MAP_SIZE - 50, self.pos.x))
        self.pos.y = max(50, min(MAP_SIZE - 50, self.pos.y))
        self.rect.center = self.pos

    def update(self, dt, keys, mouse_world_pos, terrain):
        if self.falling:
            self.scale -= 2 * dt
            if self.scale <= 0.1:
                self.health = 0
                return None
            self.image = pygame.transform.rotozoom(assets.get_image("player", self.size), 0, self.scale)
            self.rect = self.image.get_rect(center=self.pos)
            return None

        if self.dash_cooldown > 0: self.dash_cooldown -= dt
        if self.shield_cooldown > 0: self.shield_cooldown -= dt
        if self.shoot_timer > 0: self.shoot_timer -= dt

        # Dash
        if keys[pygame.K_SPACE] and self.dash_cooldown <= 0:
            self.is_dashing = True
            self.dash_timer = 0.25
            self.dash_cooldown = 1.5
            move_vec = pygame.math.Vector2(0, 0)
            if keys[pygame.K_w]: move_vec.y -= 1
            if keys[pygame.K_s]: move_vec.y += 1
            if keys[pygame.K_a]: move_vec.x -= 1
            if keys[pygame.K_d]: move_vec.x += 1
            self.dash_dir = move_vec.normalize() if move_vec.length() > 0 else (mouse_world_pos - self.pos).normalize()

        if self.is_dashing:
            self.move(self.dash_dir.x * 20, self.dash_dir.y * 20, terrain)
            self.dash_timer -= dt
            if self.dash_timer <= 0: self.is_dashing = False
        else:
            dx, dy = 0, 0
            if keys[pygame.K_w]: dy -= self.speed
            if keys[pygame.K_s]: dy += self.speed
            if keys[pygame.K_a]: dx -= self.speed
            if keys[pygame.K_d]: dx += self.speed
            if dx != 0 and dy != 0: dx *= 0.707; dy *= 0.707
            self.move(dx, dy, terrain)

        # Gloo Wall
        if keys[pygame.K_e] and self.shield_cooldown <= 0:
            self.shield_cooldown = 4.0
            angle = -math.degrees(math.atan2(mouse_world_pos.y - self.pos.y, mouse_world_pos.x - self.pos.x))
            dist = 80
            rad = math.radians(-angle)
            wall_pos = self.pos + pygame.math.Vector2(math.cos(rad), math.sin(rad)) * dist
            assets.play_sound("shield")
            return GlooWall(wall_pos, angle)

        # Rotation
        angle = -math.degrees(math.atan2(mouse_world_pos.y - self.pos.y, mouse_world_pos.x - self.pos.x))
        self.image = pygame.transform.rotate(assets.get_image("player", self.size), angle)
        self.rect = self.image.get_rect(center=self.pos)
        return None

class Enemy(pygame.sprite.Sprite):
    def __init__(self, pos, e_type="zombie"):
        super().__init__()
        self.pos = pygame.math.Vector2(pos)
        self.e_type = e_type
        self.size = (150, 150) if e_type == "boss" else (90, 90)
        self.image = assets.get_image(e_type, self.size)
        self.rect = self.image.get_rect(center=self.pos)
        self.speed = random.uniform(1.5, 3.0)
        self.health = 4 if e_type == "zombie" else (8 if e_type == "ranged" else 100)
        self.shoot_timer = random.uniform(1.0, 4.0)
        self.falling = False
        self.scale = 1.0

    def update(self, dt, player_pos, terrain, walls):
        if self.falling:
            self.scale -= 2 * dt
            if self.scale <= 0.1:
                self.kill()
            self.image = pygame.transform.rotozoom(assets.get_image(self.e_type, self.size), 0, self.scale)
            self.rect = self.image.get_rect(center=self.pos)
            return None

        dir_vec = (player_pos - self.pos)
        dist = dir_vec.length()
        
        if dist > 0:
            dir_vec = dir_vec.normalize()
            if self.e_type == "ranged" and dist < 350:
                move_dir = -dir_vec
            elif self.e_type == "ranged" and dist > 450:
                move_dir = dir_vec
            elif self.e_type == "ranged":
                move_dir = pygame.math.Vector2(0,0)
            else:
                move_dir = dir_vec
            
            target_pos = self.pos + move_dir * self.speed
            t_type = terrain.get_type(target_pos.x, target_pos.y)
            
            if t_type == "HOLE":
                self.falling = True
            elif t_type not in ["FOREST", "ROCK"]:
                self.pos = target_pos
        
        self.rect.center = self.pos
        angle = -math.degrees(math.atan2(player_pos.y - self.pos.y, player_pos.x - self.pos.x))
        self.image = pygame.transform.rotate(assets.get_image(self.e_type, self.size), angle)
        
        # Enemy Shooting
        self.shoot_timer -= dt
        if self.shoot_timer <= 0:
            if self.e_type == "zombie":
                self.shoot_timer = random.uniform(3.0, 6.0)
                return Bullet(self.pos, angle, is_enemy=True)
            elif self.e_type == "ranged":
                self.shoot_timer = 1.5
                return Bullet(self.pos, angle, is_enemy=True)
            elif self.e_type == "boss":
                self.shoot_timer = 0.4
                # Rapid fire for boss
                return Bullet(self.pos, angle + random.uniform(-10, 10), is_enemy=True)
        return None

# --- Main Game Loop ---

def main():
    terrain = TerrainGenerator(MAP_SIZE)
    camera = Camera()
    particles = ParticleManager()
    floating_texts = []
    
    player = Player()
    all_sprites = pygame.sprite.Group()
    bullets = pygame.sprite.Group()
    enemy_bullets = pygame.sprite.Group()
    enemies = pygame.sprite.Group()
    resources = pygame.sprite.Group()
    walls = pygame.sprite.Group()
    
    all_sprites.add(player)
    
    state = "MENU"
    score = 0
    spawn_timer = 0
    level = 1

    # Initial Resources
    for _ in range(10):
        r_pos = pygame.math.Vector2(random.randint(100, MAP_SIZE-100), random.randint(100, MAP_SIZE-100))
        if terrain.get_type(r_pos.x, r_pos.y) == "GRASS":
            res = Resource(r_pos, random.choice(["ammo", "upgrade"]))
            resources.add(res)

    while True:
        dt = clock.tick(FPS) / 1000.0
        mouse_world_pos = pygame.math.Vector2(pygame.mouse.get_pos()) + camera.offset
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); return
            if event.type == pygame.KEYDOWN:
                if state == "MENU" and event.key == pygame.K_SPACE: state = "PLAYING"
                if state == "GAME_OVER" and event.key == pygame.K_r: main(); return

        if state == "PLAYING":
            keys = pygame.key.get_pressed()
            
            # Player Actions
            wall = player.update(dt, keys, mouse_world_pos, terrain)
            if wall: walls.add(wall)
            
            if pygame.mouse.get_pressed()[0] and player.shoot_timer <= 0 and player.ammo > 0:
                player.shoot_timer = 0.2 - (player.upgrades * 0.02)
                player.ammo -= 1
                angle = -math.degrees(math.atan2(mouse_world_pos.y - player.pos.y, mouse_world_pos.x - player.pos.x))
                b = Bullet(player.pos, angle)
                bullets.add(b)
                camera.shake(3, 0.1)
                assets.play_sound("shoot")

            # Updates
            camera.update(player.pos, dt)
            particles.update(dt)
            
            for b in bullets:
                res = b.update(dt, terrain)
                if res == "hit_solid": b.kill(); particles.emit(b.pos, COLOR_ROCK, count=3)
                elif res == "kill": b.kill()

            for eb in enemy_bullets:
                res = eb.update(dt, terrain)
                if res == "hit_solid": eb.kill()
                elif res == "kill": eb.kill()

            # Enemy Spawning
            spawn_timer += dt
            if spawn_timer > max(0.4, 1.8 - level * 0.1):
                spawn_timer = 0
                angle = random.uniform(0, math.pi*2)
                sp_pos = player.pos + pygame.math.Vector2(math.cos(angle), math.sin(angle)) * 700
                if 0 < sp_pos.x < MAP_SIZE and 0 < sp_pos.y < MAP_SIZE:
                    e_type = "zombie"
                    # Higher probability for ranged and bosses
                    rand_val = random.random()
                    if level > 1 and rand_val < 0.4: e_type = "ranged"
                    if score > 500 and rand_val < 0.15: e_type = "boss" # Lower threshold and higher probability
                    e = Enemy(sp_pos, e_type)
                    enemies.add(e)

            for e in enemies:
                eb = e.update(dt, player.pos, terrain, walls)
                if eb: enemy_bullets.add(eb)

            for w in list(walls):
                if not w.update(dt): walls.remove(w)

            # Collisions
            # Bullets vs Enemies
            hits = pygame.sprite.groupcollide(enemies, bullets, False, True)
            for e, blist in hits.items():
                e.health -= len(blist)
                particles.emit(e.pos, BLOOD_COLOR, count=5)
                if e.health <= 0:
                    e.kill()
                    score += 100 if e.e_type != "boss" else 1000
                    floating_texts.append(FloatingText(e.pos, "+Score", UI_ACCENT))
                    assets.play_sound("death")
            
            # Enemy Bullets vs Player/Walls
            p_hit = pygame.sprite.spritecollide(player, enemy_bullets, True)
            if p_hit and not player.is_dashing:
                player.health -= 10 * len(p_hit)
                camera.shake(10, 0.2)
                if player.health <= 0: state = "GAME_OVER"

            wall_hits = pygame.sprite.groupcollide(walls, enemy_bullets, False, True)
            for w, blist in wall_hits.items():
                w.health -= 10 * len(blist)

            # Player vs Enemies (Melee)
            if not player.is_dashing:
                m_hits = pygame.sprite.spritecollide(player, enemies, True)
                if m_hits:
                    player.health -= 20 * len(m_hits)
                    camera.shake(15, 0.3)
                    if player.health <= 0: state = "GAME_OVER"
            else:
                d_hits = pygame.sprite.spritecollide(player, enemies, True)
                for de in d_hits:
                    score += 200
                    particles.emit(de.pos, BLOOD_COLOR, count=15)

            # Resource Collection
            res_hits = pygame.sprite.spritecollide(player, resources, True)
            for r in res_hits:
                if r.r_type == "ammo": player.ammo += 20
                else: player.upgrades += 1
                assets.play_sound("pickup")

            floating_texts = [ft for ft in floating_texts if ft.update(dt)]
            if score > level * 2000: level += 1

        # --- Draw ---
        BG_COLOR = (0,0,0)
        screen.fill(BG_COLOR)
        
        # Terrain Rendering (Tiles in view)
        view_x = int(camera.offset.x // TILE_SIZE)
        view_y = int(camera.offset.y // TILE_SIZE)
        for gy in range(view_y, view_y + (SCREEN_HEIGHT // TILE_SIZE) + 2):
            for gx in range(view_x, view_x + (SCREEN_WIDTH // TILE_SIZE) + 2):
                if 0 <= gx < terrain.grid_size and 0 <= gy < terrain.grid_size:
                    rect = pygame.Rect(gx * TILE_SIZE - camera.offset.x, gy * TILE_SIZE - camera.offset.y, TILE_SIZE, TILE_SIZE)
                    t_type = terrain.get_type(gx * TILE_SIZE, gy * TILE_SIZE)
                    color = COLOR_GRASS
                    if t_type == "HOLE": color = COLOR_HOLE
                    elif t_type == "WATER": color = COLOR_WATER
                    elif t_type == "RIVER_EDGE": color = COLOR_RIVER_EDGE
                    elif t_type == "FOREST": color = COLOR_FOREST
                    elif t_type == "ROCK": color = COLOR_ROCK
                    pygame.draw.rect(screen, color, rect)

        # Entities
        for r in resources: screen.blit(r.image, camera.apply(r.pos - pygame.math.Vector2(15, 15)))
        for w in walls: screen.blit(w.image, camera.apply(pygame.math.Vector2(w.rect.topleft)))
        for b in bullets: screen.blit(b.image, camera.apply(b.pos - pygame.math.Vector2(12, 12)))
        for eb in enemy_bullets: screen.blit(eb.image, camera.apply(eb.pos - pygame.math.Vector2(12, 12)))
        for e in enemies: screen.blit(e.image, camera.apply(e.pos - pygame.math.Vector2(e.rect.width//2, e.rect.height//2)))
        
        particles.draw(screen, camera)
        screen.blit(player.image, camera.apply(player.pos - pygame.math.Vector2(50, 50)))
        for ft in floating_texts: ft.draw(screen, camera)

        # HUD
        if state != "MENU":
            pygame.draw.rect(screen, (50, 0, 0), (20, 20, 200, 20))
            pygame.draw.rect(screen, (200, 50, 50), (20, 20, player.health * 2, 20))
            ammo_surf = font_md.render(f"AMMO: {player.ammo}", True, WHITE)
            score_surf = font_md.render(f"SCORE: {score}", True, UI_ACCENT)
            screen.blit(ammo_surf, (20, 50))
            screen.blit(score_surf, (20, 85))
            if player.shield_cooldown > 0:
                s_txt = font_sm.render(f"SHIELD COOLDOWN: {int(player.shield_cooldown)}s", True, (100, 200, 255))
                screen.blit(s_txt, (20, 120))

        if state == "MENU":
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 200))
            screen.blit(overlay, (0, 0))
            title = font_lg.render("GODFIRE: FOREST", True, UI_ACCENT)
            subtitle = font_md.render("Press SPACE to Survival", True, WHITE)
            instr = font_sm.render("WASD: Move | SPACE: Dash | E: Gloo Wall | MOUSE: Shoot", True, (180, 180, 180))
            screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 200))
            screen.blit(subtitle, (SCREEN_WIDTH//2 - subtitle.get_width()//2, 300))
            screen.blit(instr, (SCREEN_WIDTH//2 - instr.get_width()//2, 450))

        if state == "GAME_OVER":
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((100, 0, 0, 150))
            screen.blit(overlay, (0, 0))
            go_txt = font_lg.render("DEFEATED", True, WHITE)
            screen.blit(go_txt, (SCREEN_WIDTH//2 - go_txt.get_width()//2, 250))

        pygame.display.flip()

if __name__ == "__main__":
    main()
