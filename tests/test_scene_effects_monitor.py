from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from scene_effects import apply_scene_effects, render_city_haze, render_desk_lamp_breathe


def _dark_desk_base() -> tuple[np.ndarray, Image.Image]:
    base = np.full((1080, 1920, 3), 18, dtype=np.uint8)
    base[220:520, 760:1160] = [70, 130, 190]
    base[480:620, 1500:1780] = [190, 120, 55]
    base[820:900, 700:1220] = [30, 55, 70]
    mask = Image.new("L", (1920, 1080), 0)
    draw = ImageDraw.Draw(mask)
    draw.rectangle((80, 160, 420, 720), fill=255)
    return base, mask


def test_desk_lamp_breathe_is_slow_and_gentle() -> None:
    base, _mask = _dark_desk_base()
    low = render_desk_lamp_breathe(base, frame_index=0, total_frames=288)
    mid = render_desk_lamp_breathe(base, frame_index=72, total_frames=288)
    near = render_desk_lamp_breathe(base, frame_index=3, total_frames=288)
    assert low.dtype == np.uint8
    assert abs(int(low[540, 1640, 0]) - int(near[540, 1640, 0])) <= 2
    assert abs(int(low[370, 960, 2]) - int(base[370, 960, 2])) <= 4
    assert not np.array_equal(low, mid)


def test_city_haze_returns_rgba() -> None:
    base, mask = _dark_desk_base()
    frame = Image.fromarray(base, mode="RGB")
    result = render_city_haze(frame, frame_index=40, total_frames=288, seed=130, window_mask=mask)
    assert result.mode == "RGBA"
    assert result.size == (1920, 1080)


def test_apply_scene_effects_calm_flow_stack() -> None:
    base, mask = _dark_desk_base()
    plain = apply_scene_effects(base, 0, 288, [], 130, mask, None)
    animated = apply_scene_effects(
        base,
        48,
        288,
        ["city_haze", "desk_lamp_breathe"],
        130,
        mask,
        None,
    )
    assert animated.mode == "RGBA"
    assert not np.array_equal(
        np.asarray(plain.convert("RGB")),
        np.asarray(animated.convert("RGB")),
    )
