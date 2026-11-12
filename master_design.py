#!/usr/bin/env python3
"""
Master Design Auto-Propagation Module for Roa (Codex Pets & Shijima).

Single Source of Truth:
  - `assets/master_head.png` (350x450 RGBA master head design)
  - Propagates the approved design modifications across all 10 pose sheets:
      1. Crescent Moon in FRONT of the Cloud (true circular bottom arc, cleaned lower-left bump)
      2. Long Hair Osage (~2x length, down to y=316 in base coords) under the Cyan Sphere + Blue Ribbon,
         replacing all white pearl bead chains while keeping the sphere & ribbon intact
         and tucking naturally behind any raised arms/hands.
"""
import os
import math
from collections import deque
from PIL import Image

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
MASTER_HEAD_PATH = os.path.join(ASSETS_DIR, "master_head.png")

# Canonical palette sampled from Roa's master head
H_OUTLINE = (24, 34, 88, 255)       # Crisp dark navy hair outline
H_DARK    = (48, 68, 148, 255)      # Deep hair crease / inner border
H_SHADOW  = (88, 112, 202, 255)     # Hair shadow strand
H_BASE    = (124, 152, 236, 255)    # Main hair blue
H_LIGHT   = (156, 182, 248, 255)    # Hair highlight strand

M_BORDER_DARK = (105, 58, 22, 255)
M_BORDER_MID  = (135, 80, 32, 255)
M_SHADOW_DEEP = (232, 165, 75, 255)
M_SHADOW_SOFT = (245, 192, 98, 255)
M_YELLOW      = (255, 219, 120, 255)


def load_palette_from_master():
    """
    If `assets/master_head.png` exists, sample its key colors dynamically so that
    color adjustments to `assets/master_head.png` automatically propagate to all assets.
    """
    global H_OUTLINE, H_DARK, H_SHADOW, H_BASE, H_LIGHT
    global M_BORDER_DARK, M_BORDER_MID, M_SHADOW_DEEP, M_SHADOW_SOFT, M_YELLOW
    if not os.path.exists(MASTER_HEAD_PATH):
        return
    mh = Image.open(MASTER_HEAD_PATH).convert("RGBA")
    H_OUTLINE = mh.getpixel((28, 265))
    H_DARK    = mh.getpixel((29, 265))
    H_LIGHT   = mh.getpixel((36, 265))
    H_BASE    = mh.getpixel((41, 265))
    H_SHADOW  = mh.getpixel((46, 265))
    M_YELLOW      = mh.getpixel((257, 193))
    M_SHADOW_SOFT = mh.getpixel((257, 197))
    M_SHADOW_DEEP = mh.getpixel((257, 199))
    M_BORDER_MID  = mh.getpixel((257, 201))
    M_BORDER_DARK = mh.getpixel((257, 202))


def is_warm_skin_mask(orig_img):
    """
    Build a boolean mask of foreground warm skin/hand pixels (and their 2px dark outlines)
    so that long hair osage automatically tucks BEHIND raised arms/hands.
    """
    w, h = orig_img.size
    opix = orig_img.load()
    raw_skin = [[False] * h for _ in range(w)]
    for y in range(h):
        for x in range(w):
            r, g, b, a = opix[x, y]
            if a > 128 and r > 175 and g > 135 and (r - b) >= 10 and (r >= g):
                raw_skin[x][y] = True

    visited = [[False] * h for _ in range(w)]
    skin_mask = [[False] * h for _ in range(w)]
    for y in range(h):
        for x in range(w):
            if raw_skin[x][y] and not visited[x][y]:
                comp = []
                q = deque([(x, y)])
                visited[x][y] = True
                while q:
                    cx, cy = q.popleft()
                    comp.append((cx, cy))
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < w and 0 <= ny < h and not visited[nx][ny] and raw_skin[nx][ny]:
                            visited[nx][ny] = True
                            q.append((nx, ny))
                if len(comp) >= 35:
                    for px, py in comp:
                        skin_mask[px][py] = True

    dilated = [col[:] for col in skin_mask]
    for y in range(2, h - 2):
        for x in range(2, w - 2):
            if not skin_mask[x][y]:
                r, g, b, a = opix[x, y]
                is_outline_or_warm = a > 128 and ((r < 120 and g < 100 and b < 130) or (r - b >= 5))
                if is_outline_or_warm:
                    near = False
                    for dy in range(-2, 3):
                        for dx in range(-2, 3):
                            if abs(dx) + abs(dy) <= 3 and skin_mask[x + dx][y + dy]:
                                near = True
                                break
                        if near:
                            break
                    if near:
                        dilated[x][y] = True
    return dilated


