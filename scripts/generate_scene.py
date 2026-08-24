#!/usr/bin/env python3
"""Gera cena base estilizada para Ambience Session."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def lerp_color(
    start: tuple[int, int, int], end: tuple[int, int, int], t: float
) -> tuple[int, int, int]:
    return tuple(int(s + (e - s) * t) for s, e in zip(start, end))


def draw_monitor(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    frame_color: tuple[int, int, int],
    code_colors: list[tuple[int, int, int]],
) -> None:
    left, top, right, bottom = box
    draw.rounded_rectangle(box, radius=8, fill=frame_color)
    inner = (left + 12, top + 12, right - 12, bottom - 12)
    draw.rounded_rectangle(inner, radius=4, fill=(12, 14, 22))
    line_y = inner[1] + 16
    for index, color in enumerate(code_colors):
        width = 80 + (index * 37) % 120
        draw.rectangle(
            (inner[0] + 16, line_y, inner[0] + 16 + width, line_y + 6),
            fill=color,
        )
        line_y += 14
        if line_y > inner[3] - 20:
            break


def draw_steam(draw: ImageDraw.ImageDraw, origin: tuple[int, int]) -> None:
    x, y = origin
    cream = hex_to_rgb("#f5e6d3")
    for offset, alpha in [(0, 90), (12, 70), (-10, 60), (20, 50)]:
        color = (*cream, alpha)
        draw.ellipse((x + offset, y - 40, x + offset + 18, y), fill=color)


def draw_rain_overlay(width: int, height: int) -> Image.Image:
    rng = np.random.default_rng(42)
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for _ in range(180):
        x = int(rng.integers(0, width))
        y = int(rng.integers(0, height))
        length = int(rng.integers(8, 22))
        draw.line((x, y, x - 2, y + length), fill=(180, 200, 230, 35), width=1)
    return overlay.filter(ImageFilter.GaussianBlur(0.5))


def generate_scene(output: Path, width: int = 1920, height: int = 1080) -> None:
    midnight = hex_to_rgb("#1a1a2e")
    navy = hex_to_rgb("#16213e")
    cream = hex_to_rgb("#f5e6d3")
    accent = hex_to_rgb("#e94560")
    code_green = hex_to_rgb("#4ecca3")
    rain_blue = hex_to_rgb("#0f3460")

    pixels = np.zeros((height, width, 3), dtype=np.uint8)
    for y in range(height):
        t = y / height
        color = lerp_color(midnight, navy, t * 0.8)
        pixels[y, :] = color

    image = Image.fromarray(pixels, mode="RGB")
    draw = ImageDraw.Draw(image)

    draw.rectangle((0, height - 280, width, height), fill=(30, 22, 18))
    draw.rectangle((120, height - 320, width - 80, height - 40), fill=(45, 32, 24))

    window_box = (width - 520, 80, width - 40, height - 300)
    draw.rounded_rectangle(window_box, radius=6, fill=(20, 30, 50))
    draw.rounded_rectangle(
        (window_box[0] + 8, window_box[1] + 8, window_box[2] - 8, window_box[3] - 8),
        radius=4,
        fill=rain_blue,
    )

    for i in range(6):
        x = window_box[0] + 40 + i * 70
        draw.ellipse((x, window_box[1] + 60, x + 30, window_box[1] + 90), fill=(255, 200, 120))

    draw_monitor(
        draw,
        (160, height - 290, 620, height - 80),
        (35, 35, 42),
        [code_green, cream, accent, (100, 149, 237), code_green, cream],
    )
    draw_monitor(
        draw,
        (660, height - 290, 1120, height - 80),
        (35, 35, 42),
        [cream, code_green, (147, 112, 219), accent, cream, code_green],
    )

    draw.rounded_rectangle((200, height - 70, 520, height - 30), fill=(28, 28, 32))
    for key_x in range(210, 500, 18):
        draw.rectangle((key_x, height - 62, key_x + 12, height - 38), fill=(50, 50, 55))

    draw.ellipse((130, height - 120, 190, height - 60), fill=(80, 50, 30))
    draw.ellipse((135, height - 125, 185, height - 75), fill=(40, 25, 15))
    draw.ellipse((140, height - 130, 180, height - 85), fill=(30, 18, 10))
    draw_steam(draw, (155, height - 145))

    draw.ellipse((80, height - 200, 110, height - 170), fill=(40, 80, 50))

    pendant_y = 40
    for px in (300, 600, 900):
        draw.line((px, 0, px, pendant_y + 20), fill=(60, 50, 40), width=3)
        draw.ellipse((px - 25, pendant_y, px + 25, pendant_y + 50), fill=(255, 180, 80))

    rain = draw_rain_overlay(width, height)
    image = image.convert("RGBA")
    image = Image.alpha_composite(image, rain)
    image = image.convert("RGB")
    image = image.filter(ImageFilter.GaussianBlur(0.3))

    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, format="PNG", optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera cena base Ambience Session")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    args = parser.parse_args()
    generate_scene(args.output, args.width, args.height)
    print(f"Scene saved: {args.output}")


if __name__ == "__main__":
    main()
