#!/usr/bin/env python3
"""Gera overlays de calibração de vapor e chuva para revisão visual."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from animate_scene import (
    HEIGHT,
    WIDTH,
    load_scene,
    resolve_detection,
)


def _draw_crosshair(draw: ImageDraw.ImageDraw, x: int, y: int, color: tuple[int, int, int], size: int = 24) -> None:
    draw.line((x - size, y, x + size, y), fill=color, width=2)
    draw.line((x, y - size, x, y + size), fill=color, width=2)
    draw.ellipse((x - 4, y - 4, x + 4, y + 4), outline=color, width=2)


def _blend_rain_mask(scene: Image.Image, rain_mask: Image.Image) -> Image.Image:
    mask_array = np.asarray(rain_mask, dtype=np.float32) / 255.0
    scene_array = np.asarray(scene.convert("RGB"), dtype=np.float32)
    tint = np.zeros_like(scene_array)
    tint[:, :, 0] = 80
    tint[:, :, 1] = 160
    tint[:, :, 2] = 255
    upper_limit = int(HEIGHT * 0.65)
    mask_array[upper_limit:, :] = 0.0
    blended = scene_array * (1.0 - mask_array[:, :, None] * 0.45) + tint * (mask_array[:, :, None] * 0.45)
    return Image.fromarray(np.clip(blended, 0, 255).astype(np.uint8), mode="RGB")


def calibrate_production(production_dir: Path) -> dict[str, object]:
    meta_path = production_dir / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    animate = meta.get("animate", {})
    scene_path = production_dir / "source" / "scene-base.png"
    if not scene_path.exists():
        raise FileNotFoundError(f"Cena não encontrada: {scene_path}")

    fallback = (int(animate.get("steamX", 1010)), int(animate.get("steamY", 800)))
    auto_rain = bool(animate.get("autoRain", True) and not animate.get("noRain", False))
    auto_steam = bool(animate.get("autoSteam", True) and not animate.get("noSteam", False))

    base = load_scene(scene_path)
    scene_image = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), mode="RGB")
    rain_mask, detection = resolve_detection(base, fallback, auto_rain=auto_rain, auto_steam=auto_steam)

    source_dir = production_dir / "source"
    source_dir.mkdir(parents=True, exist_ok=True)

    steam_overlay = scene_image.copy()
    steam_draw = ImageDraw.Draw(steam_overlay)
    _draw_crosshair(steam_draw, fallback[0], fallback[1], (140, 140, 140))
    _draw_crosshair(steam_draw, detection.steam_x, detection.steam_y, (220, 40, 40))
    steam_path = source_dir / "calibration-steam.png"
    steam_overlay.save(steam_path)

    rain_path = source_dir / "calibration-rain.png"
    if rain_mask is None:
        scene_image.save(rain_path)
    else:
        _blend_rain_mask(scene_image, rain_mask).save(rain_path)

    result: dict[str, object] = {
        "steam": {
            "detected_x": detection.steam_x,
            "detected_y": detection.steam_y,
            "fallback_x": fallback[0],
            "fallback_y": fallback[1],
            "auto": detection.steam_auto,
            "confidence": round(detection.confidence_steam, 4),
            "used_fallback": not detection.steam_auto,
        },
        "rain": {
            "auto": detection.rain_auto,
            "confidence": round(detection.confidence_rain, 4),
            "enabled": auto_rain,
        },
        "outputs": {
            "steam_overlay": str(steam_path),
            "rain_overlay": str(rain_path),
        },
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Calibra detecção de vapor/chuva em uma produção")
    parser.add_argument("--production", type=Path, required=True)
    args = parser.parse_args()
    production_dir = args.production.resolve()
    result = calibrate_production(production_dir)
    steam = result["steam"]
    assert isinstance(steam, dict)
    print(
        f"Vapor detectado: ({steam['detected_x']}, {steam['detected_y']}) "
        f"conf={steam['confidence']} auto={steam['auto']} "
        f"fallback=({steam['fallback_x']}, {steam['fallback_y']}) "
        f"usou_fallback={steam['used_fallback']}"
    )
    rain = result["rain"]
    assert isinstance(rain, dict)
    if rain["enabled"]:
        print(
            f"Chuva: auto={rain['auto']} conf={rain['confidence']}"
        )
    outputs = result["outputs"]
    assert isinstance(outputs, dict)
    print(f"Overlay vapor: {outputs['steam_overlay']}")
    print(f"Overlay chuva: {outputs['rain_overlay']}")


if __name__ == "__main__":
    main()