def apply_moon_in_front(img, orig_img, mc_x, mc_y, scale=1.0):
    """
    Render the true circular Crescent Moon in front of the Cloud at (mc_x, mc_y) with `scale`.
    (mc_x, mc_y) is aligned so that x0 = mc_x - 5*scale, y0 = mc_y - 5*scale.
    """
    pix = img.load()
    opix = orig_img.load()
    w, h = img.size

    x0 = mc_x - 5.0 * scale
    y0 = mc_y - 5.0 * scale

    CX, CY, R_OUT = 31.8, 31.2, 26.0

    px_start = max(0, int(math.floor(x0 + 0 * scale)))
    px_end   = min(w - 1, int(math.ceil(x0 + 58 * scale)))

    px_unit = 1.0 / max(1.0, scale)
    t_bdark = 0.9 if scale < 0.6 else max(0.9, 1.0 * px_unit)
    t_bmid  = 1.6 if scale < 0.6 else max(1.9, 2.0 * px_unit)
    t_sdeep = 3.2 if scale < 0.6 else max(3.6, 3.5 * px_unit)
    t_ssoft = 5.0 if scale < 0.6 else max(5.8, 5.5 * px_unit)

    for px in range(px_start, px_end + 1):
        gx = (px - x0) / scale
        dx = gx - CX

        if abs(dx) > R_OUT:
            for py in range(max(0, int(y0 + 24 * scale)), min(h, int(y0 + 55 * scale))):
                gy_clean = (py - y0) / scale
                r, g, b, a = opix[px, py]
                if a > 128 and b < 210:
                    pix[px, py] = H_BASE if gy_clean < 43 else (150, 175, 242, 255)
            continue

        gy_true_bot = CY + math.sqrt(max(0.0, R_OUT**2 - dx**2))
        py_bot_int = int(round(y0 + gy_true_bot * scale))

        # 1. Clean below py_bot_int where the old distorted lower-left bump was (gx: 5..25)
        py_clean_start = max(int(round(y0 + 36 * scale)), py_bot_int + 1)
        py_clean_end   = min(h - 1, int(round(y0 + 62 * scale)))
        for py in range(py_clean_start, py_clean_end + 1):
            gy_clean = (py - y0) / scale
            r, g, b, a = opix[px, py]
            if a > 128 and ((b < 185 and r > 75) or (gx <= 21 and gy_clean <= 59 and b < 210)):
                if gx >= 17 and gy_clean >= 53:
                    if gx < 17.8:
                        pix[px, py] = (72, 96, 175, 255)
                    elif gx < 18.8:
                        pix[px, py] = (185, 202, 242, 255)
                    else:
                        pix[px, py] = (248, 250, 255, 255)
                elif gy_clean <= 43:
                    pix[px, py] = H_BASE
                elif gy_clean <= 49:
                    pix[px, py] = (162, 185, 246, 255)
                else:
                    pix[px, py] = H_BASE

        # 2. Draw the true circular moon bottom arc for gx: 7..57
        if 7.0 <= gx <= 57.0:
            start_py = None
            for py_scan in range(max(0, int(round(y0 + 25 * scale))), min(h, int(round(y0 + 52 * scale)))):
                r, g, b, a = opix[px, py_scan]
                if a > 128 and r > 165 and g > 125 and (r - b) >= 25:
                    start_py = py_scan
                    break
            if start_py is None:
                continue

            for py in range(start_py, min(h - 1, py_bot_int) + 1):
                gy = (py - y0) / scale
                if gy < 33.0:
                    continue
                dist = math.hypot(gx - CX, gy - CY)
                edge_dist = R_OUT - dist

                if edge_dist <= t_bdark or py == py_bot_int or gx <= 7.0 + px_unit * 0.8:
                    pix[px, py] = M_BORDER_DARK
                elif edge_dist <= t_bmid:
                    pix[px, py] = M_BORDER_MID
                elif edge_dist <= t_sdeep:
                    pix[px, py] = M_SHADOW_DEEP
                elif edge_dist <= t_ssoft:
                    pix[px, py] = M_SHADOW_SOFT
                else:
                    pix[px, py] = M_YELLOW


