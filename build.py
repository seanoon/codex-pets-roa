#!/usr/bin/env python3
import os
import json
import zipfile
import math
from collections import deque
from PIL import Image, ImageOps, ImageDraw

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
from collections import deque

print("=== STARTING V6 BUILD ===")

# ==========================================
# 1. PROCESS BASE IDLE & ACTION (roa_chibi_v3)
# ==========================================
v3_path = os.path.join(ASSETS_DIR, "chibi_base.jpg")
img_v3 = Image.open(v3_path).convert("RGBA")
w3, h3 = img_v3.size
pix3 = img_v3.load()

def is_near_white(r, g, b):
    max_c = max(r, g, b)
    min_c = min(r, g, b)
    sat = max_c - min_c
    return min_c > 220 and sat < 15

# Outer flood fill ONLY
visited_bg3 = [[False] * h3 for _ in range(w3)]
q3 = deque()
for x in range(w3):
    for y in [0, h3 - 1]:
        if is_near_white(*pix3[x, y][:3]):
            q3.append((x, y))
            visited_bg3[x][y] = True
for y in range(h3):
    for x in [0, w3 - 1]:
        if is_near_white(*pix3[x, y][:3]) and not visited_bg3[x][y]:
            q3.append((x, y))
            visited_bg3[x][y] = True

while q3:
    cx, cy = q3.popleft()
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        nx, ny = cx + dx, cy + dy
        if 0 <= nx < w3 and 0 <= ny < h3 and not visited_bg3[nx][ny]:
            if is_near_white(*pix3[nx, ny][:3]):
                visited_bg3[nx][ny] = True
                q3.append((nx, ny))

# Find specific enclosed arm holes in v3
# Pose 3 waving arm: X=[1251, 1298], Y=[370, 407]
# (Note: Pose 2 jump has arms raised high with no enclosed holes; X=[981, 1023] is the white tail tip!)
visited_holes3 = [[False] * h3 for _ in range(w3)]
holes_to_clear3 = []

for x in range(w3):
    for y in range(h3):
        if not visited_bg3[x][y] and not visited_holes3[x][y] and is_near_white(*pix3[x, y][:3]):
            comp = []
            q = deque([(x, y)])
            visited_holes3[x][y] = True
            while q:
                cx, cy = q.popleft()
                comp.append((cx, cy))
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < w3 and 0 <= ny < h3:
                        if not visited_bg3[nx][ny] and not visited_holes3[nx][ny]:
                            if is_near_white(*pix3[nx, ny][:3]):
                                visited_holes3[nx][ny] = True
                                q.append((nx, ny))
            min_x = min(p[0] for p in comp)
            max_x = max(p[0] for p in comp)
            min_y = min(p[1] for p in comp)
            max_y = max(p[1] for p in comp)
            # Pose 3 waving arm hole ONLY
            if (1240 <= min_x and max_x <= 1310 and 360 <= min_y and max_y <= 420):
                holes_to_clear3.append(comp)

# Apply transparency ONLY to background and verified arm holes
for x in range(w3):
    for y in range(h3):
        if visited_bg3[x][y]:
            pix3[x, y] = (255, 255, 255, 0)

for comp in holes_to_clear3:
    for px, py in comp:
        pix3[px, py] = (255, 255, 255, 0)

# Extract 4 main poses from v3
visited_comp3 = [[False] * h3 for _ in range(w3)]
components3 = []
for x in range(w3):
    for y in range(h3):
        if pix3[x, y][3] > 0 and not visited_comp3[x][y]:
            comp = []
            q = deque([(x, y)])
            visited_comp3[x][y] = True
            while q:
                cx, cy = q.popleft()
                comp.append((cx, cy))
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < w3 and 0 <= ny < h3 and not visited_comp3[nx][ny]:
                        if pix3[nx, ny][3] > 0:
                            visited_comp3[nx][ny] = True
                            q.append((nx, ny))
            if len(comp) > 1000:
                components3.append(comp)

