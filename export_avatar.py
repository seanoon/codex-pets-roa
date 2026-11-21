#!/usr/bin/env python3
"""Export Roa profile avatar with customizable or transparent background."""
import argparse
import os
from PIL import Image, ImageOps

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MASTER = os.path.join(BASE_DIR, "assets", "avatar_roa_transparent.png")
DEFAULT_BG_HEX = "#DCF1FC"


def parse_hex_color(value: str) -> tuple[int, int, int, int]:
    """Parse #RRGGBB or #RRGGBBAA hex string into an RGBA tuple."""
    s = value.strip().lstrip("#")
    if len(s) == 6:
        return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), 255)
    if len(s) == 8:
        return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), int(s[6:8], 16))
    raise ValueError(f"Invalid hex color: {value!r} (expected #RRGGBB or #RRGGBBAA)")


def render_avatar(
    fg_img: Image.Image,
    bg_color: str = DEFAULT_BG_HEX,
    bg_image_path: str | None = None,
    size: int | None = None,
) -> Image.Image:
    """Composite the transparent Roa foreground over a solid color, image, or transparency."""
    w, h = fg_img.size
    if bg_image_path:
        bg = Image.open(bg_image_path).convert("RGBA")
        canvas = ImageOps.fit(bg, (w, h), method=Image.Resampling.LANCZOS)
    elif bg_color.strip().lower() == "transparent":
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    else:
        canvas = Image.new("RGBA", (w, h), parse_hex_color(bg_color))

    canvas.alpha_composite(fg_img)
    if size and size != w:
        canvas = canvas.resize((size, size), Image.Resampling.LANCZOS)
    return canvas


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export Roa Slack/Discord avatar from transparent master."
    )
    parser.add_argument(
        "--input",
        default=DEFAULT_MASTER,
        help="Path to transparent foreground PNG (default: assets/avatar_roa_transparent.png)",
    )
    parser.add_argument(
        "--bg",
        default=DEFAULT_BG_HEX,
        help=f"Background hex color or 'transparent' (default: {DEFAULT_BG_HEX})",
    )
    parser.add_argument(
        "--bg-image",
        default=None,
        help="Optional background image path (cropped/fitted to square, overrides --bg)",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=None,
        help="Output square pixel size (e.g., 512). Defaults to master size (1024).",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output PNG path (default: roa_avatar.png, or roa_avatar_transparent.png if --bg transparent)",
    )
    parser.add_argument(
        "--both",
        action="store_true",
        help="Export both roa_avatar.png (with background) and roa_avatar_transparent.png",
    )
    args = parser.parse_args()

    fg = Image.open(args.input).convert("RGBA")

    if args.both:
        out_bg = args.output or os.path.join(BASE_DIR, "roa_avatar.png")
        out_tr = os.path.join(BASE_DIR, "roa_avatar_transparent.png")
        render_avatar(fg, bg_color=args.bg, bg_image_path=args.bg_image, size=args.size).save(out_bg, "PNG")
        render_avatar(fg, bg_color="transparent", size=args.size).save(out_tr, "PNG")
        print(f"Exported: {out_bg}")
        print(f"Exported: {out_tr}")
        return

    is_transparent = args.bg_image is None and args.bg.strip().lower() == "transparent"
    default_out = "roa_avatar_transparent.png" if is_transparent else "roa_avatar.png"
    out_path = args.output or os.path.join(BASE_DIR, default_out)

    result = render_avatar(fg, bg_color=args.bg, bg_image_path=args.bg_image, size=args.size)
    result.save(out_path, "PNG")
    print(f"Exported: {out_path} ({result.size[0]}x{result.size[1]})")


if __name__ == "__main__":
    main()