def apply_left_osage(img, orig_img, lb_x, lb_y, scale, bg_color, skin_mask, clean_inner_pearls=False, width_scale=1.0):
    """
    Erase the old white 4-bead chain under the Left Ball+Ribbon at (lb_x, lb_y, scale)
    and draw the double-length Left Hair Osage, respecting `skin_mask` (raised arms).
    If `clean_inner_pearls` is True, also restores any second inner white pearl strand
    drawn on top of the main blue bob hair (x_orig in 54..82) back to H_BASE.
    """
    pix = img.load()
    opix = orig_img.load()
    w, h = img.size

    ox = lb_x - 40.0 * scale
    oy = lb_y - 164.0 * scale

    # 1A. Erase outer white pearl chain (outside main bob hair) to bg_color
    py_erase_start = max(0, int(round(oy + 216 * scale)))
    py_erase_end   = min(h - 1, int(round(oy + 286 * scale)))
    dy_step = max(1, int(round(2 * scale)))
    for py in range(py_erase_start, py_erase_end + 1):
        y_orig = (py - oy) / scale
        main_hair_edge_orig = 56.0 - (y_orig - 218.0) * (7.0 / 62.0)
        px_start = max(0, int(round(ox + 16 * scale)))
        px_end   = min(w - 1, int(round(ox + main_hair_edge_orig * scale)))
        for px in range(px_start, px_end + 1):
            if skin_mask[px][py]:
                continue
            x_orig = (px - ox) / scale
            r, g, b, a = opix[px, py]
            is_ribbon_body = (b - r > 42 and y_orig <= 238 and x_orig >= 29)
            r_up, g_up, b_up, _ = opix[px, max(0, py - dy_step)]
            is_ribbon_outline = (y_orig <= 236 and x_orig >= 28 and b > 65 and r < 65 and (b_up - r_up > 38))
            if not (is_ribbon_body or is_ribbon_outline):
                pix[px, py] = bg_color

    # 1B. If pose has an inner second white pearl strand on top of the left bob hair, restore it to H_BASE
    if clean_inner_pearls:
        for py in range(max(0, int(round(oy + 220 * scale))), min(h - 1, int(round(oy + 286 * scale))) + 1):
            y_orig = (py - oy) / scale
            px_start = max(0, int(round(ox + 50 * scale)))
            px_end   = min(w - 1, int(round(ox + 85 * scale)))
            for px in range(px_start, px_end + 1):
                if skin_mask[px][py]:
                    continue
                r, g, b, a = opix[px, py]
                is_ribbon = (b - r > 42 and r < 100 and y_orig <= 240)
                if is_ribbon:
                    continue
                # White/grey pearl pixel or dark pearl outline surrounded by hair on the left bob
                is_pearl_white = (r > 155 and g > 165 and b > 195 and (b - r) < 42)
                is_pearl_outline = (y_orig >= 225 and (r < 95 or (b - r < 55 and b < 195)))
                if is_pearl_white or is_pearl_outline:
                    pix[px, py] = H_BASE

    # 2. Draw Left Long Osage (y_orig in 220..316)
    py_draw_start = max(0, int(round(oy + 220 * scale)))
    py_draw_end   = min(h - 1, int(round(oy + 316 * scale)))
    for py in range(py_draw_start, py_draw_end + 1):
        y_orig = (py - oy) / scale
        if y_orig < 220.0 or y_orig > 316.5:
            continue

        if y_orig < 265.0:
            st = (y_orig - 220.0) / 45.0
            xl_orig = 44.0 - 16.0 * math.sin(st * math.pi * 0.5)
        elif y_orig < 292.0:
            xl_orig = 28.0 + (y_orig - 265.0) / 14.0
        else:
            st = (y_orig - 292.0) / 24.0
            xl_orig = 29.0 + 5.0 * (st ** 1.2)

        if y_orig < 290.0:
            seam_orig = 55.0 - (y_orig - 220.0) * (11.0 / 70.0)
            xr_orig = seam_orig + 5.0
        else:
            st = (y_orig - 290.0) / 26.0
            seam_orig = 44.0 - 10.0 * (st ** 0.95)
            xr_orig = seam_orig

        xl_scaled = seam_orig - (seam_orig - xl_orig) * width_scale
        px_l = max(0, int(round(ox + xl_scaled * scale)))
        px_r = min(w - 1, int(round(ox + xr_orig * scale)))
        px_seam = int(round(ox + seam_orig * scale))
        lock_w = max(1, px_seam - px_l)
        out_w = max(1, int(round(scale)))

        for px in range(px_l, px_r + 1):
            if skin_mask[px][py]:
                continue
            r_cur, g_cur, b_cur, a_cur = pix[px, py]
            if a_cur > 128 and (b_cur - r_cur > 42 or (r_cur < 65 and b_cur > 65)) and y_orig <= 236.5:
                continue

            if px < px_l + out_w or (y_orig >= 290.0 and px > px_r - out_w):
                pix[px, py] = H_OUTLINE
            elif px < px_l + 2 * out_w:
                pix[px, py] = H_DARK
            elif abs(px - px_seam) < out_w:
                pix[px, py] = H_OUTLINE if y_orig >= 290.0 else H_DARK
            elif px > px_seam:
                pix[px, py] = H_OUTLINE if px > px_r - out_w else H_DARK
            else:
                rel = (px - px_l) / float(lock_w)
                if 0.25 <= rel <= 0.50 and y_orig < 298.0:
                    pix[px, py] = H_LIGHT
                elif rel < 0.75:
                    pix[px, py] = H_BASE
                else:
                    pix[px, py] = H_SHADOW