components3.sort(key=lambda c: min(p[0] for p in c))
poses_v3 = []
for idx, comp in enumerate(components3):
    min_x = min(p[0] for p in comp)
    max_x = max(p[0] for p in comp)
    min_y = min(p[1] for p in comp)
    max_y = max(p[1] for p in comp)
    p_img = Image.new("RGBA", (max_x - min_x + 1, max_y - min_y + 1), (0, 0, 0, 0))
    p_pix = p_img.load()
    for px, py in comp:
        p_pix[px - min_x, py - min_y] = pix3[px, py]
    poses_v3.append(p_img)

idle_raw = poses_v3[0]
jump_raw = poses_v3[2]
wave_raw = poses_v3[3]

# 1B. Apply official cloud patterns to idle and jump dresses
def create_pixel_cloud(w, h):
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([int(w * 0.05), int(h * 0.2), int(w * 0.55), int(h * 0.98)], fill=(255, 255, 255, 255))
    draw.ellipse([int(w * 0.45), int(h * 0.25), int(w * 0.95), int(h * 0.98)], fill=(255, 255, 255, 255))
    draw.ellipse([int(w * 0.22), int(h * 0.02), int(w * 0.78), int(h * 0.92)], fill=(255, 255, 255, 255))
    draw.rectangle([int(w * 0.15), int(h * 0.35), int(w * 0.85), int(h * 0.98)], fill=(255, 255, 255, 255))
    return img

def apply_dress_clouds(base_img, offset_x=0, offset_y=0):
    img = base_img.copy()
    pix = img.load()
    w, h = img.size
    clouds_spec = [
        # Lower tier (near hem, Y around 508-540)
        (78 + offset_x, 508 + offset_y, 36, 22),
        (116 + offset_x, 524 + offset_y, 40, 24),
        (156 + offset_x, 524 + offset_y, 40, 24),
        (196 + offset_x, 508 + offset_y, 36, 22),
        # Mid tier (higher up, Y around 465-495)
        (92 + offset_x, 465 + offset_y, 26, 16),
        (124 + offset_x, 480 + offset_y, 30, 18),
        (160 + offset_x, 480 + offset_y, 30, 18),
        (194 + offset_x, 465 + offset_y, 26, 16),
    ]
    for cx, cy, cw, ch in clouds_spec:
        c_img = create_pixel_cloud(cw, ch)
        cpix = c_img.load()
        for py in range(ch):
            for px in range(cw):
                tx, ty = cx + px, cy + py
                if 0 <= tx < w and 0 <= ty < h:
                    ca = cpix[px, py][3]
                    if ca > 50:
                        dr, dg, db, da = pix[tx, ty]
                        if 150 <= dr <= 235 and 185 <= dg <= 245 and db >= 220:
                            alpha = ca / 255.0
                            nr = int(dr * (1 - alpha) + 255 * alpha)
                            ng = int(dg * (1 - alpha) + 255 * alpha)
                            nb = int(db * (1 - alpha) + 255 * alpha)
                            pix[tx, ty] = (nr, ng, nb, da)
    return img

idle_raw = apply_dress_clouds(idle_raw, offset_x=0, offset_y=0)
jump_raw = apply_dress_clouds(jump_raw, offset_x=18, offset_y=0)
wave_raw = apply_dress_clouds(wave_raw, offset_x=0, offset_y=0)
print(f"Applied official cloud pattern to Idle ({idle_raw.size}), Jump ({jump_raw.size}), and Wave ({wave_raw.size})")
# ==========================================
# 3. BUILD SPRITESHEET ATLAS
# ==========================================
CELL_W = 192
CELL_H = 208
COLS = 8
ROWS = 11

TOTAL_W = CELL_W * COLS
TOTAL_H = CELL_H * ROWS
target_char_h = 175

# 3A. Prepare IDLE Upper Sway (Seamless bending sway, 100% NO cut lines!)
scale = target_char_h / idle_raw.height
scaled_w = int(idle_raw.width * scale)
scaled_h = target_char_h
idle_scaled = idle_raw.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)

