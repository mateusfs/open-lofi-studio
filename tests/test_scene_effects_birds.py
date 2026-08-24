from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from scene_effects import apply_scene_effects, render_birds, render_foliage_shimmer


def _window_base() -> tuple[np.ndarray, Image.Image]:
    base = np.full((1080, 1920, 3), 40, dtype=np.uint8)
    base[120:320, 240:1680] = [170, 195, 235]
    base[320:720, 240:1680] = [70, 140, 75]
    mask = Image.new("L", (1920, 1080), 0)
    draw = ImageDraw.Draw(mask)
    draw.rectangle((240, 120, 1680, 720), fill=255)
    return base, mask


def test_render_birds_returns_rgba_overlay() -> None:
    base, mask = _window_base()
    frame = Image.fromarray(base, mode="RGB")
    result = render_birds(frame, frame_index=36, total_frames=288, window_mask=mask, seed=127)
    assert result.mode == "RGBA"
    assert result.size == (1920, 1080)


def test_birds_stay_in_sky_band() -> None:
    base, mask = _window_base()
    frame = Image.fromarray(base, mode="RGB")
    plain = np.asarray(frame.convert("RGB"), dtype=np.int16)
    diffs: list[int] = []
    for frame_index in (12, 36, 72, 120, 180):
        result = render_birds(frame, frame_index=frame_index, total_frames=288, window_mask=mask, seed=127)
        delta = np.abs(np.asarray(result.convert("RGB"), dtype=np.int16) - plain)
        changed = delta.sum(axis=2) > 8
        ys, _xs = np.where(changed)
        if ys.size:
            diffs.append(int(ys.max()))
    assert diffs
    assert max(diffs) < 360


def test_foliage_shimmer_changes_green_region() -> None:
    base, mask = _window_base()
    frame = Image.fromarray(base, mode="RGB")
    plain = apply_scene_effects(base, 0, 288, [], 127, mask, None)
    shimmer = render_foliage_shimmer(frame, 48, 288, mask, 127)
    assert shimmer.mode == "RGBA"
    assert not np.array_equal(np.asarray(plain.convert("RGB")), np.asarray(shimmer.convert("RGB")))


def test_apply_scene_effects_includes_birds_and_foliage() -> None:
    base, mask = _window_base()
    plain = apply_scene_effects(base, 0, 288, [], 127, mask, None)
    animated = apply_scene_effects(base, 48, 288, ["foliage_shimmer", "birds"], 127, mask, None)
    assert animated.mode == "RGBA"
    assert not np.array_equal(np.asarray(plain.convert("RGB")), np.asarray(animated.convert("RGB")))