def apply_right_osage_frontal(img, orig_img, rb_x, rb_y, scale, bg_color, skin_mask, width_scale=1.0):
    """
    Erase the old white 4-bead chain under the Right Ball+Ribbon at (rb_x, rb_y, scale)
    and draw the symmetrical Right Long Hair Osage, respecting `skin_mask`.
    In orig_head, rb_x=286, rb_y=164.
    """
    pix = img.load()
    opix = orig_img.load()
    w, h = img.size

    ox = rb_x - 286.0 * scale
    oy = rb_y - 164.0 * scale

    # 1. Erase old white 4-bead chain on Right
    py_erase_start = max(0, int(round(oy + 216 * scale)))
    py_erase_end   = min(h - 1, int(round(oy + 286 * scale)))
    dy_step = max(1, int(round(2 * scale)))
    for py in range(py_erase_start, py_erase_end + 1):
        y_orig = (py - oy) / scale
        main_hair_edge_orig = 370.0 - (56.0 - (y_orig - 218.0) * (7.0 / 62.0))
        px_start = max(0, int(round(ox + (main_hair_edge_orig + 1.0) * scale)))
        px_end   = min(w - 1, int(round(ox + 356 * scale)))
        for px in range(px_start, px_end + 1):
            if skin_mask[px][py]:
                continue
            x_orig = (px - ox) / scale
            r, g, b, a = opix[px, py]
            is_ribbon_body = (b - r > 42 and y_orig <= 238 and x_orig <= 341)
            r_up, g_up, b_up, _ = opix[px, max(0, py - dy_step)]
            is_ribbon_outline = (y_orig <= 236 and x_orig <= 342 and b > 65 and r < 65 and (b_up - r_up > 38))
            if not (is_ribbon_body or is_ribbon_outline):
                pix[px, py] = bg_color

    # 2. Draw Right Long Osage (y_orig in 220..316)
    py_draw_start = max(0, int(round(oy + 220 * scale)))
    py_draw_end   = min(h - 1, int(round(oy + 316 * scale)))
    for py in range(py_draw_start, py_draw_end + 1):
        y_orig = (py - oy) / scale
        if y_orig < 220.0 or y_orig > 316.5:
            continue

        if y_orig < 265.0:
            st = (y_orig - 220.0) / 45.0
            xl_orig = 44.0 - 16.0 * math.sin(st * math.pi * 0.5)
        elif y_orig < 292.0:
            xl_orig = 28.0 + (y_orig - 265.0) / 14.0
        else:
            st = (y_orig - 292.0) / 24.0
            xl_orig = 29.0 + 5.0 * (st ** 1.2)

        if y_orig < 290.0:
            seam_orig = 55.0 - (y_orig - 220.0) * (11.0 / 70.0)
            xr_orig = seam_orig + 5.0
        else:
            st = (y_orig - 290.0) / 26.0
            seam_orig = 44.0 - 10.0 * (st ** 0.95)
            xr_orig = seam_orig

        r_seam_orig = 370.0 - seam_orig
        r_xl_orig = 370.0 - xr_orig
        r_xr_orig = r_seam_orig + (seam_orig - xl_orig) * width_scale

        px_l = max(0, int(round(ox + r_xl_orig * scale)))
        px_r = min(w - 1, int(round(ox + r_xr_orig * scale)))
        px_seam = int(round(ox + r_seam_orig * scale))
        lock_w = max(1, px_r - px_seam)
        out_w = max(1, int(round(scale)))

        for px in range(px_l, px_r + 1):
            if skin_mask[px][py]:
                continue
            r_cur, g_cur, b_cur, a_cur = pix[px, py]
            if a_cur > 128 and (b_cur - r_cur > 42 or (r_cur < 65 and b_cur > 65)) and y_orig <= 236.5:
                continue

            if px > px_r - out_w or (y_orig >= 290.0 and px < px_l + out_w):
                pix[px, py] = H_OUTLINE
            elif px > px_r - 2 * out_w:
                pix[px, py] = H_DARK
            elif abs(px - px_seam) < out_w:
                pix[px, py] = H_OUTLINE if y_orig >= 290.0 else H_DARK
            elif px < px_seam:
                pix[px, py] = H_OUTLINE if px < px_l + out_w else H_DARK
            else:
                rel = (px_r - px) / float(lock_w)
                if 0.25 <= rel <= 0.50 and y_orig < 298.0:
                    pix[px, py] = H_LIGHT
                elif rel < 0.75:
                    pix[px, py] = H_BASE
                else:
                    pix[px, py] = H_SHADOW