# Pivot is around skirt bottom / feet (scaled_h - 45) -> lower body 100% FIXED
pivot_y = scaled_h - 45
pos_x_base = (CELL_W - scaled_w) // 2
pos_y_base = CELL_H - scaled_h - 12

def make_upper_sway_cell(sway_pixels, y_bob=0):
    canvas = Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0))
    pad_w = scaled_w + 30
    pad = Image.new("RGBA", (pad_w, scaled_h), (0, 0, 0, 0))
    pad.paste(idle_scaled, (15, 0), idle_scaled)
    
    shifted = Image.new("RGBA", (pad_w, scaled_h), (0, 0, 0, 0))
    for y in range(scaled_h):
        if y >= pivot_y:
            weight = 0.0 # 100% FIXED lower body
        else:
            weight = ((pivot_y - y) / pivot_y) ** 1.3
        dx = sway_pixels * weight
        line = pad.crop((0, y, pad_w, y + 1))
        line_shifted = line.transform(
            (pad_w, 1),
            Image.Transform.AFFINE,
            (1, 0, -dx, 0, 1, 0),
            resample=Image.Resampling.BILINEAR
        )
        shifted.paste(line_shifted, (0, y), line_shifted)
    
    canvas.paste(shifted, (pos_x_base - 15, pos_y_base + y_bob), shifted)
    return canvas

# 8-frame natural sway without any cut lines
sway_shifts = [0.0, 1.8, 3.2, 1.8, 0.0, -1.8, -3.2, -1.8]
sway_bobs = [0, -1, -2, -1, 0, -1, -2, -1]
idle_cells = [make_upper_sway_cell(sw, yb) for sw, yb in zip(sway_shifts, sway_bobs)]

ground_y_in_cell = CELL_H - 12 # 196

# 3B. Prepare RUN Cycle (Frames 1, 2, 3, 4 - v7 Zero-Fringe Master Edition)
# 4 distinct frames: [Frame 1, Frame 2, Frame 3, Frame 4]
# Perfect run cycle with counter-arm swings, bouncing tail, and zero magenta fringe!
run_master_strip = Image.open(os.path.join(ASSETS_DIR, "run_strip.png"))
run_cells_right = [
    run_master_strip.crop((i * CELL_W, 0, (i + 1) * CELL_W, CELL_H))
    for i in range(4)
]
run_cells_left = [ImageOps.mirror(c) for c in run_cells_right]

# 3C. Prepare Jump / Celebration
j_scale = target_char_h / jump_raw.height
jw = int(jump_raw.width * j_scale)
jh = target_char_h
jump_scaled = jump_raw.resize((jw, jh), Image.Resampling.LANCZOS)

def make_jump_cell(offset_y=0):
    c = Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0))
    jx = (CELL_W - jw) // 2
    jy = CELL_H - jh - 12 + offset_y
    c.paste(jump_scaled, (jx, jy), jump_scaled)
    return c

# 3D. Prepare Wave / Greeting (Row 3: Waving Hand Cycle)
arm_isolated = Image.new("RGBA", wave_raw.size, (0, 0, 0, 0))
apix = arm_isolated.load()
wpix = wave_raw.load()
for y in range(290, 430):
    for x in range(230, 313):
        r, g, b, a = wpix[x, y]
        is_hair = (b > r + 30 and b > 140)
        if a > 0 and not is_hair:
            apix[x, y] = (r, g, b, a)
arm_bbox = arm_isolated.getbbox() # (230, 290, 311, 409)
wave_arm_crop = arm_isolated.crop(arm_bbox)

# Base body with hair restored from idle
wave_body = wave_raw.copy()
p0_hair = idle_raw.crop((210, 250, 300, 380))
wbpix = wave_body.load()
for y in range(290, 420):
    for x in range(235, 313):
        wbpix[x, y] = (0, 0, 0, 0)
