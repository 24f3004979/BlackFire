import pygame
import math
import random
import os
import csv
import sys

pygame.init()
pygame.mixer.pre_init(44100, -16, 2, 512)

# ── Constants ─────────────────────────────────────────────────────────────────
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
TILE_SIZE = 100
FPS = 60

# Palette
WHITE       = (255, 255, 255)
BLACK       = (0,   0,   0)
UI_ACCENT   = (255, 100,  50)
BLOOD_COLOR = (180,  20,  20)
NEON_CYAN   = (  0, 230, 255)
NEON_ORANGE = (255, 120,  30)
DARK_BG     = ( 10,  10,  18)

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("GODFIRE: Forest Shadows")
clock = pygame.time.Clock()

font_sm = pygame.font.SysFont("Consolas", 17, bold=True)
font_md = pygame.font.SysFont("Consolas", 26, bold=True)
font_lg = pygame.font.SysFont("Consolas", 62, bold=True)
font_xl = pygame.font.SysFont("Consolas", 80, bold=True)


# ── Asset Manager ──────────────────────────────────────────────────────────────
class AssetManager:
    def __init__(self):
        self.images = {}
        self.sounds = {}
        self.current_music = None
        self.placeholder_colors = {
            "player":      (  0, 200, 255),
            "zombie":      (150,  50,  50),
            "ranged":      ( 70,  70, 150),
            "boss":        (255,  30,  30),
            "bullet":      (255, 255, 100),
            "shield":      (100, 200, 255),
            "tile_grass":  ( 30,  60,  30),
            "tile_rock":   ( 70,  70,  80),
            "tile_water":  ( 30,  60, 120),
            "tile_hole":   ( 10,  10,  20),
            "tile_forest": ( 20,  40,  20),
        }

    def get_image(self, name, size=(80, 80)):
        key = (name, size)
        if key not in self.images:
            # map asset name aliases
            disk_name = name
            if name == "tile_grass":   disk_name = "tile_battle_ground"
            path = os.path.join("assets/images", f"{disk_name}.png")
            if os.path.exists(path):
                try:
                    img = pygame.image.load(path).convert_alpha()
                    self.images[key] = pygame.transform.scale(img, size)
                    return self.images[key]
                except:
                    pass
            self.images[key] = self._make_placeholder(name, size)
        return self.images[key]

    def _make_placeholder(self, name, size):
        surf = pygame.Surface(size, pygame.SRCALPHA)
        color = self.placeholder_colors.get(name, (200, 200, 200))
        if name.startswith("tile_"):
            surf.fill(color)
            for _ in range(8):
                rx, ry = random.randint(0, size[0]), random.randint(0, size[1])
                pygame.draw.circle(surf,
                    (max(0, color[0]-15), max(0, color[1]-15), max(0, color[2]-15)),
                    (rx, ry), 3)
        else:
            cx, cy = size[0]//2, size[1]//2
            r = min(size)//2 - 2
            pygame.draw.circle(surf, color, (cx, cy), r)
            pygame.draw.circle(surf, (30, 30, 30), (cx, cy), r//3)
        return surf

    def play_sound(self, name, volume=1.0):
        if name not in self.sounds:
            for attempt in [name, "sheild" if name == "shield" else name]:
                p = os.path.join("assets/sounds", f"{attempt}.wav")
                if os.path.exists(p):
                    try:
                        self.sounds[name] = pygame.mixer.Sound(p)
                        break
                    except:
                        pass
            else:
                self.sounds[name] = None
        if self.sounds.get(name):
            self.sounds[name].set_volume(volume)
            self.sounds[name].play()

    def play_music(self, name, volume=0.55):
        name = name.replace(".mp3", "")
        if self.current_music == name:
            return
        candidates = [
            os.path.join("assets/music", f"{name}.mp3"),
            os.path.join("assets/music", f"{name}_song.mp3"),
        ]
        for p in candidates:
            if os.path.exists(p):
                try:
                    pygame.mixer.music.load(p)
                    pygame.mixer.music.set_volume(volume)
                    pygame.mixer.music.play(-1)
                    self.current_music = name
                    return
                except:
                    pass

    def stop_music(self, fade_ms=800):
        pygame.mixer.music.fadeout(fade_ms)
        self.current_music = None


assets = AssetManager()


# ── Room ───────────────────────────────────────────────────────────────────────
class Room:
    TILE_NAMES = ["GRASS", "ROCK", "WATER", "HOLE", "FOREST"]
    IMG_NAMES  = ["tile_grass", "tile_rock", "tile_water", "tile_hole", "tile_forest"]

    def __init__(self, x, y):
        self.x, self.y = x, y
        self._load_map()

    def _load_map(self):
        path = os.path.join("assets/maps", f"{self.x}_{self.y}.csv")
        if os.path.exists(path):
            with open(path) as f:
                self.grid = [[int(c) for c in row] for row in csv.reader(f)]
        else:
            # Procedurally generate a simple map
            self.grid = self._generate()

    def _generate(self):
        g = [[0]*8 for _ in range(6)]
        
        # scatter features
        rng = random.Random((self.x * 31 + self.y * 97) & 0xFFFF)
        for _ in range(8):
            r, c = rng.randint(0, 5), rng.randint(0, 7)
            # prevent blocking the very edges too much to ensure smooth transitions
            if r in (0, 5) or c in (0, 7):
                if rng.random() < 0.5: continue
            g[r][c] = rng.choice([1, 2, 3, 4])
        return g

    def get_type(self, px, py):
        gx, gy = int(px // TILE_SIZE), int(py // TILE_SIZE)
        if 0 <= gx < 8 and 0 <= gy < 6:
            return self.TILE_NAMES[self.grid[gy][gx]]
        return "ROCK"

    def draw(self, surface):
        for gy, row in enumerate(self.grid):
            for gx, val in enumerate(row):
                img = assets.get_image(self.IMG_NAMES[val], (TILE_SIZE, TILE_SIZE))
                surface.blit(img, (gx * TILE_SIZE, gy * TILE_SIZE))


# ── Lighting ───────────────────────────────────────────────────────────────────
class LightingSystem:
    DIV = 6

    def __init__(self):
        self._build_mask(400)

    def _build_mask(self, radius):
        self.light_radius = radius
        rad = radius // self.DIV
        mask = pygame.Surface((rad * 2, rad * 2), pygame.SRCALPHA)
        for r in range(rad, 0, -1):
            t = r / rad
            alpha = int(60 + 195 * (1 - t))
            pygame.draw.circle(mask, (255, 255, 255, alpha), (rad, rad), r)
        self.light_mask = mask

    def render(self, surface, player_pos, extra_lights=None):
        W, H = SCREEN_WIDTH // self.DIV, SCREEN_HEIGHT // self.DIV
        small = pygame.Surface((W, H))
        small.fill((30, 32, 48))

        pulse = 1.0 + math.sin(pygame.time.get_ticks() * 0.004) * 0.04
        main_mask = pygame.transform.rotozoom(self.light_mask, 0, pulse)
        cx, cy = int(player_pos[0] // self.DIV), int(player_pos[1] // self.DIV)
        small.blit(main_mask, main_mask.get_rect(center=(cx, cy)))

        if extra_lights:
            for (lx, ly, lr, la) in extra_lights:
                rad = lr // self.DIV
                lsurf = pygame.Surface((rad * 2, rad * 2), pygame.SRCALPHA)
                for r in range(rad, 0, -1):
                    t = r / rad
                    a = int(la * (1 - t))
                    pygame.draw.circle(lsurf, (255, 255, 255, a), (rad, rad), r)
                small.blit(lsurf, lsurf.get_rect(center=(lx // self.DIV, ly // self.DIV)))

        big = pygame.transform.scale(small, (SCREEN_WIDTH, SCREEN_HEIGHT))
        surface.blit(big, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)


# ── Particles ──────────────────────────────────────────────────────────────────
class Particle:
    __slots__ = ("pos", "vel", "color", "life", "age", "size", "gravity")

    def __init__(self, pos, color, speed=3, life=1.0, size=6, gravity=0.0):
        self.pos  = pygame.math.Vector2(pos)
        angle     = random.uniform(0, math.tau)
        spd       = random.uniform(speed * 0.4, speed)
        self.vel  = pygame.math.Vector2(math.cos(angle) * spd, math.sin(angle) * spd)
        self.color   = color
        self.life    = life
        self.age     = 0.0
        self.size    = size
        self.gravity = gravity


class ParticleManager:
    def __init__(self):
        self.particles: list[Particle] = []

    def emit(self, pos, color, count=1, speed=3, life=0.7, size=6, gravity=0.0):
        for _ in range(count):
            self.particles.append(Particle(pos, color, speed, life, size, gravity))

    def emit_burst(self, pos, color1, color2, count=20):
        for _ in range(count):
            c = color1 if random.random() < 0.5 else color2
            self.particles.append(Particle(pos, c, speed=random.uniform(2, 9),
                                           life=random.uniform(0.4, 1.0),
                                           size=random.randint(3, 9),
                                           gravity=120))

    def update(self, dt):
        live = []
        for p in self.particles:
            p.age += dt
            if p.age < p.life:
                p.vel.y += p.gravity * dt
                p.pos   += p.vel * dt * 60
                live.append(p)
        self.particles = live

    def draw(self, surface):
        for p in self.particles:
            t     = p.age / p.life
            alpha = int(255 * (1 - t))
            sz    = max(1, int(p.size * (1 - t * 0.5)))
            s = pygame.Surface((sz * 2, sz * 2), pygame.SRCALPHA)
            col   = (*p.color[:3], alpha)
            pygame.draw.rect(s, col, (0, 0, sz * 2, sz * 2))
            surface.blit(s, (int(p.pos.x) - sz, int(p.pos.y) - sz))


# ── Bullet ─────────────────────────────────────────────────────────────────────
class Bullet(pygame.sprite.Sprite):
    def __init__(self, pos, angle, is_enemy=False, speed_mul=1.0, damage=5):
        super().__init__()
        self.pos      = pygame.math.Vector2(pos)
        rad           = math.radians(-angle)
        spd           = (9 if is_enemy else 15) * speed_mul
        self.vel      = pygame.math.Vector2(math.cos(rad), math.sin(rad)) * spd
        self.is_enemy = is_enemy
        self.damage   = damage
        self.image    = assets.get_image("bullet", (28, 28))
        self.rect     = self.image.get_rect(center=self.pos)
        self.trail    = []

    def update(self, dt, room):
        self.trail.append(pygame.math.Vector2(self.pos))
        if len(self.trail) > 5:
            self.trail.pop(0)
        self.pos    += self.vel * dt * 60
        self.rect.center = self.pos
        t_type = room.get_type(self.pos.x, self.pos.y)
        if t_type in ("FOREST", "ROCK"):
            return "kill"
        if not (0 <= self.pos.x <= SCREEN_WIDTH and 0 <= self.pos.y <= SCREEN_HEIGHT):
            return "kill"
        return None

    def draw_trail(self, surface):
        for i, p in enumerate(self.trail):
            alpha = int(180 * (i / len(self.trail))) if self.trail else 0
            sz    = max(2, 5 - (len(self.trail) - i))
            s     = pygame.Surface((sz*2, sz*2), pygame.SRCALPHA)
            col   = (255, 220, 60, alpha) if not self.is_enemy else (255, 80, 80, alpha)
            pygame.draw.circle(s, col, (sz, sz), sz)
            surface.blit(s, (int(p.x) - sz, int(p.y) - sz))


# ── Gloo Wall ──────────────────────────────────────────────────────────────────
class GlooWall(pygame.sprite.Sprite):
    def __init__(self, pos, angle):
        super().__init__()
        self.pos    = pygame.math.Vector2(pos)
        base        = assets.get_image("shield", (130, 40))
        self.image  = pygame.transform.rotate(base, angle)
        self.rect   = self.image.get_rect(center=self.pos)
        self.health = 250
        self.life   = 15.0
        self.age    = 0.0

    def update(self, dt):
        self.life -= dt
        self.age  += dt
        return self.life > 0 and self.health > 0


# ── Pickup ─────────────────────────────────────────────────────────────────────
class Pickup(pygame.sprite.Sprite):
    TYPES = {
        "ammo":   (NEON_CYAN,   "+25 AMMO"),
        "health": ((50, 220, 80), "+30 HP"),
    }
    def __init__(self, pos, kind="ammo"):
        super().__init__()
        self.pos  = pygame.math.Vector2(pos)
        self.kind = kind
        self.age  = 0.0
        color     = self.TYPES[kind][0]
        img = pygame.Surface((28, 28), pygame.SRCALPHA)
        pygame.draw.rect(img, (*color, 220), (4, 4, 20, 20), border_radius=6)
        pygame.draw.rect(img, WHITE, (4, 4, 20, 20), 2, border_radius=6)
        lbl = font_sm.render(kind[0].upper(), True, WHITE)
        img.blit(lbl, lbl.get_rect(center=(14, 14)))
        self.image = img
        self.rect  = self.image.get_rect(center=self.pos)

    def update(self, dt):
        self.age += dt
        self.rect.centery = int(self.pos.y + math.sin(self.age * 3) * 4)


# ── Player ─────────────────────────────────────────────────────────────────────
class Player(pygame.sprite.Sprite):
    MAX_HEALTH = 100
    MAX_AMMO   = 120

    def __init__(self):
        super().__init__()
        self.pos    = pygame.math.Vector2(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        self.size   = (90, 90)
        self.base_img = assets.get_image("player", self.size)
        self.image  = self.base_img
        self.rect   = self.image.get_rect(center=self.pos)

        self.speed         = 220           # px / sec
        self.health        = self.MAX_HEALTH
        self.ammo          = 80
        self.score         = 0
        self.kills         = 0
        self.shoot_cooldown= 0.16
        self.shoot_timer   = 0.0
        self.dash_cooldown = 0.0
        self.dash_cd_max   = 1.2
        self.shield_cd     = 0.0
        self.shield_cd_max = 3.5
        self.emp_cd        = 0.0
        self.emp_cd_max    = 5.0
        self.is_dashing    = False
        self.dash_timer    = 0.0
        self.dash_dir      = pygame.math.Vector2(1, 0)
        self.falling       = False
        self.scale         = 1.0
        self.hurt_flash    = 0.0
        self.invincible    = 0.0  # dash i-frames

    def _collide_free_pos(self, new_pos, room):
        t = room.get_type(new_pos.x, new_pos.y)
        if t in ("FOREST", "ROCK"):
            return False, t
        return True, t

    def move(self, dx, dy, room):
        if self.falling:
            return None

        new_pos = self.pos + pygame.math.Vector2(dx, dy)

        # Screen-edge transitions
        if new_pos.x < 10:   return "LEFT"
        if new_pos.x > SCREEN_WIDTH - 10:  return "RIGHT"
        if new_pos.y < 10:   return "UP"
        if new_pos.y > SCREEN_HEIGHT - 10: return "DOWN"

        ok, t = self._collide_free_pos(new_pos, room)
        if t == "HOLE" and not self.is_dashing:
            self.falling = True
            assets.play_sound("death", 0.7)
            return None
        if ok:
            self.pos = new_pos
        self.rect.center = self.pos
        return None

    def update(self, dt, keys, mouse_pos, room, particles):
        result = {"trans": None, "wall": None, "shockwave": False, "angle": 0}

        # ── Falling death animation ──────────────────────────────────────────
        if self.falling:
            self.scale -= 3.0 * dt
            if self.scale <= 0.05:
                self.health = 0
            sz = max(1, int(self.size[0] * max(0.05, self.scale)))
            self.image = pygame.transform.rotozoom(
                assets.get_image("player", self.size), 0, max(0.05, self.scale))
            self.rect  = self.image.get_rect(center=self.pos)
            return result

        # ── Cooldown ticks ───────────────────────────────────────────────────
        self.dash_cooldown = max(0, self.dash_cooldown - dt)
        self.shield_cd     = max(0, self.shield_cd - dt)
        self.emp_cd        = max(0, self.emp_cd - dt)
        self.shoot_timer   = max(0, self.shoot_timer - dt)
        self.hurt_flash    = max(0, self.hurt_flash - dt)
        self.invincible    = max(0, self.invincible - dt)

        # ── Dash ─────────────────────────────────────────────────────────────
        if keys[pygame.K_SPACE] and self.dash_cooldown <= 0:
            self.is_dashing    = True
            self.dash_timer    = 0.22
            self.dash_cooldown = self.dash_cd_max
            self.invincible    = 0.25
            mv = pygame.math.Vector2(
                keys[pygame.K_d] - keys[pygame.K_a],
                keys[pygame.K_s] - keys[pygame.K_w])
            self.dash_dir = (mv.normalize() if mv.length() > 0
                             else (mouse_pos - self.pos).normalize())
            particles.emit(self.pos, NEON_CYAN, count=12, speed=5, life=0.4)
            assets.play_sound("pickup", 0.4)

        # ── EMP ──────────────────────────────────────────────────────────────
        if keys[pygame.K_q] and self.emp_cd <= 0:
            self.emp_cd = self.emp_cd_max
            result["shockwave"] = True
            particles.emit_burst(self.pos, NEON_CYAN, (100, 200, 255), count=30)
            assets.play_sound("pickup", 0.6)

        # ── Movement ─────────────────────────────────────────────────────────
        if self.is_dashing:
            result["trans"] = self.move(
                self.dash_dir.x * 24, self.dash_dir.y * 24, room)
            self.dash_timer -= dt
            if self.dash_timer <= 0:
                self.is_dashing = False
            # dash particles trail
            particles.emit(self.pos, (80, 200, 255), count=2, speed=2, life=0.25)
        else:
            dx = (keys[pygame.K_d] - keys[pygame.K_a]) * self.speed * dt
            dy = (keys[pygame.K_s] - keys[pygame.K_w]) * self.speed * dt
            if dx != 0 and dy != 0:
                dx *= 0.707; dy *= 0.707
            result["trans"] = self.move(dx, dy, room)

        # ── Gloo Wall ────────────────────────────────────────────────────────
        if keys[pygame.K_e] and self.shield_cd <= 0:
            self.shield_cd = self.shield_cd_max
            angle  = -math.degrees(math.atan2(
                mouse_pos.y - self.pos.y, mouse_pos.x - self.pos.x))
            rad    = math.radians(-angle)
            wpos   = self.pos + pygame.math.Vector2(math.cos(rad), math.sin(rad)) * 100
            assets.play_sound("shield", 0.8)
            result["wall"] = GlooWall(wpos, angle)

        # ── Rotation ─────────────────────────────────────────────────────────
        angle    = -math.degrees(math.atan2(
            mouse_pos.y - self.pos.y, mouse_pos.x - self.pos.x))
        result["angle"] = angle

        # tint red on hurt
        base = assets.get_image("player", self.size)
        if self.hurt_flash > 0:
            tint  = base.copy()
            red   = pygame.Surface(self.size, pygame.SRCALPHA)
            red.fill((255, 0, 0, int(180 * self.hurt_flash)))
            tint.blit(red, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            self.image = pygame.transform.rotate(tint, angle)
        else:
            self.image = pygame.transform.rotate(base, angle)
        self.rect = self.image.get_rect(center=self.pos)

        return result

    def take_damage(self, amount):
        if self.invincible > 0:
            return
        self.health    = max(0, self.health - amount)
        self.hurt_flash = 0.35
        self.invincible = 0.08


# ── Swarm Intelligence (Conway's Game of Life) ────────────────────────────────
class SwarmController:
    def __init__(self, width, height, cell_size):
        self.cell_size = cell_size
        self.cols = width // cell_size
        self.rows = height // cell_size
        self.grid = [[0 for _ in range(self.cols)] for _ in range(self.rows)]
        self.update_timer = 0.0
        self.update_interval = 1.0  # Apply GoL rules every 1 second

    def update(self, dt, enemies, room_x, room_y):
        self.update_timer += dt
        
        # Reset grid counts
        new_grid = [[0 for _ in range(self.cols)] for _ in range(self.rows)]
        for e in enemies:
            gx = int(e.pos.x // self.cell_size)
            gy = int(e.pos.y // self.cell_size)
            if 0 <= gx < self.cols and 0 <= gy < self.rows:
                new_grid[gy][gx] += 1
        self.grid = new_grid

        if self.update_timer >= self.update_interval:
            self.update_timer = 0
            return self._apply_rules(enemies, room_x, room_y)
        return []

    def _apply_rules(self, enemies, room_x, room_y):
        new_enemies = []
        # GoL logic: 1 if cell has enemies, 0 otherwise
        binary_grid = [[1 if self.grid[y][x] > 0 else 0 for x in range(self.cols)] for y in range(self.rows)]
        
        spawn_candidates = []

        for y in range(self.rows):
            for x in range(self.cols):
                neighbors = 0
                for dy in [-1, 0, 1]:
                    for dx in [-1, 0, 1]:
                        if dx == 0 and dy == 0: continue
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < self.cols and 0 <= ny < self.rows:
                            neighbors += binary_grid[ny][nx]
                
                # Rule: Reproduction
                if binary_grid[y][x] == 0 and neighbors == 3:
                    # Only spawn if total enemies aren't too many
                    if len(enemies) + len(new_enemies) < 15 + (abs(room_x) + abs(room_y)) * 2:
                        spawn_candidates.append((x, y))

                # Rule: Overpopulation / Underpopulation for existing enemies
                # We handle this by setting a 'gol_state' on the enemy
                state = "stable"
                if binary_grid[y][x] == 1:
                    if neighbors < 2: state = "underpopulated"
                    elif neighbors > 3: state = "overpopulated"
                
                # Update enemies in this cell
                for e in enemies:
                    gx = int(e.pos.x // self.cell_size)
                    gy = int(e.pos.y // self.cell_size)
                    if gx == x and gy == y:
                        e.gol_state = state

        # Randomly spawn from candidates to keep it interesting
        if spawn_candidates:
            sx, sy = random.choice(spawn_candidates)
            pos = (sx * self.cell_size + self.cell_size // 2, 
                   sy * self.cell_size + self.cell_size // 2)
            new_enemies.append(Enemy(pos, "zombie"))
            
        return new_enemies

    def get_state_at(self, x, y):
        gx, gy = int(x // self.cell_size), int(y // self.cell_size)
        if 0 <= gx < self.cols and 0 <= gy < self.rows:
            # Re-calculate state for real-time movement feedback
            neighbors = 0
            binary_grid = [[1 if self.grid[ny][nx] > 0 else 0 for nx in range(self.cols)] for ny in range(self.rows)]
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    if dx == 0 and dy == 0: continue
                    nx, ny = gx + dx, gy + dy
                    if 0 <= nx < self.cols and 0 <= ny < self.rows:
                        neighbors += binary_grid[ny][nx]
            
            if binary_grid[gy][gx] == 1:
                if neighbors < 2: return "underpopulated"
                if neighbors > 3: return "overpopulated"
                return "stable"
        return "underpopulated"

# ── Enemy ──────────────────────────────────────────────────────────────────────
ENEMY_STATS = {
    "zombie": {"hp": 12,  "speed": (1.5, 3.0), "shoot_cd": 999, "dmg": 1, "score": 100, "size": (85,  85)},
    "ranged": {"hp": 20,  "speed": (1.0, 1.8), "shoot_cd": 2.0, "dmg": 1, "score": 150, "size": (85,  85)},
    "boss":   {"hp": 400, "speed": (0.8, 1.4), "shoot_cd": 0.38,"dmg": 3, "score": 500, "size": (130, 130)},
}


class Enemy(pygame.sprite.Sprite):
    def __init__(self, pos, e_type="zombie"):
        super().__init__()
        self.pos    = pygame.math.Vector2(pos)
        self.e_type = e_type
        stats       = ENEMY_STATS[e_type]
        self.size   = stats["size"]
        self.base_img = assets.get_image(e_type, self.size)
        self.image  = self.base_img
        self.rect   = self.image.get_rect(center=self.pos)
        self.speed  = random.uniform(*stats["speed"])
        self.health = stats["hp"]
        self.max_hp = stats["hp"]
        self.shoot_cd    = stats["shoot_cd"]
        self.shoot_timer = random.uniform(1.0, 3.0)
        self.dmg         = stats["dmg"]
        self.score_val   = stats["score"]
        self.stunned  = 0.0
        self.falling  = False
        self.scale    = 1.0
        self.hurt_flash = 0.0
        # Wandering for ranged
        self.wander_timer = 0.0
        self.wander_dir   = pygame.math.Vector2(random.uniform(-1,1), random.uniform(-1,1)).normalize()
        
        # Swarm GoL State
        self.gol_state = "stable"
        self.state_timer = 0.0

    def update(self, dt, player_pos, room, particles, swarm_ctrl=None):
        if self.stunned > 0:
            self.stunned = max(0, self.stunned - dt)
            return None
        if self.falling:
            self.scale -= 3.0 * dt
            if self.scale <= 0.05:
                self.kill()
            self.image = pygame.transform.rotozoom(
                assets.get_image(self.e_type, self.size), 0, max(0.05, self.scale))
            self.rect  = self.image.get_rect(center=self.pos)
            return None

        self.hurt_flash = max(0, self.hurt_flash - dt)
        
        # Intelligence based on GoL state
        current_speed = self.speed
        aggression_mul = 1.0
        
        if swarm_ctrl:
            self.gol_state = swarm_ctrl.get_state_at(self.pos.x, self.pos.y)
            
        if self.gol_state == "underpopulated":
            # Alone and afraid: move slower, no shooting
            current_speed *= 0.6
            aggression_mul = 0.0
        elif self.gol_state == "overpopulated":
            # Too many enemies: take damage, move erratically
            self.health -= 0.5 * dt
            current_speed *= 1.4
            aggression_mul = 0.5
            if random.random() < 0.1:
                self.wander_dir = pygame.math.Vector2(random.uniform(-1,1), random.uniform(-1,1)).normalize()
        else: # stable
            # Empowered by the swarm: move faster, shoot faster
            current_speed *= 1.2
            aggression_mul = 1.5

        dist = (player_pos - self.pos).length()

        # Movement logic
        if self.gol_state == "underpopulated":
            # Try to find others: move towards player (usually center of action)
            dir_vec = player_pos - self.pos
            move_vec = dir_vec.normalize() if dir_vec.length() > 0 else pygame.math.Vector2(0,0)
        elif self.gol_state == "overpopulated":
            # Move away from player and others (chaotic)
            move_vec = self.wander_dir
        else:
            # Stable movement
            if self.e_type == "ranged" and dist < 200:
                self.wander_timer -= dt
                if self.wander_timer <= 0:
                    self.wander_timer = random.uniform(0.5, 1.5)
                    perp = pygame.math.Vector2(-(player_pos - self.pos).y, (player_pos - self.pos).x)
                    if perp.length() > 0:
                        self.wander_dir = perp.normalize()
                move_vec = self.wander_dir
            else:
                dir_vec = player_pos - self.pos
                move_vec = dir_vec.normalize() if dir_vec.length() > 0 else pygame.math.Vector2(0,0)

        new_pos  = self.pos + move_vec * current_speed
        t_type   = room.get_type(new_pos.x, new_pos.y)
        if t_type == "HOLE":
            self.falling = True
        elif t_type not in ("FOREST", "ROCK"):
            self.pos = new_pos
        self.rect.center = self.pos

        # Rotate toward player
        angle = -math.degrees(math.atan2(
            player_pos.y - self.pos.y, player_pos.x - self.pos.x))
        base = assets.get_image(self.e_type, self.size)
        
        # Visual feedback for GoL state
        tint_color = None
        if self.gol_state == "underpopulated":
            tint_color = (100, 100, 100, 100) # Grayish/dim
        elif self.gol_state == "overpopulated":
            tint_color = (255, 100, 0, 100) # Orange/overheated
        
        if self.hurt_flash > 0:
            tint = base.copy()
            red  = pygame.Surface(self.size, pygame.SRCALPHA)
            red.fill((255, 0, 0, int(180 * self.hurt_flash)))
            tint.blit(red, (0,0), special_flags=pygame.BLEND_RGBA_ADD)
            self.image = pygame.transform.rotate(tint, angle)
        elif tint_color:
            tint = base.copy()
            ov = pygame.Surface(self.size, pygame.SRCALPHA)
            ov.fill(tint_color)
            tint.blit(ov, (0,0), special_flags=pygame.BLEND_RGBA_MULT)
            self.image = pygame.transform.rotate(tint, angle)
        else:
            self.image = pygame.transform.rotate(base, angle)

        # Shooting
        bullet = None
        if self.e_type in ("ranged", "boss") and aggression_mul > 0:
            self.shoot_timer -= dt * aggression_mul
            if self.shoot_timer <= 0:
                self.shoot_timer = self.shoot_cd + random.uniform(-0.1, 0.3)
                if self.e_type == "boss":
                    return [Bullet(self.pos, angle + offset, is_enemy=True, damage=self.dmg)
                            for offset in (-12, 0, 12)]
                bullet = Bullet(self.pos, angle, is_enemy=True, damage=self.dmg)
        return bullet


    def take_hit(self, damage, particles):
        self.health    -= damage
        self.hurt_flash = 0.3
        particles.emit(self.pos, BLOOD_COLOR, count=6, speed=4, life=0.5)


# ── Shockwave visual ───────────────────────────────────────────────────────────
class Shockwave:
    def __init__(self, pos):
        self.pos    = pygame.math.Vector2(pos)
        self.radius = 10
        self.max_r  = 260
        self.life   = 1.0
        self.age    = 0.0

    def update(self, dt):
        self.age    += dt
        self.radius  = self.max_r * (self.age / self.life)
        return self.age < self.life

    def draw(self, surface):
        t     = self.age / self.life
        alpha = int(200 * (1 - t))
        r     = int(self.radius)
        if r > 0:
            s = pygame.Surface((r*2+4, r*2+4), pygame.SRCALPHA)
            pygame.draw.circle(s, (0, 230, 255, alpha), (r+2, r+2), r, 3)
            surface.blit(s, (int(self.pos.x)-r-2, int(self.pos.y)-r-2))


# ── HUD ────────────────────────────────────────────────────────────────────────
def draw_hud(surface, player, room_x, room_y):
    # Health bar
    BAR_W, BAR_H = 200, 18
    bx, by = 18, 18
    pygame.draw.rect(surface, (60, 20, 20), (bx, by, BAR_W, BAR_H), border_radius=4)
    hp_w = max(0, int(BAR_W * player.health / player.MAX_HEALTH))
    hp_color = (
        (50, 220, 80) if player.health > 60
        else (230, 180, 20) if player.health > 30
        else (230, 50, 50))
    pygame.draw.rect(surface, hp_color, (bx, by, hp_w, BAR_H), border_radius=4)
    pygame.draw.rect(surface, WHITE, (bx, by, BAR_W, BAR_H), 2, border_radius=4)
    ht = font_sm.render(f"HP  {player.health}/{player.MAX_HEALTH}", True, WHITE)
    surface.blit(ht, (bx + 4, by + 1))

    # Ammo
    ammo_col = NEON_CYAN if player.ammo > 20 else (230, 80, 50)
    surface.blit(font_sm.render(f"AMMO  {player.ammo}", True, ammo_col), (bx, by + 26))

    # Room / Score
    surface.blit(font_sm.render(
        f"ROOM [{room_x:+d},{room_y:+d}]  SCORE {player.score}  KILLS {player.kills}",
        True, (180, 180, 180)), (bx, by + 48))

    # Ability cooldowns
    def _cd_bar(label, cd, cd_max, x, y, color):
        W, H = 80, 8
        ratio = 1 - (cd / cd_max) if cd_max > 0 else 1
        pygame.draw.rect(surface, (50, 50, 60), (x, y, W, H), border_radius=3)
        pygame.draw.rect(surface, color if ratio >= 1 else (100,100,110),
                         (x, y, int(W * ratio), H), border_radius=3)
        pygame.draw.rect(surface, (150,150,160), (x, y, W, H), 1, border_radius=3)
        surface.blit(font_sm.render(label, True, color if ratio >= 1 else (120,120,130)),
                     (x, y + 10))

    _cd_bar("[SPACE] DASH",   player.dash_cooldown,  player.dash_cd_max,  18, 80, NEON_CYAN)
    _cd_bar("[E] WALL",       player.shield_cd,      player.shield_cd_max, 18, 108, (100, 200, 255))
    _cd_bar("[Q] EMP",        player.emp_cd,         player.emp_cd_max,   18, 136, NEON_ORANGE)

    # Minimap
    mm_x, mm_y, mm_s = SCREEN_WIDTH - 110, 18, 90
    overlay = pygame.Surface((mm_s, mm_s), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 120))
    surface.blit(overlay, (mm_x, mm_y))
    pygame.draw.rect(surface, (80, 80, 100), (mm_x, mm_y, mm_s, mm_s), 1)
    dot_x = mm_x + mm_s // 2
    dot_y = mm_y + mm_s // 2
    pygame.draw.circle(surface, NEON_CYAN, (dot_x, dot_y), 4)
    surface.blit(font_sm.render(f"{room_x:+d},{room_y:+d}", True, (150, 150, 170)),
                 (mm_x + 4, mm_y + mm_s - 18))


def draw_menu(surface, tick):
    # Dark overlay with scanlines
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    surface.blit(overlay, (0, 0))
    for sy in range(0, SCREEN_HEIGHT, 4):
        pygame.draw.line(surface, (0, 0, 0, 30), (0, sy), (SCREEN_WIDTH, sy))

    # Animated title
    t       = math.sin(tick * 0.002) * 4
    title   = font_xl.render("GODFIRE", True, UI_ACCENT)
    shadow  = font_xl.render("GODFIRE", True, (80, 30, 10))
    surface.blit(shadow, (SCREEN_WIDTH//2 - title.get_width()//2 + 3, 155 + int(t) + 3))
    surface.blit(title,  (SCREEN_WIDTH//2 - title.get_width()//2,     155 + int(t)))

    sub = font_md.render("FOREST SHADOWS", True, (200, 130, 80))
    surface.blit(sub, (SCREEN_WIDTH//2 - sub.get_width()//2, 250))

    # Pulsing prompt
    alpha  = int(160 + 95 * math.sin(tick * 0.004))
    prompt = font_md.render("── SPACE TO BEGIN ──", True, WHITE)
    ps = pygame.Surface(prompt.get_size(), pygame.SRCALPHA)
    ps.blit(prompt, (0, 0))
    ps.set_alpha(alpha)
    surface.blit(ps, (SCREEN_WIDTH//2 - prompt.get_width()//2, 330))

    controls = [
        "WASD   Move        MOUSE   Aim",
        "LMB    Shoot       SPACE   Dash",
        "E      Gloo Wall   Q       EMP Blast",
    ]
    for i, line in enumerate(controls):
        ct = font_sm.render(line, True, (130, 130, 150))
        surface.blit(ct, (SCREEN_WIDTH//2 - ct.get_width()//2, 410 + i * 22))


def draw_game_over(surface, player):
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 210))
    surface.blit(overlay, (0, 0))

    go   = font_lg.render("DEFEATED", True, (220, 50, 50))
    surface.blit(go, (SCREEN_WIDTH//2 - go.get_width()//2, 200))

    stats = [
        f"SCORE : {player.score}",
        f"KILLS : {player.kills}",
        f"AMMO LEFT : {player.ammo}",
    ]
    for i, s in enumerate(stats):
        t = font_md.render(s, True, (180, 180, 180))
        surface.blit(t, (SCREEN_WIDTH//2 - t.get_width()//2, 290 + i*36))

    restart = font_md.render("[ R ]  RESTART", True, NEON_CYAN)
    surface.blit(restart, (SCREEN_WIDTH//2 - restart.get_width()//2, 420))


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    room_x, room_y = 0, 0
    current_room   = Room(room_x, room_y)
    lighting       = LightingSystem()
    particles      = ParticleManager()
    player         = Player()
    swarm_ctrl     = SwarmController(SCREEN_WIDTH, SCREEN_HEIGHT, 100)

    bullets       = pygame.sprite.Group()
    enemy_bullets = pygame.sprite.Group()
    enemies       = pygame.sprite.Group()
    walls         = pygame.sprite.Group()
    pickups       = pygame.sprite.Group()
    shockwaves: list[Shockwave] = []

    state = "MENU"
    tick  = 0

    # ── Screen-shake ──────────────────────────────────────────────────────────
    shake_dur   = 0.0
    shake_power = 0
    cam_offset  = pygame.math.Vector2(0, 0)

    def screenshake(dur=0.25, power=6):
        nonlocal shake_dur, shake_power
        shake_dur   = dur
        shake_power = power

    def spawn_enemies():
        enemies.empty()
        pickups.empty()
        depth = abs(room_x) + abs(room_y)
        count = 4 + depth
        for _ in range(count):
            e_pos = (random.randint(160, SCREEN_WIDTH - 160),
                     random.randint(160, SCREEN_HEIGHT - 160))
            e_type = "zombie"
            roll   = random.random()
            if depth >= 2 and roll < 0.25:
                e_type = "ranged"
            if depth >= 3 and roll < 0.10:
                e_type = "boss"
            enemies.add(Enemy(e_pos, e_type))
        # Chance for pickups
        if random.random() < 0.5:
            px = (random.randint(100, SCREEN_WIDTH - 100),
                  random.randint(100, SCREEN_HEIGHT - 100))
            pickups.add(Pickup(px, random.choice(["ammo", "health"])))

    spawn_enemies()

    while True:
        dt  = min(clock.tick(FPS) / 1000.0, 0.05)  # cap dt
        tick += 1
        mouse_raw = pygame.math.Vector2(pygame.mouse.get_pos())

        # Screenshake update
        if shake_dur > 0:
            shake_dur  = max(0, shake_dur - dt)
            cam_offset = pygame.math.Vector2(
                random.uniform(-shake_power, shake_power),
                random.uniform(-shake_power, shake_power)) * (shake_dur / 0.25)
        else:
            cam_offset = pygame.math.Vector2(0, 0)

        mouse_pos = mouse_raw - cam_offset

        # ── Music ─────────────────────────────────────────────────────────────
        if state == "MENU":
            assets.play_music("theme_song", volume=0.5)
        elif state == "PLAYING":
            assets.play_music("battle", volume=0.55)
        elif state == "GAME_OVER":
            assets.stop_music()

        # ── Events ────────────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if state == "MENU" and event.key == pygame.K_SPACE:
                    state = "PLAYING"
                if state == "GAME_OVER" and event.key == pygame.K_r:
                    main(); return

        # ── Game Logic ────────────────────────────────────────────────────────
        if state == "PLAYING":
            keys   = pygame.key.get_pressed()
            p_data = player.update(dt, keys, mouse_pos, current_room, particles)
            trans, wall_obj  = p_data["trans"], p_data["wall"]
            shockwave_active = p_data["shockwave"]
            p_angle          = p_data["angle"]

            if wall_obj:
                walls.add(wall_obj)

            # Update swarm intelligence
            new_spawns = swarm_ctrl.update(dt, enemies, room_x, room_y)
            for ns in new_spawns:
                enemies.add(ns)
                particles.emit_burst(ns.pos, NEON_CYAN, WHITE, count=15)

            if shockwave_active:
                shockwaves.append(Shockwave(player.pos))
                screenshake(0.3, 8)
                for e in list(enemies):
                    d = e.pos.distance_to(player.pos)
                    if d < 260:
                        e.stunned = 2.0 + random.uniform(0, 0.5)
                        diff = e.pos - player.pos
                        if diff.length() > 0:
                            e.pos += diff.normalize() * 60

            # Shoot
            if (pygame.mouse.get_pressed()[0]
                    and player.shoot_timer <= 0
                    and player.ammo > 0
                    and not player.falling):
                player.shoot_timer = player.shoot_cooldown
                player.ammo -= 1
                bullets.add(Bullet(player.pos, p_angle))
                assets.play_sound("shoot", 0.6)
                particles.emit(player.pos, (255, 230, 80), count=3, speed=6, life=0.2)

            # Room transition
            if trans:
                dirs = {"LEFT":  (-1,0,"x",SCREEN_WIDTH-65),
                        "RIGHT": (+1,0,"x",65),
                        "UP":    (0,-1,"y",SCREEN_HEIGHT-65),
                        "DOWN":  (0,+1,"y",65)}
                dx_, dy_, ax, av = dirs[trans]
                room_x += dx_; room_y += dy_
                setattr(player.pos, ax, av)
                current_room = Room(room_x, room_y)
                
                # Clear the tile the player spawns on so they never get stuck
                gx, gy = int(player.pos.x // TILE_SIZE), int(player.pos.y // TILE_SIZE)
                if 0 <= gx < 8 and 0 <= gy < 6:
                    if current_room.grid[gy][gx] in (1, 3, 4): # Rock, Hole, Forest
                        current_room.grid[gy][gx] = 0 # Turn to Grass
                
                spawn_enemies()
                enemy_bullets.empty()
                bullets.empty()
                walls.empty()
                shockwaves.clear()

            # Pickups
            for pu in list(pickups):
                pu.update(dt)
                if pu.rect.collidepoint(player.pos):
                    if pu.kind == "ammo":
                        player.ammo = min(player.MAX_AMMO, player.ammo + 25)
                    else:
                        player.health = min(player.MAX_HEALTH, player.health + 30)
                    particles.emit(pu.pos, (80, 255, 120), count=12, speed=5, life=0.6)
                    assets.play_sound("pickup", 0.7)
                    pu.kill()

            # Particles / shockwaves
            particles.update(dt)
            shockwaves = [sw for sw in shockwaves if sw.update(dt)]

            # Bullet updates
            for b in list(bullets):
                if b.update(dt, current_room) == "kill":
                    particles.emit(b.pos, (255, 230, 80), count=3, speed=3, life=0.3)
                    b.kill()
            for eb in list(enemy_bullets):
                if eb.update(dt, current_room) == "kill":
                    eb.kill()

            # Enemy updates
            for e in list(enemies):
                result = e.update(dt, player.pos, current_room, particles, swarm_ctrl)
                if isinstance(result, list):
                    for nb in result:
                        enemy_bullets.add(nb)
                elif result:
                    enemy_bullets.add(result)

            # Wall updates
            for w in list(walls):
                if not w.update(dt):
                    walls.remove(w)

            # Wall + enemy bullets
            for w in list(walls):
                hits = pygame.sprite.spritecollide(w, enemy_bullets, True)
                for _ in hits:
                    w.health -= 30
                    particles.emit(w.pos, NEON_CYAN, count=4, speed=3, life=0.3)

            # Player bullets hit enemies
            hits = pygame.sprite.groupcollide(enemies, bullets, False, True)
            for e, blist in hits.items():
                total = sum(b.damage for b in blist)
                e.take_hit(total, particles)
                screenshake(0.08, 3)
                if e.health <= 0:
                    particles.emit_burst(e.pos, BLOOD_COLOR, (255, 60, 30), count=25)
                    screenshake(0.2, 6)
                    player.score  += e.score_val
                    player.kills  += 1
                    # drop pickup chance
                    if random.random() < 0.18:
                        pickups.add(Pickup(e.pos, random.choice(["ammo", "health"])))
                    e.kill()
                    assets.play_sound("death", 0.65)

            # Enemy bullets hit player
            if not player.is_dashing and not player.falling and player.invincible <= 0:
                eb_hits = pygame.sprite.spritecollide(player, enemy_bullets, True)
                for eb in eb_hits:
                    player.take_damage(eb.damage)
                    screenshake(0.2, 5)
                    particles.emit(player.pos, BLOOD_COLOR, count=8, speed=4, life=0.5)
                # Melee enemies
                melee_hits = pygame.sprite.spritecollide(player, enemies, False)
                if melee_hits:
                    player.take_damage(0.6 * dt * len(melee_hits) * 60)
                    particles.emit(player.pos, BLOOD_COLOR, count=1, speed=2, life=0.3)

            if player.health <= 0:
                state = "GAME_OVER"

        # ── Render ─────────────────────────────────────────────────────────────
        # Shift surface for screenshake
        game_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        game_surf.fill(DARK_BG)

        current_room.draw(game_surf)

        # Wall glow effect
        for w in walls:
            glow = pygame.Surface((w.rect.width + 20, w.rect.height + 20), pygame.SRCALPHA)
            glow.fill((100, 200, 255, 30))
            game_surf.blit(glow, (w.rect.x - 10, w.rect.y - 10))
            game_surf.blit(w.image, w.rect)

        # Bullet trails then sprites
        for b in bullets:
            b.draw_trail(game_surf)
            game_surf.blit(b.image, b.rect)
        for eb in enemy_bullets:
            eb.draw_trail(game_surf)
            game_surf.blit(eb.image, eb.rect)

        # Pickups
        for pu in pickups:
            game_surf.blit(pu.image, pu.rect)

        # Enemies (health bars)
        for e in enemies:
            game_surf.blit(e.image, e.rect)
            if e.health < e.max_hp and not e.falling:
                bw = 50
                bx = e.rect.centerx - bw//2
                by = e.rect.top - 8
                pygame.draw.rect(game_surf, (80, 20, 20),  (bx, by, bw, 5), border_radius=2)
                hp_ratio = max(0, e.health / e.max_hp)
                pygame.draw.rect(game_surf, (220, 50, 50), (bx, by, int(bw * hp_ratio), 5), border_radius=2)

        particles.draw(game_surf)

        for sw in shockwaves:
            sw.draw(game_surf)

        game_surf.blit(player.image, player.rect)

        # Lighting
        if state != "MENU":
            extra = [(e.pos.x, e.pos.y, 80, 60) for e in enemies if e.e_type == "boss"]
            lighting.render(game_surf, player.pos, extra_lights=extra or None)

        # Blit with shake offset
        ox, oy = int(cam_offset.x), int(cam_offset.y)
        screen.fill(DARK_BG)
        screen.blit(game_surf, (ox, oy))

        # HUD (no shake)
        if state == "PLAYING":
            draw_hud(screen, player, room_x, room_y)

        # Overlays
        if state == "MENU":
            current_room.draw(screen)  # show bg behind menu
            draw_menu(screen, tick)
        elif state == "GAME_OVER":
            draw_game_over(screen, player)

        pygame.display.flip()


if __name__ == "__main__":
    main()
