#!/usr/bin/env python3
"""Gera effect-mask.png a partir da cena base para modos hybrid."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

WIDTH = 1920
HEIGHT = 1080


def generate_effect_mask(scene_path: Path, output: Path) -> Path:
    image = Image.open(scene_path).convert("RGB").resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    arr = np.asarray(image, dtype=np.float32)
    luma = 0.2126 * arr[:, :, 0] + 0.7152 * arr[:, :, 1] + 0.0722 * arr[:, :, 2]
    yy = np.linspace(0, 1, HEIGHT)[:, None]
    air = np.clip(1.0 - (yy - 0.02) / 0.9, 0.0, 1.0) ** 1.15
    glow = np.clip((luma - 70.0) / 140.0, 0.0, 1.0)
    center_y = int(HEIGHT * 0.58)
    center_x = int(WIDTH * 0.45)
    grid_y, grid_x = np.ogrid[:HEIGHT, :WIDTH]
    desk = np.exp(
        -(
            ((grid_y - center_y) / (HEIGHT * 0.2)) ** 2
            + ((grid_x - center_x) / (WIDTH * 0.28)) ** 2
        )
    )
    mask = np.clip(air * (0.3 + 0.7 * glow) * (1.0 - 0.65 * desk), 0.0, 1.0)
    mask_image = Image.fromarray((mask * 255.0).astype(np.uint8), mode="L")
    mask_image = mask_image.filter(ImageFilter.GaussianBlur(40))
    output.parent.mkdir(parents=True, exist_ok=True)
    mask_image.save(output)
    return output


def ensure_effect_mask(scene_path: Path, output: Path, force: bool = False) -> Path | None:
    if not scene_path.exists():
        return None
    if output.exists() and not force and output.stat().st_size > 1_000:
        return output
    return generate_effect_mask(scene_path, output)


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera effect-mask.png a partir da cena")
    parser.add_argument("--scene", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    path = ensure_effect_mask(args.scene.resolve(), args.output.resolve(), force=args.force)
    if path is None:
        raise SystemExit(f"Cena ausente: {args.scene}")
    print(f"Mask saved: {path}")


if __name__ == "__main__":
    main()