def apply_profile_osage(img, orig_img, lb_x, lb_y, scale):
    """
    For chibi_base.jpg Pose 1 (side profile facing right, lb_x=432, lb_y=164):
    Clean both pearl strands inside the side hair profile and draw a flowing blue osage lock!
    """
    pix = img.load()
    opix = orig_img.load()
    ox = lb_x - 40.0 * scale
    oy = lb_y - 164.0 * scale

    # First clean the two white pearl strands inside the profile hair (x_orig: 36..86, y_orig: 225..280)
    for py in range(int(round(oy + 225 * scale)), int(round(oy + 282 * scale)) + 1):
        y_orig = (py - oy) / scale
        for px in range(int(round(ox + 36 * scale)), int(round(ox + 86 * scale)) + 1):
            r, g, b, _ = opix[px, py]
            if b - r > 42 and r < 100 and y_orig <= 242:
                continue
            if r > 150 or (b - r < 45):
                pix[px, py] = H_BASE

    # Draw the profile osage lock
    for py in range(int(round(oy + 225 * scale)), int(round(oy + 316 * scale)) + 1):
        y_orig = (py - oy) / scale
        t = (y_orig - 225.0) / 91.0
        cx_orig = 63.0 - 6.0 * math.sin(t * math.pi * 0.6)
        half_w = 13.0 * (1.0 - 0.65 * (t ** 1.4))
        xl = int(round(ox + (cx_orig - half_w) * scale))
        xr = int(round(ox + (cx_orig + half_w) * scale))
        w_lock = max(1, xr - xl)
        for px in range(xl, xr + 1):
            r_cur, g_cur, b_cur, _ = opix[px, py]
            if b_cur - r_cur > 45 and r_cur < 100 and y_orig <= 240:
                continue
            if px == xl or px == xr or y_orig >= 315:
                pix[px, py] = H_OUTLINE
            elif px == xl + 1 or px == xr - 1:
                pix[px, py] = H_DARK
            else:
                rel = (px - xl) / float(w_lock)
                if 0.3 <= rel <= 0.55 and y_orig < 300:
                    pix[px, py] = H_LIGHT
                elif rel < 0.75:
                    pix[px, py] = H_BASE
                else:
                    pix[px, py] = H_SHADOW