wave_body.paste(p0_hair, (210, 250), p0_hair)

wave_scale = target_char_h / wave_raw.height
ww = int(wave_raw.width * wave_scale)
wh = target_char_h
wx = (CELL_W - ww) // 2
wy = CELL_H - wh - 12
pivot = (12, 120) # pivot inside wave_arm_crop

wave_angles = [-8, -4, 2, 8, 12, 8, 2, -4]
wave_cells = []
for ang in wave_angles:
    rot_arm = wave_arm_crop.rotate(-ang, resample=Image.Resampling.BICUBIC, center=pivot)
    f = wave_body.copy()
    f.paste(rot_arm, (arm_bbox[0], arm_bbox[1]), rot_arm)
    f_scaled = f.resize((ww, wh), Image.Resampling.LANCZOS)
    c = Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0))
    c.paste(f_scaled, (wx, wy), f_scaled)
    wave_cells.append(c)

# --- EXTRACT ROW 5 (OFFICIAL CRYING STAMP: EEN!) ---
crying_sheet_path = os.path.join(ASSETS_DIR, "crying_sheet.jpg")
cry_sheet = Image.open(crying_sheet_path).convert("RGBA")
csw, csh = cry_sheet.size
ccol_w = csw // 4

cry_raw_frames = []
for col in range(4):
    cell = cry_sheet.crop((col * ccol_w, 0, (col + 1) * ccol_w, csh)).copy()
    cw, ch = cell.size
    cpix = cell.load()
    visited = set()
    q = deque()
    for x in range(cw):
        for y in [0, ch - 1]:
            if cpix[x, y][0] > 240 and cpix[x, y][1] > 240 and cpix[x, y][2] > 240:
                q.append((x, y))
                visited.add((x, y))
    for y in range(ch):
        for x in [0, cw - 1]:
            if cpix[x, y][0] > 240 and cpix[x, y][1] > 240 and cpix[x, y][2] > 240 and (x, y) not in visited:
                q.append((x, y))
                visited.add((x, y))
    while q:
        cx, cy = q.popleft()
        cpix[cx, cy] = (0, 0, 0, 0)
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < cw and 0 <= ny < ch and (nx, ny) not in visited:
                if cpix[nx, ny][0] > 235 and cpix[nx, ny][1] > 235 and cpix[nx, ny][2] > 235:
                    visited.add((nx, ny))
                    q.append((nx, ny))
    cry_raw_frames.append(cell)

cmin_x, cmax_x = cw, 0
cmin_y, cmax_y = ch, 0
for f in cry_raw_frames:
    fpix = f.load()
    for y in range(ch):
        for x in range(cw):
            if fpix[x, y][3] > 0:
                if x < cmin_x: cmin_x = x
                if x > cmax_x: cmax_x = x
                if y < cmin_y: cmin_y = y
                if y > cmax_y: cmax_y = y

cchar_h = cmax_y - cmin_y + 1
c_scale = target_char_h / float(cchar_h)

cry_scaled_frames = []
for f in cry_raw_frames:
    cr = f.crop((cmin_x, cmin_y, cmax_x + 1, cmax_y + 1))
    csw = int(cr.width * c_scale)
    csh = target_char_h
    sc = cr.resize((csw, csh), Image.Resampling.LANCZOS)
    cimg = Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0))
    px = (CELL_W - csw) // 2
    py = CELL_H - csh - 12
    cimg.paste(sc, (px, py), sc)
    cry_scaled_frames.append(cimg)

# 8-frame smooth ping-pong loop: [0, 1, 2, 3, 2, 1, 0, 1]
failed_cells = [cry_scaled_frames[i] for i in [0, 1, 2, 3, 2, 1, 0, 1]]

# 3F. Prepare SLEEP / REST Cycle (Row 10: Special / Rest - Sitting Nodding Nap)
p3_raw = Image.open(os.path.join(ASSETS_DIR, "sleeping_nap.png"))
# scale = 0.228 to match idle head width (83px) perfectly
p3_scale = 0.228
p3_scaled = p3_raw.resize((int(round(p3_raw.width * p3_scale)), int(round(p3_raw.height * p3_scale))), Image.Resampling.LANCZOS)

