#!/usr/bin/env python3
import os
import zipfile
from collections import deque
from PIL import Image, ImageOps

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
ROA_PET_DIR = os.path.join(BASE_DIR, "roa_pet")
SHIJIMA_BUILD_DIR = os.path.join(BASE_DIR, "shijima_build", "Roa")
SHIJIMA_IMG_DIR = os.path.join(SHIJIMA_BUILD_DIR, "img")

os.makedirs(SHIJIMA_IMG_DIR, exist_ok=True)

print("=== STARTING SHIJIMA MASCOT BUILD ===")

# 1. Load existing 192x208 master spritesheet (8 cols x 11 rows)
CELL_W, CELL_H = 192, 208
GROUND_Y_IN_CELL = 196  # CELL_H - 12
atlas_path = os.path.join(ROA_PET_DIR, "spritesheet_preview.png")
atlas = Image.open(atlas_path).convert("RGBA")

def get_atlas_cell(row, col):
    x = col * CELL_W
    y = row * CELL_H
    return atlas.crop((x, y, x + CELL_W, y + CELL_H))

# Convert a 192x208 ground-aligned cell to a 128x128 Shijima frame (feet at Y=128, centered at X=64)
# Scale factor: 175px tall char -> ~114px tall in 128x128 (scale = 0.65)
SCALE_128 = 0.65

def cell_to_shijima_ground(cell_img, mirror=False):
    if mirror:
        cell_img = ImageOps.mirror(cell_img)
    new_w = int(round(CELL_W * SCALE_128))
    new_h = int(round(CELL_H * SCALE_128))
    scaled = cell_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    ground_y_scaled = int(round(GROUND_Y_IN_CELL * SCALE_128))

    canvas = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    px = (128 - new_w) // 2
    py = 128 - ground_y_scaled
    canvas.paste(scaled, (px, py), scaled)
    return canvas

# 2. Helper to clean white background and extract 3 frames from 1376x768 sheets
def extract_3_frames_from_sheet(filename, extra_seeds=None):
    path = os.path.join(ASSETS_DIR, filename)
    img = Image.open(path).convert("RGBA")
    w, h = img.size
    pix = img.load()

    def is_near_white(r, g, b):
        return min(r, g, b) > 220 and (max(r, g, b) - min(r, g, b)) < 18

    visited = [[False] * h for _ in range(w)]
    q = deque()
    for x in range(w):
        for y in [0, h - 1]:
            if is_near_white(*pix[x, y][:3]):
                visited[x][y] = True
                q.append((x, y))
    for y in range(h):
        for x in [0, w - 1]:
            if not visited[x][y] and is_near_white(*pix[x, y][:3]):
                visited[x][y] = True
                q.append((x, y))

    if extra_seeds:
        for sx, sy in extra_seeds:
            for dx in range(-4, 5):
                for dy in range(-4, 5):
                    nx, ny = sx + dx, sy + dy
                    if 0 <= nx < w and 0 <= ny < h and not visited[nx][ny] and is_near_white(*pix[nx, ny][:3]):
                        visited[nx][ny] = True
                        q.append((nx, ny))

    while q:
        cx, cy = q.popleft()
        pix[cx, cy] = (0, 0, 0, 0)
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < w and 0 <= ny < h and not visited[nx][ny]:
                if is_near_white(*pix[nx, ny][:3]):
                    visited[nx][ny] = True
                    q.append((nx, ny))

    # Extract the 3 main character connected components sorted left-to-right
    visited_comp = [[False] * h for _ in range(w)]
    components = []
    for x in range(w):
        for y in range(h):
            if pix[x, y][3] > 0 and not visited_comp[x][y]:
                comp = []
                qc = deque([(x, y)])
                visited_comp[x][y] = True
                while qc:
                    cx, cy = qc.popleft()
                    comp.append((cx, cy))
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]:
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < w and 0 <= ny < h and not visited_comp[nx][ny]:
                            if pix[nx, ny][3] > 0:
                                visited_comp[nx][ny] = True
                                qc.append((nx, ny))
                if len(comp) > 2000:
                    components.append(comp)

    components.sort(key=lambda c: min(p[0] for p in c))
    frames = []
    for comp in components[:3]:
        min_x = min(p[0] for p in comp)
        max_x = max(p[0] for p in comp)
        min_y = min(p[1] for p in comp)
        max_y = max(p[1] for p in comp)
        sub = Image.new("RGBA", (max_x - min_x + 1, max_y - min_y + 1), (0, 0, 0, 0))
        spix = sub.load()
        for px, py in comp:
            spix[px - min_x, py - min_y] = pix[px, py]
        frames.append(sub)
    return frames

# Extract the 4 new custom 3-frame sheets
wall_raw = extract_3_frames_from_sheet("wall_climb_hybrid.jpg")
ceiling_raw = extract_3_frames_from_sheet("ceiling_crawl.jpg", extra_seeds=[(1193, 593)])
pinched_raw = extract_3_frames_from_sheet("pinched_dragged.jpg")
fall_land_raw = extract_3_frames_from_sheet("fall_and_land.jpg")

TARGET_CHAR_H = 114  # Consistent character height inside 128x128 canvas