def apply_run_strip_moon_in_front(img):
    """
    Bring the crescent moon in front of the white cloud across all 4 frames
    of `assets/run_strip.png` with a single clean crescent bottom arc and
    without the old lower-left double bump.
    """
    pix = img.load()
    Y  = (254, 225, 118, 255)  # crisp bright moon yellow
    y  = (242, 204, 108, 255)  # soft gold edge
    B  = (128, 86, 48, 255)    # crisp moon brown outline
    HB = (131, 147, 231, 255)  # hair blue to clean old lower-left bump
    CW = (252, 252, 253, 255)  # cloud white
    CS = (185, 185, 202, 255)  # cloud top shadow

    def paint_rows(ox, oy, rows_spec):
        for dy, cols in rows_spec.items():
            for dx, col in cols.items():
                pix[ox + dx, oy + dy] = col

    # Frame 0 (ox=104, oy=46)
    paint_rows(104, 46, {
        11: {5: B, 6: B},
        12: {5: B, 6: Y, 7: B, 8: B, 9: B, 10: B, 11: Y, 12: Y, 13: Y, 14: Y, 15: y, 16: B},
        13: {5: HB, 6: B, 7: Y, 8: Y, 9: Y, 10: Y, 11: Y, 12: Y, 13: Y, 14: y, 15: B, 16: CS},
        14: {6: HB, 7: B, 8: B, 9: B, 10: B, 11: B, 12: B, 13: B, 14: B, 15: CS},
        15: {6: HB, 7: HB, 8: HB, 9: CS, 10: CW},
    })

    # Frame 1 (ox=296, oy=46)
    paint_rows(296, 46, {
        11: {5: HB, 6: B, 7: B},
        12: {6: B, 7: Y, 8: B, 9: B, 10: B, 11: B, 12: Y, 13: Y, 14: Y, 15: Y, 16: y, 17: B},
        13: {5: HB, 6: HB, 7: B, 8: Y, 9: Y, 10: Y, 11: Y, 12: Y, 13: Y, 14: Y, 15: y, 16: B, 17: CS},
        14: {6: HB, 7: HB, 8: B, 9: B, 10: B, 11: B, 12: B, 13: B, 14: B, 15: B, 16: CS},
        15: {6: HB, 7: HB, 8: HB, 9: HB, 10: CS, 11: CW},
    })

    # Frame 2 (ox=488, oy=46)
    paint_rows(488, 46, {
        14: {5: B, 6: B},
        15: {5: B, 6: Y, 7: B, 8: B, 9: B, 10: B, 11: Y, 12: Y, 13: Y, 14: Y, 15: y, 16: B},
        16: {5: HB, 6: B, 7: Y, 8: Y, 9: Y, 10: Y, 11: Y, 12: Y, 13: Y, 14: y, 15: B, 16: CS},
        17: {6: HB, 7: B, 8: B, 9: B, 10: B, 11: B, 12: B, 13: B, 14: B, 15: CS},
        18: {6: HB, 7: HB, 8: HB, 9: CS, 10: CW},
    })

    # Frame 3 (ox=680, oy=46)
    paint_rows(680, 46, {
        14: {6: B, 7: B},
        15: {6: B, 7: Y, 8: B, 9: B, 10: B, 11: B, 12: Y, 13: Y, 14: Y, 15: Y, 16: y, 17: B},
        16: {6: HB, 7: B, 8: Y, 9: Y, 10: Y, 11: Y, 12: Y, 13: Y, 14: Y, 15: y, 16: B, 17: CS},
        17: {6: HB, 7: HB, 8: B, 9: B, 10: B, 11: B, 12: B, 13: B, 14: B, 15: B, 16: CS},
        18: {7: HB, 8: HB, 9: HB, 10: CS, 11: CW},
    })


