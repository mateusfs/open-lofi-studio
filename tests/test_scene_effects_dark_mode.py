from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from scene_effects import (
    apply_scene_effects,
    render_desk_specular,
    render_plant_sway,
    render_rgb_breathe,
    render_screen_bloom,
)


def _dark_mode_base() -> np.ndarray:
    base = np.full((1080, 1920, 3), 14, dtype=np.uint8)
    base[180:520, 420:900] = [55, 95, 140]
    base[180:520, 1020:1500] = [50, 90, 135]
    base[200:520, 40:280] = [28, 78, 40]
    base[780:900, 700:1220] = [25, 40, 55]
    base[700:820, 200:360] = [30, 70, 95]
    base[700:820, 1560:1760] = [70, 35, 85]
    return base


def test_rgb_breathe_is_slow() -> None:
    base = _dark_mode_base()
    a = render_rgb_breathe(base, 0, 480)
    b = render_rgb_breathe(base, 3, 480)
    c = render_rgb_breathe(base, 120, 480)
    assert abs(int(a[820, 300, 2]) - int(b[820, 300, 2])) <= 3
    assert not np.array_equal(a, c)


def test_screen_bloom_avoids_upper_monitor() -> None:
    base = _dark_mode_base()
    bloomed = render_screen_bloom(base, 90, 480)
    assert abs(int(bloomed[250, 960, 2]) - int(base[250, 960, 2])) <= 6
    assert bloomed[620, 960, 2] >= base[620, 960, 2]


def test_plant_sway_changes_left_green() -> None:
    base = _dark_mode_base()
    a = render_plant_sway(base, 0, 480)
    b = render_plant_sway(base, 120, 480)
    assert a[300, 120, 1] >= base[300, 120, 1]
    assert not np.array_equal(a, b)


def test_desk_specular_moves() -> None:
    base = _dark_mode_base()
    a = render_desk_specular(base, 0, 480)
    b = render_desk_specular(base, 120, 480)
    assert not np.array_equal(a, b)


def test_apply_scene_effects_dark_mode_stack() -> None:
    base = _dark_mode_base()
    plain = apply_scene_effects(base, 0, 480, [], 140, None, None)
    animated = apply_scene_effects(
        base,
        120,
        480,
        ["rgb_breathe", "screen_bloom", "keyboard_underglow", "desk_lamp_breathe", "plant_sway", "desk_specular"],
        140,
        None,
        None,
    )
    assert animated.mode == "RGBA"
    assert not np.array_equal(
        np.asarray(plain.convert("RGB")),
        np.asarray(animated.convert("RGB")),
    )