# Pixel art effect patterns for Zzz
Z_SMALL = [
    "#####",
    "...#.",
    "..#..",
    ".#...",
    "#####"
]
Z_LARGE = [
    "#######",
    ".....#.",
    "....#..",
    "...#...",
    "..#....",
    ".#.....",
    "#######"
]

def draw_pattern(img, pattern, top_left, color=(160, 210, 255, 230), outline_color=(70, 90, 160, 230)):
    ox, oy = top_left
    ph = len(pattern)
    pw = len(pattern[0])
    for y, row in enumerate(pattern):
        for x, ch in enumerate(row):
            if ch == '#':
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    px, py = ox + x + dx, oy + y + dy
                    if 0 <= px < img.width and 0 <= py < img.height:
                        img.putpixel((px, py), outline_color)
    for y, row in enumerate(pattern):
        for x, ch in enumerate(row):
            if ch == '#':
                px, py = ox + x, oy + y
                if 0 <= px < img.width and 0 <= py < img.height:
                    img.putpixel((px, py), color)

sleep_cells = []
nods = [0, -1, 0, 2, 3, 1, 0, -1] # Nodding forward and recovering
pos_x = (CELL_W - p3_scaled.width) // 2
pos_y_base = ground_y_in_cell - p3_scaled.height

for i in range(COLS):
    canvas = Image.new('RGBA', (CELL_W, CELL_H), (0, 0, 0, 0))
    y_nod = nods[i]
    canvas.paste(p3_scaled, (pos_x, pos_y_base + y_nod), p3_scaled)
    
    # Floating Zzz near right of head
    t = i / COLS
    z1_x = pos_x + p3_scaled.width - 15 + int(math.sin(t * math.pi * 2) * 2)
    z1_y = pos_y_base + 35 - int(t * 18)
    
    t2 = (i + 3) % COLS / COLS
    z2_x = pos_x + p3_scaled.width - 5 + int(math.sin(t2 * math.pi * 2) * 3)
    z2_y = pos_y_base + 18 - int(t2 * 22)
    
    t3 = (i + 6) % COLS / COLS
    z3_x = pos_x + p3_scaled.width + 5 + int(math.sin(t3 * math.pi * 2) * 4)
    z3_y = pos_y_base + 2 - int(t3 * 26)
    
    draw_pattern(canvas, Z_SMALL, (z1_x, z1_y))
    draw_pattern(canvas, Z_SMALL, (z2_x, z2_y))
    draw_pattern(canvas, Z_LARGE, (z3_x, z3_y))
    
    sleep_cells.append(canvas)

# 3G. Prepare WAITING Cycle (Row 6: Waiting / Thinking - Head Tilt Jitome)
r6_raw = Image.open(os.path.join(ASSETS_DIR, "waiting_jitome.png"))
r6_head = r6_raw.crop((0, 0, r6_raw.width, 670))
r6_body = r6_raw.crop((0, 630, r6_raw.width, r6_raw.height))

r6_scale = 83.0 / 655.0
r6_w = int(round(r6_raw.width * r6_scale))
r6_h = int(round(r6_raw.height * r6_scale))
r6_pivot = (335, 670)

# Gentle inquisitive nodding / tilting: starts upright (+1.5 deg), tilts to -3.0 deg, returns
r6_angles = [1.5, 0.5, -0.8, -2.2, -3.0, -2.2, -0.8, 0.5]
r6_bobs = [0, -3, -6, -3, 0, -3, -6, -3]

waiting_cells = []
r6_pos_x = (CELL_W - r6_w) // 2
r6_pos_y = ground_y_in_cell - r6_h

