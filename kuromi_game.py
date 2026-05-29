"""
╔══════════════════════════════════════════════════════════════════════╗
║          KUROMI'S DARK ADVENTURE  — Fixed & Improved                ║
║  Fixes: No more freeze (async sound), Kuromi looks like Kuromi!     ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import pygame
import sys
import math
import random
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

pygame.init()
# Initialize mixer with error handling
try:
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
    SOUND_OK = True
except:
    SOUND_OK = False

# ─────────────────────────────────────────────
#  CONSTANTS & CONFIG
# ─────────────────────────────────────────────
W, H = 1280, 720
FPS  = 60
GRAVITY = 0.55
TILE = 48

# Kuromi palette
C_BG       = (10,  8,  20)
C_BLACK    = (15,  12, 28)
C_PURPLE   = (120, 40, 200)
C_LPURPLE  = (180, 100, 255)
C_PINK     = (255, 100, 200)
C_WHITE    = (240, 235, 255)
C_DARK     = (30,  20,  50)
C_SKULL    = (220, 210, 230)
C_RED      = (220, 60,  80)
C_YELLOW   = (255, 230, 60)
C_CYAN     = (80,  220, 255)
C_GOLD     = (255, 200, 50)
C_KBLACK   = (20,  18,  30)   # Kuromi's body black (slightly purple tinted)
C_KWHITE   = (245, 240, 255)  # Kuromi's face white

screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("✦ Kuromi's Dark Adventure ✦")
clock = pygame.time.Clock()

# ─────────────────────────────────────────────
#  SOUND ENGINE  (lazy / cached, no startup freeze)
# ─────────────────────────────────────────────
_sound_cache = {}

def make_sound(freq=440, duration=0.15, wave="square", volume=0.3):
    if not SOUND_OK: return None
    sr   = 44100
    n    = int(sr * duration)
    buf  = bytearray(n * 2)
    for i in range(n):
        t   = i / sr
        env = max(0.0, 1.0 - i / n)
        if wave == "square":
            v = 1.0 if math.sin(2 * math.pi * freq * t) > 0 else -1.0
        elif wave == "sine":
            v = math.sin(2 * math.pi * freq * t)
        elif wave == "noise":
            v = random.uniform(-1, 1)
        else:
            v = math.sin(2 * math.pi * freq * t)
        s = int(v * env * volume * 32767)
        s = max(-32768, min(32767, s))
        buf[2*i]   = s & 0xFF
        buf[2*i+1] = (s >> 8) & 0xFF
    snd = pygame.mixer.Sound(buffer=bytes(buf))
    return snd

def get_sound(name):
    if not SOUND_OK: return None
    if name not in _sound_cache:
        specs = {
            "jump"    : (300, 0.12, "square", 0.25),
            "shoot"   : (600, 0.08, "square", 0.20),
            "hit"     : (150, 0.18, "noise",  0.35),
            "pickup"  : (880, 0.18, "sine",   0.30),
            "death"   : (120, 0.40, "noise",  0.40),
            "boss_hit": (80,  0.25, "noise",  0.45),
            "level_up": (660, 0.40, "sine",   0.35),
        }
        if name in specs:
            _sound_cache[name] = make_sound(*specs[name])
        else:
            _sound_cache[name] = None
    return _sound_cache[name]

def play(name):
    snd = get_sound(name)
    if snd:
        try: snd.play()
        except: pass

# ─────────────────────────────────────────────
#  FONT MANAGER
# ─────────────────────────────────────────────
def get_font(size, bold=False):
    try:    return pygame.font.SysFont("segoeui", size, bold=bold)
    except: return pygame.font.Font(None, size)

FONT_BIG   = get_font(72, True)
FONT_MED   = get_font(36, True)
FONT_SMALL = get_font(22)
FONT_TINY  = get_font(16)

# ─────────────────────────────────────────────
#  PARTICLE SYSTEM
# ─────────────────────────────────────────────
@dataclass
class Particle:
    x: float; y: float
    vx: float; vy: float
    life: float; max_life: float
    color: Tuple
    size: float
    grav: float = 0.0
    shape: str  = "circle"

    def update(self):
        self.x  += self.vx
        self.y  += self.vy
        self.vy += self.grav
        self.life -= 1
        self.vx *= 0.97

    @property
    def alive(self): return self.life > 0

    def draw(self, surf):
        a = max(0, int(255 * self.life / self.max_life))
        s = max(1, int(self.size * self.life / self.max_life))
        c = (*self.color[:3], a)
        tmp = pygame.Surface((s*2+2, s*2+2), pygame.SRCALPHA)
        if self.shape == "circle":
            pygame.draw.circle(tmp, c, (s+1, s+1), s)
        elif self.shape == "star":
            draw_star(tmp, c, s+1, s+1, s, 5)
        elif self.shape == "skull":
            draw_mini_skull(tmp, c, s+1, s+1, s)
        surf.blit(tmp, (int(self.x)-s-1, int(self.y)-s-1))

particles: List[Particle] = []

def spawn_particles(x, y, color, n=12, speed=3, grav=0.1,
                    shape="circle", size=4, spread=math.pi*2):
    for _ in range(n):
        a  = random.uniform(0, spread)
        sp = random.uniform(0.5, speed)
        particles.append(Particle(
            x, y, math.cos(a)*sp, math.sin(a)*sp,
            random.randint(20, 45), 45, color,
            random.uniform(size*0.5, size*1.5), grav, shape
        ))

def spawn_death_burst(x, y):
    spawn_particles(x, y, C_PURPLE, 20, 5, 0.15, "circle", 6)
    spawn_particles(x, y, C_PINK,   10, 3, 0.10, "star",   5)
    spawn_particles(x, y, C_SKULL,   6, 4, 0.05, "skull",  8)

# ─────────────────────────────────────────────
#  DRAWING HELPERS
# ─────────────────────────────────────────────
def draw_star(surf, color, cx, cy, r, n=5):
    pts = []
    for i in range(n*2):
        a  = math.pi/2 + i*math.pi/n
        rd = r if i%2==0 else r*0.4
        pts.append((cx + math.cos(a)*rd, cy - math.sin(a)*rd))
    if len(pts) >= 3:
        pygame.draw.polygon(surf, color, pts)

def draw_mini_skull(surf, color, cx, cy, r):
    pygame.draw.circle(surf, color, (cx, cy), max(1, r))
    pygame.draw.circle(surf, C_BLACK, (cx-r//3, cy-r//4), max(1, r//3))
    pygame.draw.circle(surf, C_BLACK, (cx+r//3, cy-r//4), max(1, r//3))

def draw_glow(surf, color, cx, cy, radius, alpha=60):
    for layer in range(4):
        r = radius + layer * 8
        a = max(0, alpha - layer * 15)
        tmp = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
        pygame.draw.circle(tmp, (*color[:3], a), (r, r), r)
        surf.blit(tmp, (cx-r, cy-r), special_flags=pygame.BLEND_RGBA_ADD)

def draw_gradient_rect(surf, color1, color2, rect, vertical=True):
    x, y, w, h = rect
    steps = h if vertical else w
    for i in range(steps):
        t = i / max(1, steps - 1)
        c = tuple(int(color1[j]*(1-t) + color2[j]*t) for j in range(3))
        if vertical:
            pygame.draw.line(surf, c, (x, y+i), (x+w, y+i))
        else:
            pygame.draw.line(surf, c, (x+i, y), (x+i, y+h))

def outline_text(surf, font, text, color, outline_color, x, y, center=True):
    rendered = font.render(text, True, outline_color)
    rx = (x - rendered.get_width()//2) if center else x
    ry = y
    for dx, dy in [(-2,0),(2,0),(0,-2),(0,2),(-2,-2),(2,-2),(-2,2),(2,2)]:
        surf.blit(rendered, (rx+dx, ry+dy))
    rendered = font.render(text, True, color)
    surf.blit(rendered, (rx, ry))

# ─────────────────────────────────────────────
#  KUROMI SPRITE  —  redesigned to look like Kuromi!
#
#  Key features of real Kuromi:
#  • All-black bunny body & long pointy ears with PURPLE/pink inner ear
#  • Big white oval FACE patch on front of head
#  • Large round BLACK eyes with white highlights (cute, not scary)
#  • Small pink cheek blush dots
#  • White skull on forehead with tiny X eyes
#  • Purple jester-style bow/ribbon on side of head
#  • White chest/belly patch
#  • Short stubby limbs, round body
# ─────────────────────────────────────────────
def draw_kuromi(surf, x, y, frame, facing, size=1.0,
                invincible=False, power_type=None):
    if invincible and (frame // 3) % 2 == 0:
        return

    sc = size
    def s(v): return max(1, int(v * sc))
    cx, cy = int(x), int(y)

    # Power-up tint
    body_col = C_KBLACK
    inner_ear_col = (160, 80, 220)   # default purple-pink inner ear
    if power_type == "fire":
        body_col = (50, 18, 18); inner_ear_col = C_RED
    elif power_type == "ice":
        body_col = (15, 35, 70);  inner_ear_col = C_CYAN
    elif power_type == "star":
        body_col = (40, 35, 8);   inner_ear_col = C_GOLD

    # ── SHADOW ──────────────────────────────
    shadow = pygame.Surface((s(40), s(10)), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (0,0,0,70), shadow.get_rect())
    surf.blit(shadow, (cx - s(20), cy + s(28)))

    # ── BODY  (round, chubby) ──────────────
    body_rect = (cx - s(18), cy - s(8), s(36), s(36))
    pygame.draw.ellipse(surf, body_col, body_rect)

    # ── CHEST / BELLY patch (white oval) ──
    belly = (cx - s(11), cy - s(2), s(22), s(24))
    pygame.draw.ellipse(surf, C_KWHITE, belly)

    # ── LONG POINTY EARS ──────────────────
    # Kuromi's ears are tall, narrow, slightly inward-curving
    fl = -1 if facing == "left" else 1
    for side in [-1, 1]:
        ex = cx + side * s(9)
        # Outer ear (black)
        ear_pts = [
            (ex - s(5),  cy - s(10)),
            (ex + s(5),  cy - s(10)),
            (ex + s(3),  cy - s(52)),
            (ex,         cy - s(58)),
            (ex - s(3),  cy - s(52)),
        ]
        pygame.draw.polygon(surf, body_col, ear_pts)
        # Inner ear (purple)
        inner_pts = [
            (ex - s(2),  cy - s(14)),
            (ex + s(2),  cy - s(14)),
            (ex + s(1),  cy - s(48)),
            (ex,         cy - s(53)),
            (ex - s(1),  cy - s(48)),
        ]
        pygame.draw.polygon(surf, inner_ear_col, inner_pts)

    # ── HEAD (big round, sits on body) ────
    head_rect = (cx - s(20), cy - s(40), s(40), s(36))
    pygame.draw.ellipse(surf, body_col, head_rect)

    # ── WHITE FACE PATCH (oval, center-front of head) ──
    # This is the most recognizable Kuromi feature!
    face_rect = (cx - s(14), cy - s(37), s(28), s(28))
    pygame.draw.ellipse(surf, C_KWHITE, face_rect)

    # ── SKULL on forehead ─────────────────
    # White skull with tiny eye-Xs — signature Kuromi mark
    sk_cx = cx
    sk_cy = cy - s(30)
    sk_r  = s(6)
    # skull head
    pygame.draw.circle(surf, C_SKULL, (sk_cx, sk_cy), sk_r)
    # eye sockets (tiny black circles)
    pygame.draw.circle(surf, (20,15,30), (sk_cx - s(2), sk_cy - s(1)), max(1, s(2)))
    pygame.draw.circle(surf, (20,15,30), (sk_cx + s(2), sk_cy - s(1)), max(1, s(2)))
    # teeth (3 little rectangles)
    for ti, tx in enumerate([sk_cx - s(3), sk_cx, sk_cx + s(3)]):
        pygame.draw.rect(surf, (20,15,30), (tx - s(1), sk_cy + s(2), s(2), s(3)))

    # ── EYES  (BIG, round, cute) ──────────
    # Kuromi has large round eyes, mostly black with white shine spots
    blink = (frame % 120) < 5
    ey = cy - s(22)
    # Slightly shift eyes based on facing direction
    off = s(2) if facing == "right" else -s(2)
    elx = cx - s(6) + off
    erx = cx + s(6) + off

    if blink:
        # closed = thick curved line
        pygame.draw.arc(surf, body_col,
            (elx - s(5), ey - s(2), s(10), s(6)), 0, math.pi, s(3))
        pygame.draw.arc(surf, body_col,
            (erx - s(5), ey - s(2), s(10), s(6)), 0, math.pi, s(3))
    else:
        er = s(7)   # eye radius
        # white sclera
        pygame.draw.circle(surf, C_KWHITE, (elx, ey), er)
        pygame.draw.circle(surf, C_KWHITE, (erx, ey), er)
        # big black pupil (almost fills eye = Kuromi's signature look)
        pygame.draw.circle(surf, (10, 8, 20), (elx, ey), s(6))
        pygame.draw.circle(surf, (10, 8, 20), (erx, ey), s(6))
        # white highlight dots (2 per eye for sparkle)
        pygame.draw.circle(surf, C_WHITE, (elx + s(2), ey - s(2)), s(2))
        pygame.draw.circle(surf, C_WHITE, (elx - s(2), ey + s(2)), s(1))
        pygame.draw.circle(surf, C_WHITE, (erx + s(2), ey - s(2)), s(2))
        pygame.draw.circle(surf, C_WHITE, (erx - s(2), ey + s(2)), s(1))

    # ── PINK BLUSH CHEEKS ─────────────────
    for bx2, by2 in [(cx - s(15), cy - s(15)), (cx + s(15), cy - s(15))]:
        blush = pygame.Surface((s(12), s(7)), pygame.SRCALPHA)
        pygame.draw.ellipse(blush, (255, 130, 180, 130), blush.get_rect())
        surf.blit(blush, (bx2 - s(6), by2 - s(3)))

    # ── MOUTH (small happy curve) ─────────
    pygame.draw.arc(surf, (80, 60, 100),
        (cx - s(5), cy - s(11), s(10), s(6)), math.pi, 2*math.pi, s(2))

    # ── JESTER BOW / RIBBON ───────────────
    # Purple bow on top-right of head — very Kuromi
    bwx = cx + s(16)
    bwy = cy - s(38)
    bow_col = (160, 50, 220)
    bow_dark = (100, 20, 160)
    # left triangle
    pygame.draw.polygon(surf, bow_col, [
        (bwx,        bwy),
        (bwx - s(12), bwy - s(7)),
        (bwx - s(12), bwy + s(7)),
    ])
    # right triangle
    pygame.draw.polygon(surf, bow_col, [
        (bwx,        bwy),
        (bwx + s(12), bwy - s(7)),
        (bwx + s(12), bwy + s(7)),
    ])
    # center knot
    pygame.draw.circle(surf, C_PINK, (bwx, bwy), s(4))
    pygame.draw.circle(surf, (255, 180, 220), (bwx, bwy), s(2))

    # ── ARMS (stubby) ─────────────────────
    bob = math.sin(frame * 0.2) * s(3)
    # Left arm
    pygame.draw.ellipse(surf, body_col,
        (cx - s(28), cy - s(4) + int(bob), s(14), s(10)))
    # Right arm
    pygame.draw.ellipse(surf, body_col,
        (cx + s(14), cy - s(4) - int(bob), s(14), s(10)))

    # ── LEGS / WALK ───────────────────────
    walk_a = math.sin(frame * 0.3) * s(5)
    # Left leg
    pygame.draw.ellipse(surf, body_col,
        (cx - s(16), cy + s(20) + int(walk_a), s(14), s(12)))
    # Right leg
    pygame.draw.ellipse(surf, body_col,
        (cx + s(2),  cy + s(20) - int(walk_a), s(14), s(12)))
    # Boots (small purple ovals)
    pygame.draw.ellipse(surf, (120, 40, 180),
        (cx - s(18), cy + s(28) + int(walk_a), s(16), s(9)))
    pygame.draw.ellipse(surf, (120, 40, 180),
        (cx + s(2),  cy + s(28) - int(walk_a), s(16), s(9)))

    # ── POWER AURA ────────────────────────
    if power_type:
        aura_col = {"fire": C_RED, "ice": C_CYAN, "star": C_GOLD}.get(power_type, C_PURPLE)
        draw_glow(surf, aura_col, cx, cy, s(28), 45)

# ─────────────────────────────────────────────
#  ENEMY DRAWINGS (unchanged)
# ─────────────────────────────────────────────
def draw_ghost(surf, x, y, frame, color=C_PURPLE):
    bob = math.sin(frame * 0.08) * 4
    y = int(y + bob)
    pts = [(x-16, y+20), (x-16, y), (x-8, y-16),
           (x, y-20), (x+8, y-16), (x+16, y),
           (x+16, y+20), (x+12, y+12), (x+6, y+20),
           (x, y+12), (x-6, y+20), (x-12, y+12)]
    pygame.draw.polygon(surf, color, pts)
    pygame.draw.polygon(surf, C_DARK, pts, 2)
    pygame.draw.circle(surf, C_WHITE, (x-6, y+2), 5)
    pygame.draw.circle(surf, C_WHITE, (x+6, y+2), 5)
    pygame.draw.circle(surf, C_BLACK, (x-5, y+3), 3)
    pygame.draw.circle(surf, C_BLACK, (x+7, y+3), 3)

def draw_bat(surf, x, y, frame):
    flap = math.sin(frame * 0.25) * 8
    body_col = (40, 20, 60)
    for side, mul in [(-1, -1), (1, 1)]:
        wing_pts = [
            (x + side*4,  y),
            (x + side*30, y - 10 + flap*mul),
            (x + side*24, y + 8  + flap*mul),
            (x + side*14, y + 4),
        ]
        pygame.draw.polygon(surf, body_col, wing_pts)
    pygame.draw.ellipse(surf, (60, 30, 80), (x-8, y-8, 16, 14))
    pygame.draw.circle(surf, C_RED,   (x-3, y-3), 3)
    pygame.draw.circle(surf, C_RED,   (x+3, y-3), 3)
    pygame.draw.circle(surf, C_BLACK, (x-3, y-3), 2)
    pygame.draw.circle(surf, C_BLACK, (x+3, y-3), 2)
    pygame.draw.line(surf, C_WHITE, (x-2, y+4), (x-2, y+8), 2)
    pygame.draw.line(surf, C_WHITE, (x+2, y+4), (x+2, y+8), 2)

def draw_pumpkin_boss(surf, x, y, frame, hp_ratio):
    sc = 1.5 + 0.1*math.sin(frame*0.05)
    def s(v): return max(1, int(v*sc))
    col = (int(200*hp_ratio + 50*(1-hp_ratio)),
           int(100*hp_ratio), int(20*(1-hp_ratio)))
    pygame.draw.ellipse(surf, col, (x-s(40), y-s(50), s(80), s(70)))
    for i in range(-3, 4):
        pygame.draw.arc(surf, (col[0]//2, col[1]//2, col[2]//2),
            (x+i*s(10)-s(20), y-s(30), s(40), s(40)),
            math.pi, 2*math.pi, s(3))
    pygame.draw.rect(surf, (40,80,20), (x-s(6), y-s(64), s(12), s(18)))
    angry = (1 - hp_ratio) > 0.4
    eye_wig = int(math.sin(frame*0.3)*3) if angry else 0
    pygame.draw.polygon(surf, C_YELLOW, [
        (x-s(22), y-s(20)+eye_wig), (x-s(10), y-s(28)+eye_wig),
        (x-s(10), y-s(12)+eye_wig)])
    pygame.draw.polygon(surf, C_YELLOW, [
        (x+s(22), y-s(20)-eye_wig), (x+s(10), y-s(28)-eye_wig),
        (x+s(10), y-s(12)-eye_wig)])
    mouth_pts = [(x-s(25), y+s(5))]
    teeth = 6
    for i in range(teeth+1):
        mx2 = x - s(25) + i*(s(50)//teeth)
        mouth_pts.append((mx2, y+s(5) + (s(15) if i%2==0 else 0)))
    mouth_pts.append((x+s(25), y+s(5)))
    if len(mouth_pts) >= 3:
        pygame.draw.polygon(surf, C_BLACK, mouth_pts)
        pygame.draw.lines(surf, C_YELLOW, False, mouth_pts, s(3))
    draw_glow(surf, col, x, y, s(50), 30)

# ─────────────────────────────────────────────
#  BULLET / PROJECTILE
# ─────────────────────────────────────────────
@dataclass
class Bullet:
    x: float; y: float
    vx: float; vy: float
    owner: str
    power: int = 1
    alive: bool = True
    frame: int = 0
    color: Tuple = C_PINK

    def update(self, platforms):
        self.x += self.vx
        self.y += self.vy
        self.frame += 1
        if not (0 < self.x < W) or not (0 < self.y < H):
            self.alive = False
            return
        for p in platforms:
            if p.collidepoint(self.x, self.y):
                self.alive = False
                return

    def draw(self, surf):
        if not self.alive: return
        draw_glow(surf, self.color, int(self.x), int(self.y), 8, 60)
        draw_star(surf, self.color, int(self.x), int(self.y), 7, 5)
        if random.random() < 0.4:
            particles.append(Particle(
                self.x, self.y,
                random.uniform(-1,1), random.uniform(-1,1),
                8, 8, self.color, 3, 0))

# ─────────────────────────────────────────────
#  PLATFORM TILE
# ─────────────────────────────────────────────
def draw_platform(surf, rect, style="normal", frame=0):
    x, y, w, h = rect
    if style == "normal":
        draw_gradient_rect(surf, C_PURPLE, C_DARK, rect)
        pygame.draw.rect(surf, C_LPURPLE, rect, 2)
        for i in range(w//TILE + 1):
            rx = x + i*TILE + TILE//4
            if rx < x + w:
                draw_star(surf, (*C_LPURPLE, 80), rx, y+4, 4, 4)
    elif style == "cloud":
        draw_gradient_rect(surf, (180,100,220), (100,50,160), rect)
        pygame.draw.rect(surf, C_PINK, rect, 2)
    elif style == "spiky":
        draw_gradient_rect(surf, (80,10,10), (40,5,5), rect)
        pygame.draw.rect(surf, C_RED, rect, 2)
        for i in range(w//12):
            sx2 = x + i*12 + 6
            pygame.draw.polygon(surf, C_RED, [(sx2-5,y),(sx2+5,y),(sx2,y-10)])
    elif style == "bounce":
        t = math.sin(frame*0.08)
        col = (int(100+80*t), int(40+30*t), int(200+40*t))
        pygame.draw.rect(surf, col, rect)
        pygame.draw.rect(surf, C_WHITE, rect, 2)

# ─────────────────────────────────────────────
#  POWER-UP
# ─────────────────────────────────────────────
@dataclass
class PowerUp:
    x: float; y: float
    ptype: str
    alive: bool = True
    frame: int  = 0

    @property
    def rect(self): return pygame.Rect(self.x-16, self.y-16, 32, 32)

    def update(self): self.frame += 1

    def draw(self, surf):
        bob = math.sin(self.frame * 0.1) * 4
        cx2, cy2 = int(self.x), int(self.y + bob)
        colors = {"fire":C_RED,"ice":C_CYAN,"star":C_GOLD,
                  "heart":C_PINK,"speed":C_YELLOW}
        col = colors.get(self.ptype, C_WHITE)
        draw_glow(surf, col, cx2, cy2, 20, 70)
        if self.ptype == "heart":
            pygame.draw.circle(surf, col, (cx2-5, cy2-3), 7)
            pygame.draw.circle(surf, col, (cx2+5, cy2-3), 7)
            pygame.draw.polygon(surf, col, [(cx2-11,cy2-1),(cx2+11,cy2-1),(cx2,cy2+12)])
        elif self.ptype == "star":
            draw_star(surf, col, cx2, cy2, 14, 5)
        elif self.ptype == "speed":
            pygame.draw.polygon(surf, col, [
                (cx2+4,cy2-14),(cx2-2,cy2-2),(cx2+6,cy2-2),
                (cx2-4,cy2+14),(cx2+2,cy2+2),(cx2-6,cy2+2)])
        else:
            pygame.draw.circle(surf, col, (cx2, cy2), 12)
            lbl = FONT_TINY.render(self.ptype[0].upper(), True, C_BLACK)
            surf.blit(lbl, (cx2 - lbl.get_width()//2, cy2 - lbl.get_height()//2))

# ─────────────────────────────────────────────
#  ENEMY
# ─────────────────────────────────────────────
@dataclass
class Enemy:
    x: float; y: float
    etype: str
    hp: int; max_hp: int
    vx: float = 1.0; vy: float = 0.0
    alive: bool = True
    frame: int  = 0
    shoot_cd: int = 0
    bullet_color: Tuple = C_RED
    patrol_left: float  = 0
    patrol_right: float = 0

    @property
    def rect(self):
        return pygame.Rect(self.x-20, self.y-30, 40, 50)

    def update(self, player_x, player_y, platforms, bullets_out):
        if not self.alive: return
        self.frame += 1
        dx = player_x - self.x
        dy = player_y - self.y

        if self.etype == "ghost":
            dist = math.hypot(dx, dy)
            if dist > 0:
                self.x += (dx/dist) * 1.2
                self.y += (dy/dist) * 0.8
            self.shoot_cd -= 1
            if self.shoot_cd <= 0 and dist < 350:
                self.shoot_cd = 90
                spd = 4
                bvx = (dx/dist)*spd if dist>0 else spd
                bvy = (dy/dist)*spd if dist>0 else 0
                bullets_out.append(Bullet(self.x, self.y, bvx, bvy, "enemy",
                                          color=self.bullet_color))
        elif self.etype == "bat":
            self.x += self.vx
            if self.x < self.patrol_left or self.x > self.patrol_right:
                self.vx *= -1
            if abs(dx) < 200 and abs(dy) < 300:
                self.y += (dy / max(1, abs(dy))) * 1.5
        elif self.etype == "pumpkin":
            self.x += self.vx
            if self.x < self.patrol_left + 10 or self.x > self.patrol_right - 10:
                self.vx *= -1
            self.shoot_cd -= 1
            rage = self.hp < self.max_hp * 0.4
            if self.shoot_cd <= 0:
                self.shoot_cd = 40 if rage else 80
                angles = 8 if rage else 4
                for i in range(angles):
                    a = i * (2*math.pi / angles)
                    spd = 5 if rage else 3
                    bullets_out.append(Bullet(self.x, self.y,
                        math.cos(a)*spd, math.sin(a)*spd, "enemy",
                        color=(255,150,0)))
        self.x = max(30, min(W-30, self.x))

    def draw(self, surf):
        if not self.alive: return
        ix, iy = int(self.x), int(self.y)
        if self.etype == "ghost":
            draw_ghost(surf, ix, iy, self.frame)
        elif self.etype == "bat":
            draw_bat(surf, ix, iy, self.frame)
        elif self.etype == "pumpkin":
            draw_pumpkin_boss(surf, ix, iy, self.frame, self.hp/self.max_hp)
        if self.hp < self.max_hp:
            bar_w = 50
            ratio = self.hp / self.max_hp
            bx2 = ix - bar_w//2
            by2 = iy - 55
            pygame.draw.rect(surf, C_RED,   (bx2, by2, bar_w, 6))
            pygame.draw.rect(surf, C_YELLOW if ratio<0.4 else (50,220,50),
                             (bx2, by2, int(bar_w*ratio), 6))
            pygame.draw.rect(surf, C_WHITE, (bx2, by2, bar_w, 6), 1)

# ─────────────────────────────────────────────
#  PARALLAX BACKGROUND
# ─────────────────────────────────────────────
class Background:
    def __init__(self):
        self.stars  = [(random.randint(0,W), random.randint(0,H//2),
                        random.uniform(0.5,2.0),
                        random.choice([C_PURPLE,C_PINK,C_WHITE]))
                       for _ in range(120)]
        self.moon_x = W*3//4
        self.moon_y = 100

    def draw(self, surf, cam_x=0, frame=0):
        draw_gradient_rect(surf, (8,5,18),  (25,12,50), (0,0,W,H//2))
        draw_gradient_rect(surf, (25,12,50),(40,20,70), (0,H//2,W,H//2))

        mx = int(self.moon_x - cam_x*0.05) % W
        pygame.draw.circle(surf, (240,230,255), (mx, self.moon_y), 45)
        pygame.draw.circle(surf, (200,190,230), (mx-10, self.moon_y-8), 18)
        draw_glow(surf, (200,180,255), mx, self.moon_y, 45, 25)

        for sx2, sy2, sz2, sc2 in self.stars:
            twinkle = 0.6 + 0.4*math.sin(frame*0.05 + sx2*0.1)
            a = int(200 * twinkle)
            pygame.draw.circle(surf, (*sc2[:3], min(255,a)),
                               (int(sx2 - cam_x*sz2*0.01) % W, sy2), int(sz2))

        for layer, (col, factor) in enumerate([
            ((30,15,50), 0.15), ((45,20,65), 0.25)]):
            pts = [(0, H)]
            for mx2 in range(0, W+60, 60):
                px = (mx2 - int(cam_x*factor)) % (W+60)
                height = (150 + int(80*math.sin(mx2*0.018+layer)) +
                          int(60*math.sin(mx2*0.033+layer+1)))
                pts.append((px-60, H-80+height))
            pts.append((W, H))
            if len(pts) >= 3:
                pygame.draw.polygon(surf, col, pts)

# ─────────────────────────────────────────────
#  COLLECTIBLE
# ─────────────────────────────────────────────
@dataclass
class Coin:
    x: float; y: float
    alive: bool = True
    frame: int  = 0
    value: int  = 10

    @property
    def rect(self): return pygame.Rect(self.x-8, self.y-8, 16, 16)

    def draw(self, surf):
        if not self.alive: return
        bob = math.sin(self.frame*0.12)*3
        sz  = 8 + int(2*math.sin(self.frame*0.15))
        draw_star(surf, C_GOLD, int(self.x), int(self.y+bob), sz, 5)
        draw_glow(surf, C_GOLD, int(self.x), int(self.y+bob), sz, 40)
        self.frame += 1

# ─────────────────────────────────────────────
#  PLAYER
# ─────────────────────────────────────────────
class Player:
    def __init__(self): self.reset()

    def reset(self):
        self.x = 200.0; self.y = 400.0
        self.vx = 0.0;  self.vy = 0.0
        self.on_ground   = False
        self.facing      = "right"
        self.hp          = 5; self.max_hp = 5
        self.invincible  = 0
        self.frame       = 0
        self.bullets: List[Bullet] = []
        self.shoot_cd    = 0
        self.score       = 0
        self.combo       = 0; self.combo_timer = 0
        self.power_type  = None
        self.power_timer = 0
        self.speed_mult  = 1.0
        self.jump_count  = 0
        self.max_jumps   = 2

    @property
    def rect(self):
        return pygame.Rect(self.x-16, self.y-36, 32, 60)

    def handle_input(self, keys):
        spd = 4.5 * self.speed_mult
        if   keys[pygame.K_LEFT]  or keys[pygame.K_a]:
            self.vx = -spd; self.facing = "left"
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vx =  spd; self.facing = "right"
        else:
            self.vx *= 0.75

    def try_jump(self):
        if self.jump_count < self.max_jumps:
            self.vy = -13.5 if self.jump_count == 0 else -11.0
            self.jump_count += 1
            play("jump")
            spawn_particles(self.x, self.y+20, C_PURPLE, 8, 3, 0.2)

    def try_shoot(self):
        if self.shoot_cd > 0: return
        spd   = 10 if self.power_type == "speed" else 7
        power = 2  if self.power_type in ("fire","star") else 1
        col   = {"fire":C_RED,"ice":C_CYAN,"star":C_GOLD}.get(self.power_type, C_PINK)
        bvx   = spd * (1 if self.facing=="right" else -1)
        self.bullets.append(Bullet(
            self.x + (20 if self.facing=="right" else -20),
            self.y-10, bvx, 0, "player", power, color=col))
        play("shoot")
        self.shoot_cd = 12 if self.power_type == "fire" else 20

    def update(self, platforms, platform_styles):
        self.frame += 1
        self.vy += GRAVITY
        if self.invincible  > 0: self.invincible  -= 1
        if self.shoot_cd    > 0: self.shoot_cd    -= 1
        if self.power_timer > 0:
            self.power_timer -= 1
            if self.power_timer == 0:
                self.power_type = None
                self.speed_mult = 1.0
        if self.combo_timer > 0:
            self.combo_timer -= 1
        else:
            self.combo = 0

        self.x += self.vx
        self.x  = max(20, min(W-20, self.x))

        self.y += self.vy
        self.on_ground = False
        for i, p in enumerate(platforms):
            style = platform_styles[i] if i < len(platform_styles) else "normal"
            if (self.vy >= 0 and
                p.left < self.x < p.right and
                p.top  < self.y < p.bottom):
                if style == "spiky":
                    self.take_damage(1)
                elif style == "bounce":
                    self.vy = -16
                    spawn_particles(self.x, self.y, C_LPURPLE, 10, 4, 0.2)
                else:
                    self.y = p.top
                    self.vy = 0
                    self.on_ground = True
                    self.jump_count = 0

        if self.y > H + 100:
            self.take_damage(2)
            self.y = 300; self.vy = 0

        for b in self.bullets:
            b.update(platforms)
        self.bullets = [b for b in self.bullets if b.alive]

    def take_damage(self, amount=1):
        if self.invincible > 0: return False
        if self.power_type == "ice": amount = max(0, amount-1)
        self.hp -= amount
        self.invincible = 80
        play("hit")
        spawn_particles(self.x, self.y, C_RED, 12, 4, 0.15)
        return True

    def pickup_power(self, ptype):
        self.power_type  = ptype
        self.power_timer = 600
        if ptype == "speed": self.speed_mult = 1.8
        if ptype == "heart":
            self.hp = min(self.max_hp+1, 8)
            self.max_hp = min(8, self.max_hp+1)
            self.power_type  = None
            self.power_timer = 0
        play("pickup")

    def draw(self, surf):
        draw_kuromi(surf, int(self.x), int(self.y), self.frame,
                    self.facing, invincible=(self.invincible>0),
                    power_type=self.power_type)
        for b in self.bullets:
            b.draw(surf)

# ─────────────────────────────────────────────
#  HUD
# ─────────────────────────────────────────────
def draw_hud(surf, player, level, frame):
    for i in range(player.max_hp):
        hx = 20 + i*36; hy = 20
        col = C_PINK if i < player.hp else (60, 30, 50)
        pygame.draw.circle(surf, col, (hx-5, hy-3), 7)
        pygame.draw.circle(surf, col, (hx+5, hy-3), 7)
        pygame.draw.polygon(surf, col, [(hx-11,hy-1),(hx+11,hy-1),(hx,hy+12)])

    outline_text(surf, FONT_MED, f"✦ {player.score:06d}", C_GOLD, C_BLACK, W//2, 12)
    outline_text(surf, FONT_SMALL, f"Stage {level}", C_LPURPLE, C_BLACK, W-80, 16)

    if player.combo >= 2:
        alpha = min(255, player.combo_timer * 8)
        cs = FONT_MED.render(f"x{player.combo} COMBO!", True, C_YELLOW)
        cs.set_alpha(alpha)
        surf.blit(cs, (W//2 - cs.get_width()//2, 60))

    if player.power_type and player.power_timer > 0:
        bar_w = 160
        ratio = player.power_timer / 600
        col   = {"fire":C_RED,"ice":C_CYAN,"star":C_GOLD,
                 "speed":C_YELLOW}.get(player.power_type, C_PINK)
        pygame.draw.rect(surf, C_DARK,  (W-bar_w-20, 45, bar_w, 12), border_radius=6)
        pygame.draw.rect(surf, col,     (W-bar_w-20, 45, int(bar_w*ratio), 12), border_radius=6)
        pygame.draw.rect(surf, C_WHITE, (W-bar_w-20, 45, bar_w, 12), 1, border_radius=6)
        lbl = FONT_TINY.render(player.power_type.upper(), True, col)
        surf.blit(lbl, (W-bar_w-22-lbl.get_width(), 45))

    jx, jy = 20, H-30
    for i in range(player.max_jumps):
        col = C_LPURPLE if player.jump_count <= i else (50,30,70)
        pygame.draw.circle(surf, col, (jx+i*20, jy), 7)

# ─────────────────────────────────────────────
#  LEVEL DEFINITIONS
# ─────────────────────────────────────────────
def build_level(level_num):
    platforms, styles, enemies, power_ups, coins = [], [], [], [], []

    def add_plat(x, y, w, style="normal"):
        platforms.append(pygame.Rect(x, y, w, TILE))
        styles.append(style)

    add_plat(0, H-TILE, W, "normal")   # ground

    if level_num == 1:
        add_plat(200, 550, 200)
        add_plat(500, 460, 180)
        add_plat(750, 380, 200)
        add_plat(400, 300, 150, "cloud")
        add_plat(650, 220, 180, "cloud")
        add_plat(900, 300, 160)
        add_plat(1100,400, 150)
        add_plat(50,  480, 120)
        add_plat(150, 380, 100, "bounce")
        enemies += [
            Enemy(600,420,"ghost",3,3, 1.0,patrol_left=450,patrol_right=750,bullet_color=C_PURPLE),
            Enemy(850,340,"bat",  2,2, 1.5,patrol_left=700,patrol_right=1000),
            Enemy(300,510,"ghost",3,3,-1.0,patrol_left=150,patrol_right=450,bullet_color=C_LPURPLE),
        ]
        power_ups += [PowerUp(500,420,"fire"), PowerUp(900,260,"star"), PowerUp(150,440,"heart")]
        coins += [Coin(x2,y2) for x2,y2 in [
            (250,520),(530,430),(780,350),(420,270),
            (680,190),(950,270),(1120,370),(100,450)]]
        goal = pygame.Rect(1160, H-TILE-60, 60, 60)

    elif level_num == 2:
        plats_data = [
            (100,580,150,"normal"),(250,500,180,"cloud"),(420,430,150,"normal"),
            (580,360,160,"bounce"),(720,290,150,"cloud"),(870,350,150,"spiky"),
            (1000,280,150,"normal"),(1150,350,150,"cloud"),(900,480,150,"normal"),
            (700,500,160,"bounce"),(500,540,150,"normal"),(300,400,150,"cloud"),
            (150,300,150,"normal"),
        ]
        for x2,y2,w2,st2 in plats_data:
            add_plat(x2, y2, w2, st2)
        enemies += [
            Enemy(400,390,"ghost",4,4, 1.2,patrol_left=250,patrol_right=550,bullet_color=C_PINK),
            Enemy(700,250,"bat",  3,3, 2.0,patrol_left=600,patrol_right=900),
            Enemy(600,320,"ghost",4,4,-1.2,patrol_left=480,patrol_right=720,bullet_color=C_RED),
            Enemy(900,240,"bat",  3,3, 1.5,patrol_left=800,patrol_right=1050),
            Enemy(1100,310,"ghost",4,4,-1.0,patrol_left=950,patrol_right=1200,bullet_color=C_LPURPLE),
        ]
        power_ups += [PowerUp(280,460,"ice"), PowerUp(730,250,"speed"), PowerUp(1000,240,"star")]
        coins += [Coin(c2[0],c2[1]) for c2 in [
            (260,460),(440,390),(590,320),(740,260),(880,310),
            (1010,240),(1160,310),(500,500),(700,460),(310,360)]]
        goal = pygame.Rect(1180, 300, 60, 60)

    elif level_num == 3:
        add_plat(0, H-TILE*2, W)
        add_plat(100,500,200,"cloud"); add_plat(400,420,200)
        add_plat(700,340,200,"cloud"); add_plat(1000,420,200)
        add_plat(250,280,150,"bounce"); add_plat(600,200,150,"cloud"); add_plat(900,280,150)
        boss = Enemy(640, H-TILE*2-60, "pumpkin", 30, 30, 2.0,
                     patrol_left=200, patrol_right=1080, bullet_color=(255,150,0))
        enemies.append(boss)
        power_ups += [
            PowerUp(150,460,"fire"), PowerUp(450,380,"star"),
            PowerUp(750,300,"ice"),  PowerUp(1050,380,"heart"),
        ]
        coins += [Coin(c2[0],c2[1]) for c2 in [
            (200,480),(430,380),(660,160),(920,250),(1080,380),(300,240),(700,500),(500,380)]]
        goal = pygame.Rect(-9999, -9999, 60, 60)

    else:
        prev_y = H - TILE*2
        for i in range(25):
            xr = random.randint(50, W-250)
            prev_y = max(200, prev_y - random.randint(60,120))
            st2 = random.choice(["normal","cloud","bounce","spiky"])
            add_plat(xr, prev_y, random.randint(120,220), st2)
        for _ in range(8):
            ex2 = random.randint(100,W-100); ey2 = random.randint(200,H-100)
            et2 = random.choice(["ghost","bat"])
            enemies.append(Enemy(ex2,ey2,et2,3,3,random.uniform(-1.5,1.5),
                patrol_left=max(50,ex2-200), patrol_right=min(W-50,ex2+200)))
        for _ in range(5):
            power_ups.append(PowerUp(random.randint(100,W-100),random.randint(200,H-150),
                random.choice(["fire","ice","star","speed","heart"])))
        for _ in range(15):
            coins.append(Coin(random.randint(80,W-80),random.randint(150,H-120)))
        goal = pygame.Rect(W//2-30, 160, 60, 60)

    return platforms, styles, enemies, power_ups, coins, goal

# ─────────────────────────────────────────────
#  FLOATING TEXT
# ─────────────────────────────────────────────
@dataclass
class FloatText:
    x:float; y:float; text:str; color:Tuple
    life:int=60; max_life:int=60; vy:float=-1.5

    def update(self): self.y += self.vy; self.life -= 1
    @property
    def alive(self): return self.life > 0

    def draw(self, surf):
        a   = max(0, int(255 * self.life / self.max_life))
        lbl = FONT_SMALL.render(self.text, True, self.color)
        lbl.set_alpha(a)
        surf.blit(lbl, (int(self.x)-lbl.get_width()//2, int(self.y)))

float_texts: List[FloatText] = []

# ─────────────────────────────────────────────
#  SCREENS
# ─────────────────────────────────────────────
def screen_title():
    frame = 0
    while True:
        clock.tick(FPS)
        for e in pygame.event.get():
            if e.type == pygame.QUIT: return "quit"
            if e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_RETURN, pygame.K_SPACE): return "play"
                if e.key == pygame.K_ESCAPE: return "quit"
        frame += 1
        draw_gradient_rect(screen, (5,3,12),(20,8,40),(0,0,W,H))

        for i in range(10):
            sx2 = (i*130 + frame//2) % W
            sy2 = 100 + int(50*math.sin(frame*0.04+i))
            tmp = pygame.Surface((32,32), pygame.SRCALPHA)
            draw_mini_skull(tmp, (*C_PURPLE,80), 16, 16, 12)
            screen.blit(tmp, (sx2, sy2))

        outline_text(screen, FONT_BIG, "✦ KUROMI'S ✦", C_PINK, C_BLACK, W//2, 100)
        outline_text(screen, FONT_BIG, "DARK ADVENTURE", C_LPURPLE, C_BLACK, W//2, 180)

        draw_kuromi(screen, W//2, 420, frame, "right", size=1.8)
        draw_glow(screen, C_PURPLE, W//2, 420, 90, 30)

        alpha = int(180 + 75*math.sin(frame*0.08))
        lbl = FONT_MED.render("Press SPACE or ENTER to Begin", True, C_WHITE)
        lbl.set_alpha(alpha)
        screen.blit(lbl, (W//2-lbl.get_width()//2, 580))

        for i2, c2 in enumerate([
            "← → / A D  Move  |  SPACE / W  Jump (Double Jump!)",
            "Z / J  Shoot      |  P  Pause  |  ESC  Quit"]):
            lbl2 = FONT_TINY.render(c2, True, C_SKULL)
            screen.blit(lbl2, (W//2 - lbl2.get_width()//2, 640+i2*20))

        pygame.display.flip()

def screen_game_over(score):
    frame = 0
    while True:
        clock.tick(FPS)
        for e in pygame.event.get():
            if e.type == pygame.QUIT: return "quit"
            if e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_RETURN, pygame.K_SPACE): return "play"
                if e.key == pygame.K_ESCAPE: return "quit"
        frame += 1
        draw_gradient_rect(screen,(15,5,5),(40,10,20),(0,0,W,H))
        draw_kuromi(screen, W//2, 380, frame, "right", size=1.2, invincible=True)
        outline_text(screen, FONT_BIG, "GAME OVER", C_RED, C_BLACK, W//2, 150)
        outline_text(screen, FONT_MED, f"Score: {score:06d}", C_GOLD, C_BLACK, W//2, 270)
        lbl = FONT_SMALL.render("Press SPACE to Retry", True, C_WHITE)
        lbl.set_alpha(int(180+75*math.sin(frame*0.08)))
        screen.blit(lbl, (W//2-lbl.get_width()//2, 490))
        if random.random() < 0.3:
            spawn_particles(random.randint(0,W), random.randint(0,H//2),
                            C_RED, 1, 1, 0.05, "star")
        for p in particles: p.update(); p.draw(screen)
        particles[:] = [p for p in particles if p.alive]
        pygame.display.flip()

def screen_win(score):
    frame = 0
    while True:
        clock.tick(FPS)
        for e in pygame.event.get():
            if e.type == pygame.QUIT: return "quit"
            if e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_RETURN, pygame.K_SPACE): return "play"
                if e.key == pygame.K_ESCAPE: return "quit"
        frame += 1
        draw_gradient_rect(screen,(5,3,18),(20,8,50),(0,0,W,H))
        if random.random() < 0.5:
            spawn_particles(random.randint(0,W), random.randint(H//2,H),
                random.choice([C_PINK,C_PURPLE,C_GOLD,C_CYAN]), 2, 3, -0.05, "star")
        for p in particles: p.update(); p.draw(screen)
        particles[:] = [p for p in particles if p.alive]
        draw_kuromi(screen, W//2, 350, frame, "right", size=1.8, power_type="star")
        outline_text(screen, FONT_BIG, "✦ YOU WIN! ✦", C_GOLD, C_BLACK, W//2, 120)
        outline_text(screen, FONT_MED, f"Final Score: {score:06d}", C_PINK, C_BLACK, W//2, 230)
        outline_text(screen, FONT_SMALL, "Thanks for playing!", C_WHITE, C_BLACK, W//2, 490)
        lbl = FONT_SMALL.render("Press SPACE to Play Again", True, C_LPURPLE)
        lbl.set_alpha(int(180+75*math.sin(frame*0.08)))
        screen.blit(lbl, (W//2-lbl.get_width()//2, 540))
        pygame.display.flip()

# ─────────────────────────────────────────────
#  MAIN GAME LOOP
# ─────────────────────────────────────────────
def run_game():
    global particles, float_texts
    particles   = []
    float_texts = []

    player    = Player()
    level_num = 1
    total_score = 0
    bg = Background()

    platforms, styles, enemies, power_ups, coins = [], [], [], [], []
    goal  = None
    cam_x = 0.0

    def load_level(lv):
        nonlocal platforms, styles, enemies, power_ups, coins, goal, cam_x
        platforms, styles, enemies, power_ups, coins, goal = build_level(lv)
        cam_x = 0.0
        particles.clear()
        float_texts.clear()
        player.x, player.y = 200, 400
        player.vx = player.vy = 0
        player.jump_count = 0

    load_level(level_num)

    frame          = 0
    boss_dead      = False
    paused         = False
    shake          = 0
    enemy_bullets: List[Bullet] = []

    while True:
        clock.tick(FPS)
        frame += 1

        # ── EVENTS ──────────────────────────────
        for e in pygame.event.get():
            if e.type == pygame.QUIT: return "quit"
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE: return "quit"
                if e.key in (pygame.K_UP, pygame.K_w, pygame.K_SPACE):
                    player.try_jump()
                if e.key in (pygame.K_z, pygame.K_j):
                    player.try_shoot()
                if e.key == pygame.K_p: paused = not paused

        if paused:
            overlay = pygame.Surface((W,H), pygame.SRCALPHA)
            overlay.fill((0,0,0,120))
            screen.blit(overlay,(0,0))
            outline_text(screen, FONT_BIG, "PAUSED", C_WHITE, C_BLACK, W//2, H//2-40)
            pygame.display.flip()
            continue

        keys = pygame.key.get_pressed()
        player.handle_input(keys)

        # ── UPDATE ───────────────────────────────
        player.update(platforms, styles)

        target_cam = player.x - W//3
        cam_x += (target_cam - cam_x) * 0.1

        for en in enemies:
            en.update(player.x + cam_x, player.y, platforms, enemy_bullets)

        for b in enemy_bullets:
            b.update(platforms)
        enemy_bullets[:] = [b for b in enemy_bullets if b.alive]

        # ── COLLISIONS: player bullets vs enemies ──
        for b in player.bullets:
            if not b.alive: continue
            for en in enemies:
                if not en.alive: continue
                rb = pygame.Rect(b.x-6, b.y-6, 12, 12)
                if rb.colliderect(en.rect):
                    en.hp -= b.power
                    b.alive = False
                    play("boss_hit" if en.etype=="pumpkin" else "hit")
                    if en.etype == "pumpkin": shake = 8
                    spawn_particles(b.x, b.y, C_YELLOW, 8, 3, 0.1, "star")
                    if en.hp <= 0:
                        en.alive = False
                        player.combo += 1
                        player.combo_timer = 120
                        pts = 100 * player.combo * (3 if en.etype=="pumpkin" else 1)
                        player.score += pts
                        spawn_death_burst(en.x, en.y)
                        float_texts.append(FloatText(en.x, en.y-40,
                            f"+{pts}" + (f"  COMBO x{player.combo}" if player.combo>1 else ""),
                            C_GOLD if player.combo>1 else C_WHITE))

        # ── COLLISIONS: enemy bullets vs player ───
        for b in enemy_bullets:
            if not b.alive: continue
            rb = pygame.Rect(b.x-6, b.y-6, 12, 12)
            if rb.colliderect(player.rect):
                if player.take_damage(1):
                    b.alive = False; shake = 5
                    float_texts.append(FloatText(player.x, player.y-50, "-1", C_RED))

        # ── COLLISIONS: enemies vs player ─────────
        for en in enemies:
            if not en.alive: continue
            if en.rect.colliderect(player.rect):
                if player.take_damage(1):
                    shake = 5
                    float_texts.append(FloatText(player.x, player.y-50, "OW!", C_RED))

        # ── COLLECT COINS ─────────────────────────
        for c in coins:
            if c.alive and c.rect.colliderect(player.rect):
                c.alive = False
                player.score += c.value
                float_texts.append(FloatText(c.x, c.y-20, f"+{c.value}", C_GOLD))
                spawn_particles(c.x, c.y, C_GOLD, 6, 3, 0.05, "star")

        # ── COLLECT POWER-UPS ─────────────────────
        for pu in power_ups:
            if pu.alive and pu.rect.colliderect(player.rect):
                pu.alive = False
                player.pickup_power(pu.ptype)
                spawn_particles(pu.x, pu.y, C_PINK, 14, 4, 0.1, "star")
                float_texts.append(FloatText(pu.x, pu.y-30, pu.ptype.upper()+"!", C_PINK))
            pu.update()

        # ── BOSS DEATH ────────────────────────────
        if level_num == 3 and not boss_dead:
            if not any(en.alive and en.etype=="pumpkin" for en in enemies):
                boss_dead = True
                goal = pygame.Rect(W//2-30, H-TILE-100, 60, 60)
                play("level_up")
                for _ in range(40):
                    spawn_particles(W//2, H//2,
                        random.choice([C_GOLD,C_PINK,C_PURPLE,C_CYAN]),
                        2, 6, 0.1, "star")

        # ── REACH GOAL ────────────────────────────
        if goal and player.rect.colliderect(goal):
            play("level_up")
            total_score += player.score
            player.score = 0
            level_num += 1
            boss_dead = False
            if level_num > 3:
                return ("win", total_score + player.score)
            load_level(level_num)
            enemy_bullets.clear()
            float_texts.append(FloatText(W//2, H//2,
                f"STAGE {level_num}!", C_GOLD, life=120, max_life=120))

        # ── PLAYER DEATH ──────────────────────────
        if player.hp <= 0:
            play("death")
            spawn_death_burst(player.x, player.y)
            return ("game_over", total_score + player.score)

        # ── UPDATE PARTICLES & TEXTS ──────────────
        for p in particles: p.update()
        particles[:] = [p for p in particles if p.alive]
        for ft in float_texts: ft.update()
        float_texts[:] = [ft for ft in float_texts if ft.alive]

        # Ambient skull rain (limited to avoid particle overload)
        if frame % 30 == 0 and len(particles) < 200:
            spawn_particles(random.randint(0,W), H+10,
                C_PURPLE, 1, 0, -0.5, "skull", 5)

        # ── DRAW ──────────────────────────────────
        sx2, sy2 = 0, 0
        if shake > 0:
            sx2 = random.randint(-shake, shake)
            sy2 = random.randint(-shake, shake)
            shake -= 1

        surf = pygame.Surface((W, H))
        bg.draw(surf, cam_x, frame)

        # Platforms
        for i, p in enumerate(platforms):
            pr = pygame.Rect(p.x - int(cam_x), p.y, p.w, p.h)
            draw_platform(surf, pr, styles[i] if i < len(styles) else "normal", frame)

        # Goal portal
        if goal and goal.x > -1000:
            gx2 = goal.x - int(cam_x); gy2 = goal.y
            draw_glow(surf, C_GOLD, gx2+30, gy2+30, 40, 60)
            draw_star(surf, C_GOLD, gx2+30, gy2+30,
                      20 + int(5*math.sin(frame*0.1)), 6)
            lbl = FONT_TINY.render("GOAL" if level_num<3 else "★ CLEAR ★", True, C_GOLD)
            surf.blit(lbl, (gx2+30-lbl.get_width()//2, gy2-22))

        # Coins
        for c in coins:
            if c.alive:
                cd = Coin(c.x - cam_x, c.y, c.alive, c.frame, c.value)
                cd.draw(surf)

        # Power-ups
        for pu in power_ups:
            if pu.alive:
                pd = PowerUp(pu.x - cam_x, pu.y, pu.ptype, pu.alive, pu.frame)
                pd.draw(surf)

        # Enemies
        for en in enemies:
            if not en.alive: continue
            import copy
            ed = copy.copy(en)
            ed.x -= cam_x
            ed.draw(surf)

        # Enemy bullets
        for b in enemy_bullets:
            import copy
            bd = copy.copy(b)
            bd.x -= cam_x
            bd.draw(surf)

        # Player + bullets (on separate alpha surface for invincibility flash)
        psf = pygame.Surface((W,H), pygame.SRCALPHA)
        draw_kuromi(psf, int(player.x - cam_x), int(player.y),
                    player.frame, player.facing,
                    invincible=(player.invincible>0),
                    power_type=player.power_type)
        for b in player.bullets:
            import copy
            bd2 = copy.copy(b)
            bd2.x -= cam_x
            bd2.draw(psf)
        surf.blit(psf, (0,0))

        # Particles & float texts
        for p in particles: p.draw(surf)
        for ft in float_texts: ft.draw(surf)

        # HUD
        draw_hud(surf, player, level_num, frame)

        # Boss HP bar
        for en in enemies:
            if en.alive and en.etype == "pumpkin":
                bw2 = 500; bx2 = W//2 - bw2//2; by2 = H-60
                draw_gradient_rect(surf, C_RED, (120,10,10), (bx2,by2,bw2,24))
                ratio = en.hp / en.max_hp
                draw_gradient_rect(surf, C_YELLOW, C_GOLD, (bx2,by2,int(bw2*ratio),24))
                pygame.draw.rect(surf, C_WHITE, (bx2,by2,bw2,24), 2)
                lbl = FONT_SMALL.render("PUMPKIN KING", True, C_WHITE)
                surf.blit(lbl, (bx2, by2-26))

        screen.blit(surf, (sx2, sy2))
        pygame.display.flip()

    return ("quit", 0)

# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────
def main():
    while True:
        action = screen_title()
        if action == "quit": break

        result = run_game()
        if isinstance(result, tuple):
            outcome, score = result
        else:
            outcome, score = result, 0

        if outcome == "quit": break
        elif outcome == "game_over":
            act2 = screen_game_over(score)
            if act2 == "quit": break
        elif outcome == "win":
            act2 = screen_win(score)
            if act2 == "quit": break

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