# Deterministic, pixel-verified per-asset head anchor table:
#   mc: (mc_x, mc_y, mc_scale) aligned to exact moon right/top contour
#   lb: (lb_x, lb_y, lb_scale) aligned to exact left hair edge & left ribbon bottom
#   rb: (rb_x, rb_y, rb_scale) aligned to exact right hair edge & right ribbon bottom
#   inner_l: True when the base art has a 2nd inner white pearl string on top of the left hair
ASSET_HEAD_SPECS = {
    "chibi_base.jpg": {
        "bg": (255, 255, 255, 255),
        "heads": [
            {"mc": (230, 150, 1.0),  "lb": (40, 164, 1.0),   "rb": (286, 164, 1.0)},
            {"mc": None,             "lb": (432, 164, 1.0),  "rb": "profile"},
            {"mc": (906, 139, 1.0),  "lb": (721, 158, 0.98), "rb": (960, 156, 0.98)},
            {"mc": (1244, 150, 1.0), "lb": (1054, 164, 1.0), "rb": (1300, 164, 1.0)},
        ],
    },
    "crying_sheet.jpg": {
        "bg": (255, 255, 255, 255),
        "heads": [
            {"mc": (234, 130, 1.05),  "lb": (27, 150, 1.05),   "rb": (292, 150, 1.05),  "lw_scale": 0.72, "rw_scale": 0.56},
            {"mc": (577, 130, 1.05),  "lb": (371, 150, 1.05),  "rb": (636, 150, 1.05),  "lw_scale": 0.72, "rw_scale": 0.56},
            {"mc": (912, 130, 1.05),  "lb": (709, 150, 1.05),  "rb": (972, 150, 1.05),  "lw_scale": 0.72, "rw_scale": 0.56},
            {"mc": (1247, 130, 1.05), "lb": (1043, 150, 1.05), "rb": (1307, 150, 1.05), "lw_scale": 0.65, "rw_scale": 0.56},
        ],
    },
    "waiting_jitome.png": {
        "bg": (0, 0, 0, 0),
        "heads": [
            {"mc": (429, 191, 2.06), "lb": (25, 244, 2.05), "rb": (543, 222, 2.05)},
        ],
    },
    "sleeping_nap.png": {
        "bg": (0, 0, 0, 0),
        "heads": [
            {"mc": (247, 115, 1.08), "lb": (19, 136, 1.02), "rb": (305, 142, 1.00), "inner_l": True, "rw_scale": 0.72},
        ],
    },
    "hacker_typing.png": {
        "bg": (0, 0, 0, 0),
        "heads": [
            {"mc": (284, 112, 1.05), "lb": (38, 132, 1.02), "rb": (325, 146, 1.00), "inner_l": True, "rw_scale": 0.72},
        ],
    },
    "wall_climb_hybrid.jpg": {
        "bg": (255, 255, 255, 255),
        "heads": [
            {"mc": (241, 128, 0.88),  "lb": (69, 175, 0.90),   "rb": (284, 145, 0.88), "inner_l": True, "rw_scale": 0.58},
            {"mc": (721, 139, 0.87),  "lb": (540, 172, 0.90),  "rb": (755, 150, 0.88), "inner_l": True, "rw_scale": 0.58},
            {"mc": (1195, 136, 0.88), "lb": (1019, 178, 0.90), "rb": (1236, 150, 0.88), "inner_l": True, "rw_scale": 0.58},
        ],
    },
    "ceiling_crawl.jpg": {
        "bg": (255, 255, 255, 255),
        "heads": [
            {"mc": (241, 128, 0.88),  "lb": (69, 175, 0.90),   "rb": (284, 145, 0.88), "inner_l": True, "rw_scale": 0.58},
            {"mc": (722, 138, 0.87),  "lb": (540, 172, 0.90),  "rb": (755, 150, 0.88), "inner_l": True, "rw_scale": 0.58},
            {"mc": (1195, 136, 0.88), "lb": (1019, 178, 0.90), "rb": (1236, 150, 0.88), "inner_l": True, "rw_scale": 0.58},
        ],
    },
    "pinched_dragged.jpg": {
        "bg": (255, 255, 255, 255),
        "heads": [
            {"mc": (241, 128, 0.88),  "lb": (69, 175, 0.90),   "rb": (284, 145, 0.88), "inner_l": True, "rw_scale": 0.58},
            {"mc": (721, 139, 0.87),  "lb": (540, 172, 0.90),  "rb": (755, 150, 0.88), "inner_l": True, "rw_scale": 0.58},
            {"mc": (1195, 136, 0.88), "lb": (1019, 178, 0.90), "rb": (1236, 150, 0.88), "inner_l": True, "rw_scale": 0.58},
        ],
    },
    "fall_and_land.jpg": {
        "bg": (255, 255, 255, 255),
        "heads": [
            {"mc": (247, 126, 0.92),  "lb": (69, 185, 0.90),   "rb": (310, 140, 0.88), "inner_l": True, "rw_scale": 0.58},
            {"mc": (753, 204, 0.90),  "lb": (558, 224, 0.90),  "rb": (810, 225, 0.90), "inner_l": True, "rw_scale": 0.72},
            {"mc": (1224, 165, 0.92), "lb": (1028, 179, 0.90), "rb": (1280, 185, 0.90), "inner_l": True, "rw_scale": 0.72},
        ],
    },
}