for a, b in zip(r6_angles, r6_bobs):
    rot_h = r6_head.rotate(a, resample=Image.Resampling.BICUBIC, center=r6_pivot)
    c_large = Image.new('RGBA', r6_raw.size, (0, 0, 0, 0))
    c_large.paste(r6_body, (0, 630), r6_body)
    c_large.paste(rot_h, (0, b), rot_h)
    scaled_f = c_large.resize((r6_w, r6_h), Image.Resampling.LANCZOS)
    
    cell_canvas = Image.new('RGBA', (CELL_W, CELL_H), (0, 0, 0, 0))
    cell_canvas.paste(scaled_f, (r6_pos_x, r6_pos_y), scaled_f)
    waiting_cells.append(cell_canvas)

# 3H. Prepare REVIEW / HACKER Cycle (Row 8: Review - Furious Laptop Typing with Dynamic Hand Movement)
r8_raw = Image.open(os.path.join(ASSETS_DIR, "hacker_typing.png"))
r8_scale = 83.0 / 342.0
r8_w = int(round(r8_raw.width * r8_scale))
r8_h = int(round(r8_raw.height * r8_scale))

# Extract hand layers for dynamic typing animation
r_box = (195, 405, 285, 495)
r_hand = r8_raw.crop(r_box)

l_box = (145, 435, 215, 505)
l_hand = r8_raw.crop(l_box)

# Dynamic hand key-tapping offsets (large coords)
r_dys = [6, -5, 7, -4, 6, -5, 7, -4]
l_dys = [-5, 6, -4, 7, -5, 6, -4, 7]
r_spark_pos = (245, 492)
l_spark_pos = (190, 502)

review_cells = []
r8_pos_x = (CELL_W - r8_w) // 2
r8_pos_y = ground_y_in_cell - r8_h

for i in range(COLS):
    c_large = r8_raw.copy()
    
    # Left hand shifted
    ldy = l_dys[i]
    c_large.paste(l_hand, (l_box[0], l_box[1] + ldy), l_hand)
    
    # Right hand shifted
    rdy = r_dys[i]
    c_large.paste(r_hand, (r_box[0], r_box[1] + rdy), r_hand)
    
    # Draw key tap spark on the hand tapping down
    draw_keys = ImageDraw.Draw(c_large)
    if rdy > 0:
        sx, sy = r_spark_pos
        draw_keys.rectangle([sx-3, sy-2, sx+3, sy+2], fill=(255, 255, 255, 255))
        draw_keys.rectangle([sx-2, sy-3, sx+2, sy+3], fill=(180, 240, 255, 240))
    if ldy > 0:
        sx, sy = l_spark_pos
        draw_keys.rectangle([sx-3, sy-2, sx+3, sy+2], fill=(255, 255, 255, 255))
        draw_keys.rectangle([sx-2, sy-3, sx+2, sy+3], fill=(180, 240, 255, 240))
        
    scaled_hacker = c_large.resize((r8_w, r8_h), Image.Resampling.LANCZOS)
    
    canvas = Image.new('RGBA', (CELL_W, CELL_H), (0, 0, 0, 0))
    yb = 0 if i % 2 == 0 else -1
    canvas.paste(scaled_hacker, (r8_pos_x, r8_pos_y + yb), scaled_hacker)
    
    # Rising digital sparkle particles
    t1 = i / COLS
    p1_x = r8_pos_x + 72 + int(math.sin(t1 * math.pi * 2) * 3)
    p1_y = r8_pos_y + 80 - int(t1 * 30)
    
    t2 = (i + 3) % COLS / COLS
    p2_x = r8_pos_x + 80 + int(math.cos(t2 * math.pi * 2) * 4)
    p2_y = r8_pos_y + 75 - int(t2 * 28)
    
    t3 = (i + 6) % COLS / COLS
    p3_x = r8_pos_x + 66 + int(math.sin(t3 * math.pi * 2 + 1) * 3)
    p3_y = r8_pos_y + 70 - int(t3 * 32)
    
    draw_c = ImageDraw.Draw(canvas)
    draw_c.rectangle([p1_x, p1_y, p1_x+2, p1_y+2], fill=(140, 220, 255, 230))
    draw_c.rectangle([p2_x, p2_y, p2_x+1, p2_y+1], fill=(180, 240, 255, 230))
    draw_c.rectangle([p3_x, p3_y, p3_x+2, p3_y+2], fill=(140, 220, 255, 230))
    
    review_cells.append(canvas)