# 2A. Format Wall Climb frames (shime12, shime13, shime14)
# In wall_climb_hybrid.jpg, Roa climbs a wall on the RIGHT.
# Shijima's base sprites face LEFT (climbing the LEFT wall), and Shijima flips horizontally when on the RIGHT wall.
# We align the left edge (hands/toes gripping the wall) to X = 14 so ImageAnchor="14,112" touches the wall cleanly!
wall_frames_128 = []
for f in wall_raw:
    f_left = ImageOps.mirror(f)
    scale = TARGET_CHAR_H / f_left.height
    sw = int(round(f_left.width * scale))
    sh = TARGET_CHAR_H
    s_img = f_left.resize((sw, sh), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    # Place left-most edge (gripping hand/foot) at X = 12
    px = 12
    py = 128 - sh - 4
    canvas.paste(s_img, (px, py), s_img)
    wall_frames_128.append(canvas)

# 2B. Format Ceiling Crawl frames (shime23, shime24, shime25)
# Mirror to face/move left by default; align top of gripping hands to Y = 4 (ImageAnchor="64,6")
ceiling_frames_128 = []
for f in ceiling_raw:
    f_left = ImageOps.mirror(f)
    scale = TARGET_CHAR_H / f_left.height
    sw = int(round(f_left.width * scale))
    sh = TARGET_CHAR_H
    s_img = f_left.resize((sw, sh), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    px = (128 - sw) // 2
    py = 2  # hands right at top edge
    canvas.paste(s_img, (px, py), s_img)
    ceiling_frames_128.append(canvas)

# 2C. Format Pinched / Dragged frames (shime1, shime5..10)
# Align top of head/scruff to (64, 14) so ImageAnchor="64,16" hangs right below the finger!
pinched_frames_128 = []
for f in pinched_raw:
    scale = TARGET_CHAR_H / f.height
    sw = int(round(f.width * scale))
    sh = TARGET_CHAR_H
    s_img = f.resize((sw, sh), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    px = (128 - sw) // 2
    py = 6
    canvas.paste(s_img, (px, py), s_img)
    pinched_frames_128.append(canvas)

# Create tilted versions for extreme drag swing
pinched_left_tilt = pinched_frames_128[0].rotate(-8, resample=Image.Resampling.BICUBIC, center=(64, 16))
pinched_right_mild = ImageOps.mirror(pinched_frames_128[0])
pinched_right_tilt = pinched_right_mild.rotate(8, resample=Image.Resampling.BICUBIC, center=(64, 16))
pinched_struggle_1 = pinched_frames_128[2]
pinched_struggle_2 = ImageOps.mirror(pinched_frames_128[2])

# 2D. Format Falling & Landing frames (shime4, shime18, shime19, shime11)
fall_land_128 = []
for idx, f in enumerate(fall_land_raw):
    # Sitting frames (idx 1 and 2) are naturally slightly shorter in height than standing
    target_h = 108 if idx == 0 else 102
    scale = target_h / f.height
    sw = int(round(f.width * scale))
    sh = target_h
    s_img = f.resize((sw, sh), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    px = (128 - sw) // 2
    py = (128 - sh) // 2 if idx == 0 else (128 - sh)
    canvas.paste(s_img, (px, py), s_img)
    fall_land_128.append(canvas)

def save_shime(num, img):
    out_path = os.path.join(SHIJIMA_IMG_DIR, f"shime{num}.png")
    img.save(out_path, "PNG")

# ==========================================
# 3. POPULATE STANDARD SHIME1..SHIME46 + CUSTOM FRAMES
# ==========================================
# Extract all rows from existing atlas converted to 128x128
idle_128 = [cell_to_shijima_ground(get_atlas_cell(0, c)) for c in range(8)]
run_left_128 = [cell_to_shijima_ground(get_atlas_cell(2, c)) for c in range(4)]
wave_128 = [cell_to_shijima_ground(get_atlas_cell(3, c)) for c in range(8)]
jump_128 = [cell_to_shijima_ground(get_atlas_cell(4, c)) for c in range(8)]
cry_128 = [cell_to_shijima_ground(get_atlas_cell(5, c)) for c in range(8)]
wait_128 = [cell_to_shijima_ground(get_atlas_cell(6, c)) for c in range(8)]
review_128 = [cell_to_shijima_ground(get_atlas_cell(8, c)) for c in range(8)]
lookup_128 = [cell_to_shijima_ground(get_atlas_cell(9, c)) for c in range(8)]
sleep_128 = [cell_to_shijima_ground(get_atlas_cell(10, c)) for c in range(8)]

# Standard Shimeji 1..46 mapping:
# 1..3: Stand / Walk (we also add 4-step walk using shime1,2,3,47)
save_shime(1, idle_128[0])
save_shime(2, run_left_128[0])
save_shime(3, run_left_128[2])
# 4: Falling
save_shime(4, fall_land_128[0])
# 5..10: Pinched / Dragged / Resisting
save_shime(5, pinched_frames_128[0])   # swing left
save_shime(6, pinched_right_mild)      # swing right
save_shime(7, pinched_left_tilt)       # swing far left
save_shime(8, pinched_right_tilt)      # swing far right
save_shime(9, pinched_struggle_1)      # struggle > < left
save_shime(10, pinched_struggle_2)     # struggle > < right
# 11: Sit
save_shime(11, fall_land_128[2])
# 12..14: Wall Grab & Climb
save_shime(12, wall_frames_128[0])     # reach up 1
save_shime(13, wall_frames_128[1])     # neutral grab
save_shime(14, wall_frames_128[2])     # reach up 2 (> <)
# 15..17: Spin head / inquisitive jitome frames
save_shime(15, wait_128[2])
save_shime(16, wait_128[4])
save_shime(17, wait_128[6])
# 18..19: Landing bounce (plop on butt -> sit up)
save_shime(18, fall_land_128[1])
save_shime(19, fall_land_128[2])
# 20..21: Sprawl / Nap
save_shime(20, sleep_128[0])
save_shime(21, sleep_128[4])
# 22: Jumping
save_shime(22, jump_128[3])
# 23..25: Ceiling Grab & Crawl
save_shime(23, ceiling_frames_128[1])  # neutral hang
save_shime(24, ceiling_frames_128[0])  # reach 1
save_shime(25, ceiling_frames_128[2])  # reach 2 (> <)
# 26..29: Sit and look up / around
save_shime(26, lookup_128[2])
save_shime(27, wait_128[1])
save_shime(28, wait_128[3])
save_shime(29, wait_128[5])
# 30..33: Sit and dangle legs (use sitting & nap frames)
save_shime(30, fall_land_128[2])
save_shime(31, fall_land_128[2])
save_shime(32, sleep_128[1])
save_shime(33, sleep_128[5])
# 34..37: IE carrying / throwing
save_shime(34, run_left_128[0])
save_shime(35, run_left_128[1])
save_shime(36, run_left_128[2])
save_shime(37, wave_128[4])
# 38..41: Pull up / breed shimeji (celebration jump & wave)
save_shime(38, wait_128[0])
save_shime(39, wait_128[4])
save_shime(40, jump_128[2])
save_shime(41, jump_128[4])
# 42..46: Divide / split into two (hacker typing -> jump!)
save_shime(42, review_128[0])
save_shime(43, review_128[2])
save_shime(44, review_128[4])
save_shime(45, jump_128[2])
save_shime(46, jump_128[3])

# ==========================================
# 4. EXTRA FRAMES FOR FULL 11-ACTION SMOOTH ANIMATIONS (shime47..shime96)
# ==========================================
# 47..50: Full 4-step smooth Run cycle (frames 0, 1, 2, 3)
for i in range(4):
    save_shime(47 + i, run_left_128[i])
# 51..58: Full 8-step Idle Sway (frames 0..7)
for i in range(8):
    save_shime(51 + i, idle_128[i])
# 59..66: Full 8-step Wave Greeting (frames 0..7)
for i in range(8):
    save_shime(59 + i, wave_128[i])
# 67..74: Full 8-step Celebration Jump (frames 0..7)
for i in range(8):
    save_shime(67 + i, jump_128[i])
# 75..82: Full 8-step Crying "Een!" Stamp (frames 0..7)
for i in range(8):
    save_shime(75 + i, cry_128[i])
# 83..90: Full 8-step Waiting Jitome Head-Tilt (frames 0..7)
for i in range(8):
    save_shime(83 + i, wait_128[i])
# 91..98: Full 8-step Hacker Laptop Review (frames 0..7)
for i in range(8):
    save_shime(91 + i, review_128[i])
# 99..106: Full 8-step Sleeping Nap with Zzz (frames 0..7)
for i in range(8):
    save_shime(99 + i, sleep_128[i])
# 107: Center dangle when pinched
save_shime(107, pinched_frames_128[1])

print("Saved shime1.png through shime107.png (128x128 PNGs)")

# ==========================================
# 5. GENERATE SHIJIMA actions.xml & behaviors.xml
# ==========================================
def pose_block(start_num, count, anchor="64,128", vel="0,0", dur="4"):
    lines = []
    for i in range(count):
        lines.append(f'\t\t\t\t<Pose Image="/shime{start_num + i}.png" ImageAnchor="{anchor}" Velocity="{vel}" Duration="{dur}" />')
    return "\n".join(lines)

actions_xml = f"""<?xml version="1.0" encoding="UTF-8" ?>
<Mascot xmlns="http://www.group-finity.com/Mascot" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
	xsi:schemaLocation="http://www.group-finity.com/Mascot Mascot.xsd">

	<ActionList>
		<Action Name="Look" Type="Embedded" Class="com.group_finity.mascot.action.Look" />
		<Action Name="Offset" Type="Embedded" Class="com.group_finity.mascot.action.Offset" />

		<!-- Standing (8-frame smooth upper-body sway) -->
		<Action Name="Stand" Type="Stay" BorderType="Floor">
			<Animation>
{pose_block(51, 8, anchor="64,128", vel="0,0", dur="4")}
			</Animation>
		</Action>

		<Action Name="Walk" Type="Move" BorderType="Floor">
			<Animation>
				<Pose Image="/shime47.png" ImageAnchor="64,128" Velocity="-2,0" Duration="4" />
				<Pose Image="/shime48.png" ImageAnchor="64,128" Velocity="-2,0" Duration="4" />
				<Pose Image="/shime49.png" ImageAnchor="64,128" Velocity="-2,0" Duration="4" />
				<Pose Image="/shime50.png" ImageAnchor="64,128" Velocity="-2,0" Duration="4" />
			</Animation>
		</Action>

		<Action Name="Run" Type="Move" BorderType="Floor">
			<Animation>
				<Pose Image="/shime47.png" ImageAnchor="64,128" Velocity="-4,0" Duration="3" />
				<Pose Image="/shime48.png" ImageAnchor="64,128" Velocity="-4,0" Duration="3" />
				<Pose Image="/shime49.png" ImageAnchor="64,128" Velocity="-4,0" Duration="3" />
				<Pose Image="/shime50.png" ImageAnchor="64,128" Velocity="-4,0" Duration="3" />
			</Animation>
		</Action>

		<Action Name="Dash" Type="Move" BorderType="Floor">
			<Animation>
				<Pose Image="/shime47.png" ImageAnchor="64,128" Velocity="-8,0" Duration="2" />
				<Pose Image="/shime48.png" ImageAnchor="64,128" Velocity="-8,0" Duration="2" />
				<Pose Image="/shime49.png" ImageAnchor="64,128" Velocity="-8,0" Duration="2" />
				<Pose Image="/shime50.png" ImageAnchor="64,128" Velocity="-8,0" Duration="2" />
			</Animation>
		</Action>

		<!-- Custom Roa Actions -->
		<Action Name="WaveAction" Type="Animate" BorderType="Floor">
			<Animation>
{pose_block(59, 8, anchor="64,128", vel="0,0", dur="4")}
{pose_block(59, 8, anchor="64,128", vel="0,0", dur="4")}
			</Animation>
		</Action>

		<Action Name="CelebrateJumpAction" Type="Animate" BorderType="Floor">
			<Animation>
{pose_block(67, 8, anchor="64,128", vel="0,0", dur="3")}
{pose_block(67, 8, anchor="64,128", vel="0,0", dur="3")}
			</Animation>
		</Action>

		<Action Name="CryingStampAction" Type="Animate" BorderType="Floor">
			<Animation>
{pose_block(75, 8, anchor="64,128", vel="0,0", dur="4")}
{pose_block(75, 8, anchor="64,128", vel="0,0", dur="4")}
			</Animation>
		</Action>

		<Action Name="InquisitiveWaitAction" Type="Stay" BorderType="Floor">
			<Animation>
{pose_block(83, 8, anchor="64,128", vel="0,0", dur="4")}
			</Animation>
		</Action>

		<Action Name="HackerReviewAction" Type="Stay" BorderType="Floor">
			<Animation>
{pose_block(91, 8, anchor="64,128", vel="0,0", dur="3")}
			</Animation>
		</Action>

		<!-- Sitting & Nap -->
		<Action Name="Sit" Type="Stay" BorderType="Floor">
			<Animation>
				<Pose Image="/shime11.png" ImageAnchor="64,128" Velocity="0,0" Duration="250" />
			</Animation>
		</Action>

		<Action Name="SitAndLookUp" Type="Stay" BorderType="Floor">
			<Animation>
				<Pose Image="/shime26.png" ImageAnchor="64,128" Velocity="0,0" Duration="250" />
			</Animation>
		</Action>

		<Action Name="SitAndLookAtMouse" Type="Stay" BorderType="Floor">
			<Animation Condition="#{{mascot.environment.cursor.y &lt; mascot.environment.screen.height/2}}">
				<Pose Image="/shime26.png" ImageAnchor="64,128" Velocity="0,0" Duration="250" />
			</Animation>
			<Animation>
				<Pose Image="/shime11.png" ImageAnchor="64,128" Velocity="0,0" Duration="250" />
			</Animation>
		</Action>

		<Action Name="SitAndSpinHeadAction" Type="Animate" BorderType="Floor">
			<Animation>
{pose_block(83, 8, anchor="64,128", vel="0,0", dur="4")}
			</Animation>
		</Action>

		<Action Name="SitWithLegsUp" Type="Stay" BorderType="Floor">
			<Animation>
				<Pose Image="/shime30.png" ImageAnchor="64,128" Velocity="0,0" Duration="250" />
			</Animation>
		</Action>

		<Action Name="SitWithLegsDown" Type="Stay" BorderType="Floor">
			<Animation>
				<Pose Image="/shime31.png" ImageAnchor="64,128" Velocity="0,0" Duration="250" />
			</Animation>
		</Action>

		<Action Name="SitAndDangleLegs" Type="Stay" BorderType="Floor">
			<Animation>
{pose_block(99, 8, anchor="64,128", vel="0,0", dur="5")}
			</Animation>
		</Action>

		<!-- Laying / Sleeping Nap with Zzz -->
		<Action Name="Sprawl" Type="Stay" BorderType="Floor">
			<Animation>
{pose_block(99, 8, anchor="64,128", vel="0,0", dur="5")}
			</Animation>
		</Action>

		<Action Name="Creep" Type="Move" BorderType="Floor">
			<Animation>
				<Pose Image="/shime47.png" ImageAnchor="64,128" Velocity="-1,0" Duration="6" />
				<Pose Image="/shime48.png" ImageAnchor="64,128" Velocity="-1,0" Duration="6" />
				<Pose Image="/shime49.png" ImageAnchor="64,128" Velocity="-1,0" Duration="6" />
				<Pose Image="/shime50.png" ImageAnchor="64,128" Velocity="-1,0" Duration="6" />
			</Animation>
		</Action>

		<!-- Ceiling -->
		<Action Name="GrabCeiling" Type="Stay" BorderType="Ceiling">
			<Animation>
				<Pose Image="/shime23.png" ImageAnchor="64,8" Velocity="0,0" Duration="250" />
			</Animation>
		</Action>

		<Action Name="ClimbCeiling" Type="Move" BorderType="Ceiling">
			<Animation>
				<Pose Image="/shime25.png" ImageAnchor="64,8" Velocity="0,0" Duration="12" />
				<Pose Image="/shime25.png" ImageAnchor="64,8" Velocity="-1,0" Duration="4" />
				<Pose Image="/shime23.png" ImageAnchor="64,8" Velocity="-1,0" Duration="4" />
				<Pose Image="/shime24.png" ImageAnchor="64,8" Velocity="-1,0" Duration="4" />
				<Pose Image="/shime24.png" ImageAnchor="64,8" Velocity="0,0" Duration="12" />
				<Pose Image="/shime24.png" ImageAnchor="64,8" Velocity="-2,0" Duration="4" />
				<Pose Image="/shime23.png" ImageAnchor="64,8" Velocity="-2,0" Duration="4" />
				<Pose Image="/shime25.png" ImageAnchor="64,8" Velocity="-2,0" Duration="4" />
			</Animation>
		</Action>

		<!-- Wall -->
		<Action Name="GrabWall" Type="Stay" BorderType="Wall">
			<Animation>
				<Pose Image="/shime13.png" ImageAnchor="16,112" Velocity="0,0" Duration="250" />
			</Animation>
		</Action>

		<Action Name="ClimbWall" Type="Move" BorderType="Wall">
			<Animation Condition="#{{TargetY &lt; mascot.anchor.y}}">
				<Pose Image="/shime14.png" ImageAnchor="16,112" Velocity="0,0" Duration="12" />
				<Pose Image="/shime14.png" ImageAnchor="16,112" Velocity="0,-1" Duration="4" />
				<Pose Image="/shime12.png" ImageAnchor="16,112" Velocity="0,-1" Duration="4" />
				<Pose Image="/shime13.png" ImageAnchor="16,112" Velocity="0,-1" Duration="4" />
				<Pose Image="/shime13.png" ImageAnchor="16,112" Velocity="0,0" Duration="12" />
				<Pose Image="/shime13.png" ImageAnchor="16,112" Velocity="0,-2" Duration="4" />
				<Pose Image="/shime12.png" ImageAnchor="16,112" Velocity="0,-2" Duration="4" />
				<Pose Image="/shime14.png" ImageAnchor="16,112" Velocity="0,-2" Duration="4" />
			</Animation>

			<Animation Condition="#{{TargetY &gt;= mascot.anchor.y}}">
				<Pose Image="/shime14.png" ImageAnchor="16,112" Velocity="0,0" Duration="12" />
				<Pose Image="/shime14.png" ImageAnchor="16,112" Velocity="0,2" Duration="4" />
				<Pose Image="/shime12.png" ImageAnchor="16,112" Velocity="0,2" Duration="4" />
				<Pose Image="/shime13.png" ImageAnchor="16,112" Velocity="0,2" Duration="4" />
				<Pose Image="/shime13.png" ImageAnchor="16,112" Velocity="0,0" Duration="12" />
				<Pose Image="/shime13.png" ImageAnchor="16,112" Velocity="0,1" Duration="4" />
				<Pose Image="/shime12.png" ImageAnchor="16,112" Velocity="0,1" Duration="4" />
				<Pose Image="/shime14.png" ImageAnchor="16,112" Velocity="0,1" Duration="4" />
			</Animation>
		</Action>

		<!-- IE -->
		<Action Name="FallWithIe" Type="Embedded" Class="com.group_finity.mascot.action.FallWithIE"
			 IeOffsetX="0" IeOffsetY="-64">
			<Animation>
				<Pose Image="/shime36.png" ImageAnchor="64,128" Velocity="0,0" Duration="250" />
			</Animation>
		</Action>
		<Action Name="WalkWithIe" BorderType="Floor" Type="Embedded" Class="com.group_finity.mascot.action.WalkWithIE"
			 IeOffsetX="0" IeOffsetY="-64">
			<Animation>
				<Pose Image="/shime34.png" ImageAnchor="64,128" Velocity="-2,0" Duration="6" />
				<Pose Image="/shime35.png" ImageAnchor="64,128" Velocity="-2,0" Duration="6" />
				<Pose Image="/shime34.png" ImageAnchor="64,128" Velocity="-2,0" Duration="6" />
				<Pose Image="/shime36.png" ImageAnchor="64,128" Velocity="-2,0" Duration="6" />
			</Animation>
		</Action>
		<Action Name="RunWithIe" BorderType="Floor" Type="Embedded" Class="com.group_finity.mascot.action.WalkWithIE"
			 IeOffsetX="0" IeOffsetY="-64">
			<Animation>
				<Pose Image="/shime34.png" ImageAnchor="64,128" Velocity="-8,0" Duration="2" />
				<Pose Image="/shime35.png" ImageAnchor="64,128" Velocity="-8,0" Duration="2" />
				<Pose Image="/shime34.png" ImageAnchor="64,128" Velocity="-8,0" Duration="2" />
				<Pose Image="/shime36.png" ImageAnchor="64,128" Velocity="-8,0" Duration="2" />
			</Animation>
		</Action>
		<Action Name="ThrowIe" BorderType="Floor" Type="Embedded" Class="com.group_finity.mascot.action.ThrowIE"
			InitialVX="32" InitialVY="-10" Gravity="0.5">
			<Animation>
				<Pose Image="/shime37.png" ImageAnchor="64,128" Velocity="0,0" Duration="40" />
			</Animation>
		</Action>

		<!-- Falling & Landing -->
		<Action Name="Jumping" Type="Embedded" Class="com.group_finity.mascot.action.Jump"
			VelocityParam="20">
			<Animation>
				<Pose Image="/shime22.png" ImageAnchor="64,128" Velocity="0,0" Duration="250" />
			</Animation>
		</Action>

		<Action Name="Falling" Type="Embedded" Class="com.group_finity.mascot.action.Fall"
			RegistanceX="0.05" RegistanceY="0.1" Gravity="2">
			<Animation>
				<Pose Image="/shime4.png" ImageAnchor="64,120" Velocity="0,0" Duration="250" />
			</Animation>
		</Action>

		<Action Name="Bouncing" Type="Animate" BorderType="Floor">
			<Animation>
				<Pose Image="/shime18.png" ImageAnchor="64,128" Velocity="0,0" Duration="12" />
				<Pose Image="/shime19.png" ImageAnchor="64,128" Velocity="0,0" Duration="16" />
			</Animation>
		</Action>

		<Action Name="Tripping" Type="Animate" BorderType="Floor">
			<Animation>
				<Pose Image="/shime18.png" ImageAnchor="64,128" Velocity="-4,0" Duration="10" />
				<Pose Image="/shime19.png" ImageAnchor="64,128" Velocity="-2,0" Duration="12" />
			</Animation>
		</Action>

		<!-- Dragging (Pinched by head/scruff at ImageAnchor 64,16) -->
		<Action Name="Pinched" Type="Embedded" Class="com.group_finity.mascot.action.Dragged">
			<Animation Condition="#{{FootX &lt; mascot.environment.cursor.x-50}}">
				<Pose Image="/shime9.png" ImageAnchor="64,16" Velocity="0,0" Duration="5" />
			</Animation>
			<Animation Condition="#{{FootX &lt; mascot.environment.cursor.x-30}}">
				<Pose Image="/shime7.png" ImageAnchor="64,16" Velocity="0,0" Duration="5" />
			</Animation>
			<Animation Condition="#{{FootX &lt; mascot.environment.cursor.x}}">
				<Pose Image="/shime5.png" ImageAnchor="64,16" Velocity="0,0" Duration="5" />
			</Animation>
			<Animation Condition="#{{FootX &gt; mascot.environment.cursor.x-10 &amp;&amp; FootX &lt; mascot.environment.cursor.x+10}}">
				<Pose Image="/shime107.png" ImageAnchor="64,16" Velocity="0,0" Duration="5" />
			</Animation>
			<Animation Condition="#{{FootX &lt; mascot.environment.cursor.x+30}}">
				<Pose Image="/shime6.png" ImageAnchor="64,16" Velocity="0,0" Duration="5"/>
			</Animation>
			<Animation Condition="#{{FootX &lt; mascot.environment.cursor.x+50}}">
				<Pose Image="/shime8.png" ImageAnchor="64,16" Velocity="0,0" Duration="5" />
			</Animation>
			<Animation Condition="#{{FootX &gt;= mascot.environment.cursor.x+30}}">
				<Pose Image="/shime10.png" ImageAnchor="64,16" Velocity="0,0" Duration="5" />
			</Animation>
		</Action>

		<Action Name="Resisting" Type="Embedded" Class="com.group_finity.mascot.action.Regist">
			<Animation>
				<Pose Image="/shime9.png" ImageAnchor="64,16" Velocity="0,0" Duration="5" />
				<Pose Image="/shime10.png" ImageAnchor="64,16" Velocity="0,0" Duration="5" />
				<Pose Image="/shime9.png" ImageAnchor="64,16" Velocity="0,0" Duration="5" />
				<Pose Image="/shime10.png" ImageAnchor="64,16" Velocity="0,0" Duration="5" />
				<Pose Image="/shime107.png" ImageAnchor="64,16" Velocity="0,0" Duration="40" />
				<Pose Image="/shime9.png" ImageAnchor="64,16" Velocity="0,0" Duration="4" />
				<Pose Image="/shime10.png" ImageAnchor="64,16" Velocity="0,0" Duration="4" />
				<Pose Image="/shime9.png" ImageAnchor="64,16" Velocity="0,0" Duration="4" />
				<Pose Image="/shime10.png" ImageAnchor="64,16" Velocity="0,0" Duration="4" />
				<Pose Image="/shime9.png" ImageAnchor="64,16" Velocity="0,0" Duration="3" />
				<Pose Image="/shime10.png" ImageAnchor="64,16" Velocity="0,0" Duration="3" />
				<Pose Image="/shime9.png" ImageAnchor="64,16" Velocity="0,0" Duration="3" />
				<Pose Image="/shime10.png" ImageAnchor="64,16" Velocity="0,0" Duration="3" />
			</Animation>
		</Action>
	</ActionList>

	<!-- Actual Behavior Sequences -->
	<ActionList>
		<!-- ALWAYS REQUIRED -->
		<Action Name="Fall" Type="Sequence" Loop="false">
			<ActionReference Name="Falling"/>
			<Action Type="Select">
				<Action Type="Sequence" Condition="${{mascot.environment.floor.isOn(mascot.anchor) || mascot.environment.activeIE.topBorder.isOn(mascot.anchor) }}">
					<ActionReference Name="Bouncing"/>
					<ActionReference Name="Stand" Duration="${{100+Math.random()*100}}" />
				</Action>
				<ActionReference Name="GrabWall" Duration="100" />
			</Action>
		</Action>

		<!-- ALWAYS REQUIRED -->
		<Action Name="Dragged" Type="Sequence" Loop="true">
			<ActionReference Name="Pinched"/>
			<ActionReference Name="Resisting" />
		</Action>

		<!-- ALWAYS REQUIRED -->
		<Action Name="Thrown" Type="Sequence" Loop="false">
			<ActionReference Name="Falling" InitialVX="${{mascot.environment.cursor.dx}}" InitialVY="${{mascot.environment.cursor.dy}}"/>
			<Action Type="Select">
				<Action Type="Sequence" Condition="${{mascot.environment.floor.isOn(mascot.anchor) || mascot.environment.activeIE.topBorder.isOn(mascot.anchor) }}">
					<ActionReference Name="Bouncing"/>
					<ActionReference Name="Stand" Duration="${{100+Math.random()*100}}" />
				</Action>
				<ActionReference Name="GrabWall" Duration="100" />
			</Action>
		</Action>

		<Action Name="StandUp" Type="Sequence" Loop="false">
			<ActionReference Name="Stand" Duration="${{200+Math.random()*400}}" />
		</Action>

		<Action Name="SitDown" Type="Sequence" Loop="false">
			<ActionReference Name="Sit" Duration="${{200+Math.random()*400}}" />
		</Action>

		<Action Name="LieDown" Type="Sequence" Loop="false">
			<ActionReference Name="Sprawl" Duration="${{300+Math.random()*500}}" />
		</Action>

		<!-- Custom Roa Behavior Sequences -->
		<Action Name="WaveGreeting" Type="Sequence" Loop="false">
			<ActionReference Name="WaveAction" />
			<ActionReference Name="Stand" Duration="${{60+Math.random()*60}}" />
		</Action>

		<Action Name="CelebrateJump" Type="Sequence" Loop="false">
			<ActionReference Name="CelebrateJumpAction" />
			<ActionReference Name="Stand" Duration="${{60+Math.random()*60}}" />
		</Action>

		<Action Name="CryingStamp" Type="Sequence" Loop="false">
			<ActionReference Name="CryingStampAction" />
			<ActionReference Name="Stand" Duration="${{60+Math.random()*60}}" />
		</Action>

		<Action Name="InquisitiveWait" Type="Sequence" Loop="false">
			<ActionReference Name="InquisitiveWaitAction" Duration="${{160+Math.random()*160}}" />
		</Action>

		<Action Name="HackerReview" Type="Sequence" Loop="false">
			<ActionReference Name="HackerReviewAction" Duration="${{200+Math.random()*250}}" />
		</Action>

		<Action Name="SleepingNap" Type="Sequence" Loop="false">
			<ActionReference Name="Sprawl" Duration="${{300+Math.random()*400}}" />
		</Action>

		<Action Name="SitWhileDanglingLegs" Type="Sequence" Loop="false">
			<ActionReference Name="SitWithLegsUp" Duration="10" />
			<ActionReference Name="SitWithLegsDown" Duration="${{60+Math.random()*60}}" />
			<ActionReference Name="SitAndDangleLegs" Duration="${{250+Math.random()*200}}" />
			<ActionReference Name="SitWithLegsDown" Duration="${{60+Math.random()*60}}" />
			<ActionReference Name="SitWithLegsUp" Duration="10" />
		</Action>

		<Action Name="HoldOntoWall" Type="Sequence" Loop="false">
			<ActionReference Name="GrabWall" Duration="${{200+Math.random()*400}}" />
		</Action>

		<Action Name="FallFromWall" Type="Sequence" Loop="false">
			<ActionReference Name="Offset" X="${{mascot.lookRight ? -1 : 1}}" />
			<ActionReference Name="Stand" />
		</Action>

		<Action Name="HoldOntoCeiling" Type="Sequence" Loop="false">
			<ActionReference Name="GrabCeiling" Duration="${{200+Math.random()*400}}" />
		</Action>

		<Action Name="FallFromCeiling" Type="Sequence" Loop="false">
			<ActionReference Name="Offset" Y="1" />
			<ActionReference Name="Stand" />
		</Action>

		<Action Name="WalkAlongWorkAreaFloor" Type="Sequence" Loop="false">
			<ActionReference Name="Walk" TargetX="${{mascot.environment.workArea.left+64+Math.random()*(mascot.environment.workArea.width-128)}}" />
		</Action>

		<Action Name="RunAlongWorkAreaFloor" Type="Sequence" Loop="false">
			<ActionReference Name="Run" TargetX="${{mascot.environment.workArea.left+64+Math.random()*(mascot.environment.workArea.width-128)}}" />
		</Action>

		<Action Name="CrawlAlongWorkAreaFloor" Type="Sequence" Loop="false">
			<ActionReference Name="Creep" TargetX="${{mascot.environment.workArea.left+64+Math.random()*(mascot.environment.workArea.width-128)}}" />
		</Action>

		<Action Name="WalkLeftAlongFloorAndSit" Type="Sequence" Loop="false">
			<ActionReference Name="Walk" TargetX="${{mascot.environment.workArea.left+64}}" />
			<ActionReference Name="Stand" Duration="${{50+Math.random()*50}}" />
			<ActionReference Name="Look" />
			<ActionReference Name="Stand" Duration="${{50+Math.random()*50}}" />
			<ActionReference Name="Sit" Duration="${{200+Math.random()*300}}" />
		</Action>

		<Action Name="WalkRightAlongFloorAndSit" Type="Sequence" Loop="false">
			<ActionReference Name="Walk" TargetX="${{mascot.environment.workArea.right-64}}" />
			<ActionReference Name="Stand" Duration="${{50+Math.random()*50}}" />
			<ActionReference Name="Look" />
			<ActionReference Name="Stand" Duration="${{50+Math.random()*50}}" />
			<ActionReference Name="Sit" Duration="${{200+Math.random()*300}}" />
		</Action>

		<Action Name="GrabWorkAreaBottomLeftWall" Type="Sequence" Loop="false">
			<ActionReference Name="Walk" TargetX="#{{mascot.environment.workArea.left}}" />
			<ActionReference Name="GrabWall" Duration="${{60+Math.random()*60}}" />
		</Action>

		<Action Name="GrabWorkAreaBottomRightWall" Type="Sequence" Loop="false">
			<ActionReference Name="Walk" TargetX="#{{mascot.environment.workArea.right}}" />
			<ActionReference Name="GrabWall" Duration="${{60+Math.random()*60}}" />
		</Action>

		<Action Name="WalkLeftAndSit" Type="Sequence" Loop="false">
			<ActionReference Name="Walk" TargetX="${{mascot.environment.workArea.left+64+Math.random()*(mascot.anchor.x-mascot.environment.workArea.left-64)}}" />
			<ActionReference Name="Stand" Duration="${{50+Math.random()*50}}" />
			<ActionReference Name="Look" />
			<ActionReference Name="Stand" Duration="${{50+Math.random()*50}}" />
			<ActionReference Name="Sit" Duration="${{200+Math.random()*300}}" />
		</Action>

		<Action Name="WalkRightAndSit" Type="Sequence" Loop="false">
			<ActionReference Name="Walk" TargetX="${{mascot.anchor.x+(mascot.environment.workArea.right-mascot.anchor.x-64)*Math.random()}}" />
			<ActionReference Name="Stand" Duration="${{50+Math.random()*50}}" />
			<ActionReference Name="Look" />
			<ActionReference Name="Stand" Duration="${{50+Math.random()*50}}" />
			<ActionReference Name="Sit" Duration="${{200+Math.random()*300}}" />
		</Action>

		<Action Name="WalkAndGrabBottomLeftWall" Type="Sequence" Loop="false">
			<ActionReference Name="Run" TargetX="#{{mascot.environment.workArea.left}}" />
			<ActionReference Name="GrabWall" Duration="${{60+Math.random()*60}}" />
		</Action>

		<Action Name="WalkAndGrabBottomRightWall" Type="Sequence" Loop="false">
			<ActionReference Name="Run" TargetX="#{{mascot.environment.workArea.right}}" />
			<ActionReference Name="GrabWall" Duration="${{60+Math.random()*60}}" />
		</Action>

		<Action Name="JumpFromBottomOfIE" Type="Sequence" Loop="false">
			<ActionReference Name="Jumping" TargetX="${{mascot.anchor.x}}" TargetY="${{mascot.environment.activeIE.bottom+64}}" />
			<ActionReference Name="GrabCeiling" Duration="${{100+Math.random()*100}}" />
		</Action>

		<Action Name="ClimbHalfwayAlongWall" Type="Sequence" Loop="false">
			<ActionReference Name="ClimbWall" TargetY="${{mascot.environment.workArea.top+64+Math.random()*(mascot.environment.workArea.height-128)}}" />
		</Action>

		<Action Name="ClimbAlongWall" Type="Sequence" Loop="false">
			<ActionReference Name="ClimbWall" TargetY="#{{mascot.environment.workArea.top}}" />
			<ActionReference Name="GrabCeiling" Duration="${{50+Math.random()*50}}" />
		</Action>

		<Action Name="ClimbAlongCeiling" Type="Sequence" Loop="false">
			<ActionReference Name="ClimbCeiling" TargetX="${{mascot.environment.workArea.left+64+Math.random()*(mascot.environment.workArea.width-128)}}" />
		</Action>

		<Action Name="WalkAlongIECeiling" Type="Sequence" Loop="false">
			<ActionReference Name="Walk" TargetX="${{mascot.environment.activeIE.left+64+Math.random()*(mascot.environment.activeIE.width-128)}}" />
		</Action>

		<Action Name="RunAlongIECeiling" Type="Sequence" Loop="false">
			<ActionReference Name="Run" TargetX="${{mascot.environment.activeIE.left+64+Math.random()*(mascot.environment.activeIE.width-128)}}" />
		</Action>

		<Action Name="CrawlAlongIECeiling" Type="Sequence" Loop="false">
			<ActionReference Name="Creep" TargetX="${{mascot.environment.activeIE.left+64+Math.random()*(mascot.environment.activeIE.width-128)}}" />
		</Action>

		<Action Name="SitOnTheLeftEdgeOfIE" Type="Sequence" Loop="false">
			<ActionReference Name="Walk" TargetX="${{mascot.environment.activeIE.left+100+Math.random()*300}}" />
			<ActionReference Name="Stand" Duration="${{100+Math.random()*100}}" />
			<ActionReference Name="Sit" Duration="${{300+Math.random()*300}}" />
		</Action>

		<Action Name="SitOnTheRightEdgeOfIE" Type="Sequence" Loop="false">
			<ActionReference Name="Walk" TargetX="${{mascot.environment.activeIE.right-100-Math.random()*300}}" />
			<ActionReference Name="Stand" Duration="${{100+Math.random()*100}}" />
			<ActionReference Name="Sit" Duration="${{300+Math.random()*300}}" />
		</Action>

		<Action Name="JumpFromLeftEdgeOfIE" Type="Sequence" Loop="false">
			<ActionReference Name="Walk" TargetX="${{mascot.environment.activeIE.left+Math.random()*50}}" />
			<ActionReference Name="Stand" Duration="${{50+Math.random()*50}}" />
			<ActionReference Name="Falling" InitialVX="${{-15-Math.random()*5}}" InitialVY="${{-20-Math.random()*5}}"/>
			<ActionReference Name="Bouncing" />
		</Action>

		<Action Name="JumpFromRightEdgeOfIE" Type="Sequence" Loop="false">
			<ActionReference Name="Walk" TargetX="${{mascot.environment.activeIE.right-Math.random()*50}}" />
			<ActionReference Name="Stand" Duration="${{50+Math.random()*50}}" />
			<ActionReference Name="Falling" InitialVX="${{15+Math.random()*5}}" InitialVY="${{-20-Math.random()*5}}"/>
			<ActionReference Name="Bouncing" />
		</Action>

		<Action Name="WalkLeftAlongIEAndSit" Type="Sequence" Loop="false">
			<ActionReference Name="Run" TargetX="${{mascot.environment.activeIE.left+100+Math.random()*300}}" />
			<ActionReference Name="Stand" Duration="${{100+Math.random()*100}}" />
			<ActionReference Name="Sit" Duration="${{300+Math.random()*300}}" />
		</Action>

		<Action Name="WalkRightAlongIEAndSit" Type="Sequence" Loop="false">
			<ActionReference Name="Run" TargetX="${{mascot.environment.activeIE.right-100-Math.random()*300}}" />
			<ActionReference Name="Stand" Duration="${{100+Math.random()*100}}" />
			<ActionReference Name="Sit" Duration="${{300+Math.random()*300}}" />
		</Action>

		<Action Name="WalkLeftAlongIEAndJump" Type="Sequence" Loop="false">
			<ActionReference Name="Run" TargetX="${{mascot.environment.activeIE.left+Math.random()*50}}" />
			<ActionReference Name="Falling" InitialVX="${{-15-Math.random()*5}}" InitialVY="${{-20-Math.random()*5}}"/>
			<ActionReference Name="Bouncing" />
		</Action>

		<Action Name="WalkRightAlongIEAndJump" Type="Sequence" Loop="false">
			<ActionReference Name="Run" TargetX="${{mascot.environment.activeIE.right-Math.random()*50}}" />
			<ActionReference Name="Falling" InitialVX="${{15+Math.random()*5}}" InitialVY="${{-20-Math.random()*5}}"/>
			<ActionReference Name="Bouncing" />
		</Action>

		<Action Name="DashIeCeilingLeftEdgeFromJump" Type="Sequence" Loop="false">
			<ActionReference Name="Dash" TargetX="${{mascot.environment.activeIE.left+Math.random()*20+20}}" />
			<ActionReference Name="Falling" InitialVX="${{-5-Math.random()*2}}" InitialVY="${{-20-Math.random()*5}}"/>
			<ActionReference Name="Bouncing" />
		</Action>

		<Action Name="DashIeCeilingRightEdgeFromJump" Type="Sequence" Loop="false">
			<ActionReference Name="Dash" TargetX="${{mascot.environment.activeIE.right-Math.random()*20-20}}" />
			<ActionReference Name="Falling" InitialVX="${{5+Math.random()*2}}" InitialVY="${{-20-Math.random()*5}}"/>
			<ActionReference Name="Bouncing" />
		</Action>

		<Action Name="HoldOntoIEWall" Type="Sequence" Loop="false">
			<ActionReference Name="ClimbWall" TargetY="${{mascot.environment.activeIE.top+64 + Math.random()*(mascot.environment.activeIE.height-128)}}" />
		</Action>

		<Action Name="ClimbIEWall" Type="Sequence" Loop="false">
			<ActionReference Name="ClimbWall" TargetY="#{{mascot.environment.activeIE.top+64}}" />
			<ActionReference Name="Offset" Y="-64" />
			<ActionReference Name="Sit" Duration="5" />
			<ActionReference Name="Stand" Duration="${{10+Math.random()*10}}" />
			<ActionReference Name="Walk" TargetX="${{mascot.lookRight ? mascot.environment.activeIE.left+Math.random()*100 : mascot.environment.activeIE.right-Math.random*100}}" />
		</Action>

		<Action Name="ClimbIEBottom" Type="Sequence" Loop="false">
			<ActionReference Name="ClimbCeiling" TargetX="${{mascot.environment.activeIE.left+64+(Math.random()*mascot.environment.activeIE.width-128)}}" />
		</Action>

		<Action Name="GrabIEBottomLeftWall" Type="Sequence" Loop="false">
			<ActionReference Name="ClimbCeiling" TargetX="#{{mascot.environment.activeIE.left}}" />
			<ActionReference Name="Look" />
			<ActionReference Name="ClimbWall" TargetY="#{{mascot.environment.activeIE.bottom-64}}" />
		</Action>

		<Action Name="GrabIEBottomRightWall" Type="Sequence" Loop="false">
			<ActionReference Name="ClimbCeiling" TargetX="#{{mascot.environment.activeIE.right}}" />
			<ActionReference Name="Look" />
			<ActionReference Name="ClimbWall" TargetY="#{{mascot.environment.activeIE.bottom-64}}" />
		</Action>

		<Action Name="JumpFromLeftWall" Type="Sequence" Loop="false">
			<ActionReference Name="Jumping" TargetX="${{mascot.environment.workArea.left}}" TargetY="${{mascot.environment.workArea.bottom-Math.random()*mascot.environment.workArea.height/4}}" />
			<ActionReference Name="GrabWall" Duration="${{100+Math.random()*100}}" />
		</Action>

		<Action Name="JumpFromRightWall" Type="Sequence" Loop="false">
			<ActionReference Name="Jumping" TargetX="${{mascot.environment.workArea.right}}" TargetY="${{mascot.environment.workArea.bottom-Math.random()*mascot.environment.workArea.height/4}}" />
			<ActionReference Name="GrabWall" Duration="${{100+Math.random()*100}}" />
		</Action>

		<Action Name="JumpOnIELeftWall" Type="Sequence" Loop="false">
			<ActionReference Name="Jumping" TargetX="${{mascot.environment.activeIE.left}}" TargetY="${{mascot.environment.activeIE.bottom-Math.random()*mascot.environment.activeIE.height/4}}" />
			<ActionReference Name="GrabWall" Duration="${{100+Math.random()*100}}" />
		</Action>

		<Action Name="JumpOnIERightWall" Type="Sequence" Loop="false">
			<ActionReference Name="Jumping" TargetX="${{mascot.environment.activeIE.right}}" TargetY="${{mascot.environment.activeIE.bottom-Math.random()*mascot.environment.activeIE.height/4}}" />
			<ActionReference Name="GrabWall" Duration="${{100+Math.random()*100}}" />
		</Action>

		<Action Name="ThrowIEFromLeft" Type="Sequence" Loop="false">
			<ActionReference Name="Jumping" TargetX="${{mascot.environment.activeIE.left}}" TargetY="${{mascot.environment.activeIE.bottom+64}}" />
			<ActionReference Name="FallWithIe" />
			<ActionReference Name="WalkWithIe" TargetX="#{{mascot.environment.workArea.right-400}}" />
			<ActionReference Name="ThrowIe" />
			<ActionReference Name="Stand" Duration="${{50+Math.random()*50}}" />
			<ActionReference Name="Look" />
			<ActionReference Name="Stand" Duration="${{50+Math.random()*50}}" />
		</Action>
		<Action Name="ThrowIEFromRight" Type="Sequence" Loop="false">
			<ActionReference Name="Jumping" TargetX="${{mascot.environment.activeIE.right}}" TargetY="${{mascot.environment.activeIE.bottom+64}}" />
			<ActionReference Name="FallWithIe" />
			<ActionReference Name="WalkWithIe" TargetX="#{{mascot.environment.workArea.left+400}}" />
			<ActionReference Name="ThrowIe" />
			<ActionReference Name="Stand" Duration="${{50+Math.random()*50}}" />
			<ActionReference Name="Look" />
			<ActionReference Name="Stand" Duration="${{50+Math.random()*50}}" />
		</Action>
		<Action Name="WalkAndThrowIEFromRight" Type="Sequence" Loop="false">
			<ActionReference Name="Jumping" TargetX="${{mascot.environment.activeIE.left}}" TargetY="${{mascot.environment.activeIE.bottom+64}}" />
			<ActionReference Name="FallWithIe" />
			<ActionReference Name="RunWithIe" TargetX="#{{mascot.environment.workArea.right-400}}" />
			<ActionReference Name="ThrowIe" />
			<ActionReference Name="Stand" Duration="${{50+Math.random()*50}}" />
			<ActionReference Name="Look" />
			<ActionReference Name="Stand" Duration="${{50+Math.random()*50}}" />
		</Action>
		<Action Name="WalkAndThrowIEFromLeft" Type="Sequence" Loop="false">
			<ActionReference Name="Jumping" TargetX="${{mascot.environment.activeIE.right}}" TargetY="${{mascot.environment.activeIE.bottom+64}}" />
			<ActionReference Name="FallWithIe" />
			<ActionReference Name="RunWithIe" TargetX="#{{mascot.environment.workArea.left+400}}" />
			<ActionReference Name="ThrowIe" />
			<ActionReference Name="Stand" Duration="${{50+Math.random()*50}}" />
			<ActionReference Name="Look" />
			<ActionReference Name="Stand" Duration="${{50+Math.random()*50}}" />
		</Action>

		<Action Name="ChaseMouse" Type="Sequence" Loop="false">
			<Action Type="Sequence" Condition="${{mascot.environment.ceiling.isOn(mascot.anchor) || mascot.environment.activeIE.bottomBorder.isOn(mascot.anchor)}}">
				<ActionReference Name="Offset" Y="1" />
				<ActionReference Name="Falling"/>
				<ActionReference Name="Bouncing" />
			</Action>
			<Action Type="Sequence" Condition="${{mascot.environment.workArea.leftBorder.isOn(mascot.anchor) || mascot.environment.activeIE.rightBorder.isOn(mascot.anchor)}}">
				<ActionReference Name="Offset" X="1" />
				<ActionReference Name="Falling"/>
				<ActionReference Name="Bouncing" />
			</Action>
			<Action Type="Sequence" Condition="${{mascot.environment.workArea.rightBorder.isOn(mascot.anchor) || mascot.environment.activeIE.leftBorder.isOn(mascot.anchor)}}">
				<ActionReference Name="Offset" X="-1" />
				<ActionReference Name="Falling"/>
				<ActionReference Name="Bouncing" />
			</Action>
			<Action Type="Select">
				<ActionReference Name="DashIeCeilingLeftEdgeFromJump"
					Condition="${{mascot.environment.activeIE.topBorder.isOn(mascot.anchor) &amp;&amp;
					mascot.anchor.x &lt; (mascot.environment.activeIE.left+mascot.environment.activeIE.right)/2}}"/>
				<ActionReference Name="DashIeCeilingRightEdgeFromJump"
					Condition="${{mascot.environment.activeIE.topBorder.isOn(mascot.anchor) &amp;&amp;
					mascot.anchor.x &gt;= (mascot.environment.activeIE.left+mascot.environment.activeIE.right)/2}}" />
			</Action>
			<ActionReference Name="Dash" TargetX="${{ mascot.anchor.x+(mascot.environment.cursor.x-mascot.anchor.x)*Math.random()/2 }}" />
			<ActionReference Name="Tripping" Condition="${{Math.random() &lt; 0.05}}" />
			<ActionReference Name="Dash" TargetX="${{ mascot.anchor.x+(mascot.environment.cursor.x-mascot.anchor.x)*Math.random() }}" />
			<ActionReference Name="Tripping" Condition="${{Math.random() &lt; 0.05}}" />
			<ActionReference Name="Dash" TargetX="#{{mascot.environment.cursor.x+Gap}}"
				Gap="${{ mascot.anchor.x &lt; mascot.environment.cursor.x ?
					-Math.min( mascot.environment.cursor.x-mascot.anchor.x, Math.random()*200) :
					Math.min( mascot.anchor.x-mascot.environment.cursor.x, Math.random()*200 ) }}" />
			<ActionReference Name="Look" LookRight="${{mascot.anchor.x &lt; mascot.environment.cursor.x}}" />
		</Action>

		<Action Name="SitAndFaceMouse" Type="Sequence" Loop="false">
			<ActionReference Name="SitAndLookAtMouse" Duration="${{10+Math.random()*10}}" />
			<ActionReference Name="Look" LookRight="${{mascot.anchor.x &lt; mascot.environment.cursor.x}}" />
			<ActionReference Name="SitAndLookAtMouse" Duration="${{10+Math.random()*10}}" />
			<ActionReference Name="Look" LookRight="${{mascot.anchor.x &lt; mascot.environment.cursor.x}}" />
			<ActionReference Name="SitAndLookAtMouse" Duration="${{10+Math.random()*10}}" />
			<ActionReference Name="Look" LookRight="${{mascot.anchor.x &lt; mascot.environment.cursor.x}}" />
		</Action>
		<Action Name="SitAndSpinHead" Type="Sequence" Loop="false">
			<ActionReference Name="SitAndSpinHeadAction" />
		</Action>

		<Action Name="PullUpShimeji1" Type="Embedded" Class="com.group_finity.mascot.action.Breed"
			BornX="-32" BornY="96" BornBehavior="PullUp">
			<Animation>
				<Pose Image="/shime1.png" ImageAnchor="64,128" Velocity="0,0" Duration="16" />
				<Pose Image="/shime38.png" ImageAnchor="64,128" Velocity="0,0" Duration="4" />
				<Pose Image="/shime39.png" ImageAnchor="64,128" Velocity="0,0" Duration="20" />
				<Pose Image="/shime40.png" ImageAnchor="64,128" Velocity="0,0" Duration="20" />
				<Pose Image="/shime41.png" ImageAnchor="64,128" Velocity="0,0" Duration="20" />
			</Animation>
		</Action>
		<Action Name="PullUpShimeji2" Type="Animate">
			<Animation>
				<Pose Image="/shime9.png" ImageAnchor="32,128" Velocity="20,-20" Duration="1" />
				<Pose Image="/shime9.png" ImageAnchor="32,128" Velocity="20,-10" Duration="1" />
				<Pose Image="/shime9.png" ImageAnchor="32,128" Velocity="20,-5" Duration="1" />
			</Animation>
		</Action>
		<Action Name="PullUpShimeji" Type="Sequence">
			<ActionReference Name="PullUpShimeji1" />
			<ActionReference Name="PullUpShimeji2" />
			<ActionReference Name="Falling" InitialVX="${{mascot.lookRight ? -20 : 20}}"/>
			<ActionReference Name="Bouncing" />
			<ActionReference Name="Sprawl" Duration="40" />
		</Action>

		<Action Name="PullUp" Type="Sequence">
			<ActionReference Name="Falling" InitialVX="${{mascot.lookRight ? 10 : -10}}" InitialVY="-40"/>
			<ActionReference Name="Bouncing" />
		</Action>
		<Action Name="Divide1" Type="Embedded" Class="com.group_finity.mascot.action.Breed"
			BornX="-16" BornY="0" BornBehavior="Divided">
			<Animation>
				<Pose Image="/shime42.png" ImageAnchor="64,128" Velocity="0,0" Duration="5" />
				<Pose Image="/shime43.png" ImageAnchor="64,128" Velocity="0,0" Duration="5" />
				<Pose Image="/shime44.png" ImageAnchor="64,128" Velocity="0,0" Duration="5" />
				<Pose Image="/shime45.png" ImageAnchor="64,128" Velocity="0,0" Duration="5" />
				<Pose Image="/shime46.png" ImageAnchor="64,128" Velocity="0,0" Duration="20" />
			</Animation>
		</Action>
		<Action Name="SplitIntoTwo" Type="Sequence">
			<ActionReference Name="Divide1" />
			<ActionReference Name="Offset" X="16" />
			<ActionReference Name="Look" />
			<ActionReference Name="Divided" />
		</Action>
		<Action Name="Divided" Type="Sequence">
			<ActionReference Name="Falling" InitialVX="${{mascot.lookRight ? 10 : -10}}" InitialVY="-5"/>
			<ActionReference Name="Bouncing" />
		</Action>
	</ActionList>

</Mascot>
"""

with open(os.path.join(SHIJIMA_BUILD_DIR, "actions.xml"), "w", encoding="utf-8") as f:
    f.write(actions_xml)

with open("/tmp/default_behaviors.xml", "r", encoding="utf-8-sig") as f:
    behaviors_xml = f.read()

custom_floor_behaviors = """			<Behavior Name="StandUp" Frequency="150" Hidden="true" />
			<Behavior Name="WaveGreeting" Frequency="120" />
			<Behavior Name="CelebrateJump" Frequency="100" />
			<Behavior Name="InquisitiveWait" Frequency="120" />
			<Behavior Name="HackerReview" Frequency="120" />
			<Behavior Name="SleepingNap" Frequency="100" />
			<Behavior Name="CryingStamp" Frequency="60" />"""

behaviors_xml = behaviors_xml.replace(
    '\t\t\t<Behavior Name="StandUp" Frequency="200" Hidden="true" />',
    custom_floor_behaviors
)

with open(os.path.join(SHIJIMA_BUILD_DIR, "behaviors.xml"), "w", encoding="utf-8") as f:
    f.write(behaviors_xml)

# ==========================================
# 6. PACKAGE roa_shijima.zip
# ==========================================
zip_path = os.path.join(BASE_DIR, "roa_shijima.zip")
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    zf.write(os.path.join(SHIJIMA_BUILD_DIR, "actions.xml"), arcname="Roa/actions.xml")
    zf.write(os.path.join(SHIJIMA_BUILD_DIR, "behaviors.xml"), arcname="Roa/behaviors.xml")
    for fn in sorted(os.listdir(SHIJIMA_IMG_DIR)):
        if fn.endswith(".png"):
            zf.write(os.path.join(SHIJIMA_IMG_DIR, fn), arcname=f"Roa/img/{fn}")

# Also export animated preview GIFs for the 4 new Shijima actions
def save_gif(frames, out_name, dur=150):
    p_frames = []
    for f in frames:
        alpha = f.split()[3]
        rgb = f.convert("RGB")
        p_img = rgb.quantize(colors=255, method=Image.Resampling.LANCZOS)
        p_mask = Image.eval(alpha, lambda a: 255 if a < 128 else 0)
        p_img.paste(255, p_mask)
        p_img.info["transparency"] = 255
        p_frames.append(p_img)
    p_frames[0].save(
        os.path.join(BASE_DIR, out_name),
        save_all=True,
        append_images=p_frames[1:],
        duration=dur,
        loop=0,
        disposal=2,
        transparency=255
    )

save_gif([wall_frames_128[0], wall_frames_128[1], wall_frames_128[2], wall_frames_128[1]], "wall_climb_cycle.gif", dur=160)
save_gif([ceiling_frames_128[0], ceiling_frames_128[1], ceiling_frames_128[2], ceiling_frames_128[1]], "ceiling_crawl_cycle.gif", dur=160)
save_gif([pinched_frames_128[0], pinched_frames_128[1], pinched_right_mild, pinched_frames_128[1], pinched_struggle_1, pinched_struggle_2], "pinched_cycle.gif", dur=150)
save_gif([fall_land_128[0], fall_land_128[1], fall_land_128[2], fall_land_128[2]], "fall_land_cycle.gif", dur=220)

print(f"=== SHIJIMA BUILD COMPLETE: {zip_path} ({os.path.getsize(zip_path)} bytes) ===")