def patch_asset_image(filename, img=None):
    """
    Load and return a patched RGBA `PIL.Image` for `assets/<filename>` with
    all master head design modifications applied.
    """
    load_palette_from_master()
    if img is None:
        path = os.path.join(ASSETS_DIR, filename)
        img = Image.open(path).convert("RGBA")
    else:
        img = img.convert("RGBA").copy()

    if filename == "run_strip.png":
        apply_run_strip_moon_in_front(img)
        return img

    if filename not in ASSET_HEAD_SPECS:
        return img

    orig_img = img.copy()
    spec = ASSET_HEAD_SPECS[filename]
    bg_color = spec["bg"]
    skin_mask = is_warm_skin_mask(orig_img)

    for hspec in spec["heads"]:
        if hspec["mc"] is not None:
            mc_x, mc_y, mc_s = hspec["mc"]
            apply_moon_in_front(img, orig_img, mc_x, mc_y, mc_s)

        if hspec["lb"] is not None:
            lb_x, lb_y, lb_s = hspec["lb"]
            if hspec["rb"] == "profile":
                apply_profile_osage(img, orig_img, lb_x, lb_y, lb_s)
            else:
                clean_inner = hspec.get("inner_l", False)
                lw_s = hspec.get("lw_scale", 1.0)
                apply_left_osage(img, orig_img, lb_x, lb_y, lb_s, bg_color, skin_mask, clean_inner_pearls=clean_inner, width_scale=lw_s)

        if isinstance(hspec["rb"], tuple):
            rb_x, rb_y, rb_s = hspec["rb"]
            rw_s = hspec.get("rw_scale", 1.0)
            apply_right_osage_frontal(img, orig_img, rb_x, rb_y, rb_s, bg_color, skin_mask, width_scale=rw_s)

    return img


def ensure_master_head(force=False):
    """
    Ensure `assets/master_head.png` (350x450 RGBA) exists.
    If it already exists and `force=False`, keep the existing file so user edits to
    `assets/master_head.png` are preserved and propagated as the single source of truth.
    """
    if os.path.exists(MASTER_HEAD_PATH) and not force:
        return Image.open(MASTER_HEAD_PATH).convert("RGBA")
    cb = Image.open(os.path.join(ASSETS_DIR, "chibi_base.jpg")).convert("RGBA")
    head = cb.crop((0, 0, 350, 450))
    orig_head = head.copy()
    skin_mask = is_warm_skin_mask(orig_head)
    apply_moon_in_front(head, orig_head, 230, 150, 1.0)
    apply_left_osage(head, orig_head, 40, 164, 1.0, (255, 255, 255, 255), skin_mask)
    apply_right_osage_frontal(head, orig_head, 286, 164, 1.0, (255, 255, 255, 255), skin_mask)
    head.save(MASTER_HEAD_PATH)
    print(f"Saved canonical master head to {MASTER_HEAD_PATH}")
    return head


if __name__ == "__main__":
    import subprocess
    import sys

    force_reset = "--reset-master" in sys.argv
    ensure_master_head(force=force_reset)
    print("Propagating master design from assets/master_head.png to all deliverables...")
    subprocess.run([sys.executable, os.path.join(BASE_DIR, "build.py")], check=True)
    subprocess.run([sys.executable, os.path.join(BASE_DIR, "build_shijima.py")], check=True)
    print("All deliverables (roa.codex-pet & roa_shijima.zip) updated successfully!")