# Assemble Master Atlas
atlas = Image.new("RGBA", (TOTAL_W, TOTAL_H), (0, 0, 0, 0))

def put_cell(col, row, cell_img):
    x = col * CELL_W
    y = row * CELL_H
    atlas.paste(cell_img, (x, y), cell_img)

# Row 0: Idle (Upper body sway, lower body fixed!)
for c in range(COLS):
    put_cell(c, 0, idle_cells[c])

# Row 1: Running Right (Legs moving, 4-step cycle repeated twice)
for c in range(COLS):
    put_cell(c, 1, run_cells_right[c % 4])

# Row 2: Running Left (Mirrored run cycle)
for c in range(COLS):
    put_cell(c, 2, run_cells_left[c % 4])

# Row 3: Greeting / Waving Hand (Animated 8-frame wave loop!)
for c in range(COLS):
    put_cell(c, 3, wave_cells[c])

# Row 4: Jumping / Success (Celebration jump!)
jump_offsets = [0, -6, -14, -16, -10, -2, 0, 0]
for c in range(COLS):
    if c in [0, 6, 7]:
        put_cell(c, 4, idle_cells[c])
    else:
        put_cell(c, 4, make_jump_cell(jump_offsets[c]))

# Row 5: Failed / Error (Official "Een!" Crying Stamp Animation)
for c in range(COLS):
    put_cell(c, 5, failed_cells[c])

# Row 6: Waiting (Inquisitive Head Tilt with Official Jitome & Cat Mouth)
for c in range(COLS):
    put_cell(c, 6, waiting_cells[c])

# Row 7: Running Alt (Fast run)
for c in range(COLS):
    put_cell(c, 7, run_cells_right[c % 4])

# Row 8: Review (Furious Hacker Laptop Typing with Rising Sparkles)
for c in range(COLS):
    put_cell(c, 8, review_cells[c])

# Row 9: Look up (Swaying gently)
for c in range(COLS):
    put_cell(c, 9, make_upper_sway_cell(sway_shifts[c], y_bob=-2))

# Row 10: Special / Rest (Sitting Nodding Nap with floating Zzz)
for c in range(COLS):
    put_cell(c, 10, sleep_cells[c])

# ==========================================
# 4. SAVE BUNDLE & PREVIEWS
# ==========================================
build_dir = os.path.join(BASE_DIR, "roa_pet")
os.makedirs(build_dir, exist_ok=True)
spritesheet_path = os.path.join(build_dir, "spritesheet.webp")
atlas.save(spritesheet_path, "WEBP", lossless=True)
atlas.save(os.path.join(build_dir, "spritesheet_preview.png"))

# Create .codex-pet bundle
bundle_path = os.path.join(BASE_DIR, "roa.codex-pet")
with zipfile.ZipFile(bundle_path, "w", zipfile.ZIP_DEFLATED) as zf:
    zf.write(spritesheet_path, arcname="spritesheet.webp")
    pet_info = {
        "id": "roa",
        "displayName": "Roa",
        "description": "Roa the cat desktop pet.",
        "spritesheetPath": "spritesheet.webp",
        "spriteVersionNumber": 2
    }
    with open(os.path.join(build_dir, "pet.json"), "w", encoding="utf-8") as f:
        json.dump(pet_info, f, ensure_ascii=False, indent=2)
    zf.write(os.path.join(build_dir, "pet.json"), arcname="pet.json")

# Export animated preview GIFs
idle_cells[0].save(
    "idle_sway_perfect.gif",
    save_all=True,
    append_images=idle_cells[1:],
    duration=130,
    loop=0,
    disposal=2
)

run_cycle_8 = [run_cells_right[c % 4] for c in range(8)]
run_cycle_8[0].save(
    "run_cycle_perfect.gif",
    save_all=True,
    append_images=run_cycle_8[1:],
    duration=120,
    loop=0,
    disposal=2
)

wave_cells[0].save(
    "wave_cycle_perfect.gif",
    save_all=True,
    append_images=wave_cells[1:],
    duration=120,
    loop=0,
    disposal=2
)

failed_cells[0].save(
    "failed_cycle_perfect.gif",
    save_all=True,
    append_images=failed_cells[1:],
    duration=130,
    loop=0,
    disposal=2
)

# Row 10 Rest / Sleep Cycle GIF
p_sleep_frames = []
for f in sleep_cells:
    alpha = f.split()[3]
    rgb = f.convert('RGB')
    p_img = rgb.quantize(colors=255, method=Image.Resampling.LANCZOS)
    p_mask = Image.eval(alpha, lambda a: 255 if a < 128 else 0)
    p_img.paste(255, p_mask)
    p_img.info['transparency'] = 255
    p_sleep_frames.append(p_img)

p_sleep_frames[0].save(
    "rest_cycle_perfect.gif",
    save_all=True,
    append_images=p_sleep_frames[1:],
    duration=140,
    loop=0,
    disposal=2,
    transparency=255
)

# Row 6 Waiting Cycle GIF
p_waiting_frames = []
for f in waiting_cells:
    alpha = f.split()[3]
    rgb = f.convert('RGB')
    p_img = rgb.quantize(colors=255, method=Image.Resampling.LANCZOS)
    p_mask = Image.eval(alpha, lambda a: 255 if a < 128 else 0)
    p_img.paste(255, p_mask)
    p_img.info['transparency'] = 255
    p_waiting_frames.append(p_img)

p_waiting_frames[0].save(
    "waiting_cycle_perfect.gif",
    save_all=True,
    append_images=p_waiting_frames[1:],
    duration=140,
    loop=0,
    disposal=2,
    transparency=255
)

# Row 8 Review Cycle GIF
p_review_frames = []
for f in review_cells:
    alpha = f.split()[3]
    rgb = f.convert('RGB')
    p_img = rgb.quantize(colors=255, method=Image.Resampling.LANCZOS)
    p_mask = Image.eval(alpha, lambda a: 255 if a < 128 else 0)
    p_img.paste(255, p_mask)
    p_img.info['transparency'] = 255
    p_review_frames.append(p_img)

p_review_frames[0].save(
    "review_cycle_perfect.gif",
    save_all=True,
    append_images=p_review_frames[1:],
    duration=90,
    loop=0,
    disposal=2,
    transparency=255
)

# Also generate a test preview on neon pink to prove NO white parts are lost!
pink_test = Image.new("RGBA", (CELL_W, CELL_H), (255, 0, 128, 255))
pink_test.paste(idle_cells[0], (0, 0), idle_cells[0])
pink_test.save("verified_no_transparency_bug.png")

# Also generate pink preview for all 4 run cycle frames
pink_run_strip = Image.new("RGBA", (CELL_W * 4, CELL_H), (255, 0, 128, 255))
for i in range(4):
    pink_run_strip.paste(run_cells_right[i], (i * CELL_W, 0), run_cells_right[i])
pink_run_strip.save("verified_run_on_pink.png")

# Also generate pink preview for sway frames (frame 0 and max sway frame 2)
pink_idle_strip = Image.new("RGBA", (CELL_W * 4, CELL_H), (255, 0, 128, 255))
for i in range(4):
    pink_idle_strip.paste(idle_cells[i], (i * CELL_W, 0), idle_cells[i])
pink_idle_strip.save("verified_idle_on_pink.png")

print(f"=== BUILD V6 COMPLETE: {bundle_path} ({os.path.getsize(bundle_path)} bytes) ===")