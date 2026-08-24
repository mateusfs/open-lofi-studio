from __future__ import annotations

import unittest
from pathlib import Path

import numpy as np

from animate_scene import (
    STEAM_CONFIDENCE_MIN,
    detect_steam_origin,
    detect_window_mask,
    load_scene,
    resolve_detection,
)

ROOT = Path(__file__).resolve().parent.parent
STEAM_TOLERANCE_X = 80
STEAM_TOLERANCE_Y = 60


def _scene_path(relative: str) -> Path:
    path = ROOT / relative
    if not path.exists():
        raise unittest.SkipTest(f"Fixture ausente: {path}")
    return path


class DetectionTests(unittest.TestCase):
    def test_steam_016_right_side(self) -> None:
        base = load_scene(_scene_path("assets/scenes/016-rainy-night-coding-seoul-han-river/scene-base.png"))
        origin, auto, confidence = detect_steam_origin(base, (1450, 780))
        self.assertTrue(auto)
        self.assertGreater(confidence, STEAM_CONFIDENCE_MIN)
        self.assertGreater(origin[0], 1200)

    def test_steam_032_center(self) -> None:
        base = load_scene(_scene_path("assets/scenes/032-space-programming-sessio-deep-orbit/scene-base.png"))
        origin, auto, confidence = detect_steam_origin(base, (1100, 760))
        self.assertTrue(auto)
        self.assertGreater(confidence, STEAM_CONFIDENCE_MIN)
        self.assertGreater(origin[0], 950)
        self.assertLess(origin[0], 1150)

    def test_steam_034_left_center(self) -> None:
        base = load_scene(_scene_path("assets/scenes/034-space-programming-sessio-lunar-base/scene-base.png"))
        origin, auto, confidence = detect_steam_origin(base, (820, 728))
        self.assertTrue(auto)
        self.assertGreater(confidence, STEAM_CONFIDENCE_MIN)
        self.assertGreater(origin[0], 750)
        self.assertLess(origin[0], 900)

    def test_steam_040_left(self) -> None:
        base = load_scene(
            _scene_path("productions/040-ai-research-lab-server-hum/source/scene-base.png")
        )
        origin, auto, confidence = detect_steam_origin(base, (390, 585))
        self.assertTrue(auto)
        self.assertGreater(confidence, STEAM_CONFIDENCE_MIN)
        self.assertGreater(origin[0], 350)
        self.assertLess(origin[0], 500)

    def test_steam_within_tolerance_032(self) -> None:
        base = load_scene(_scene_path("assets/scenes/032-space-programming-sessio-deep-orbit/scene-base.png"))
        origin, auto, _ = detect_steam_origin(base, (1100, 760))
        self.assertTrue(auto)
        self.assertLessEqual(abs(origin[0] - 1100), STEAM_TOLERANCE_X)
        self.assertLessEqual(abs(origin[1] - 760), STEAM_TOLERANCE_Y)

    def test_steam_fallback_on_low_confidence(self) -> None:
        synthetic = np.full((1080, 1920, 3), 128.0, dtype=np.float32)
        fallback = (321, 654)
        origin, auto, confidence = detect_steam_origin(synthetic, fallback)
        self.assertFalse(auto)
        self.assertEqual(origin, fallback)
        self.assertLess(confidence, STEAM_CONFIDENCE_MIN)

    def test_rain_mask_016_covers_window_not_desk(self) -> None:
        base = load_scene(_scene_path("assets/scenes/016-rainy-night-coding-seoul-han-river/scene-base.png"))
        mask, rain_auto, confidence = detect_window_mask(base)
        self.assertTrue(rain_auto)
        self.assertGreater(confidence, 0.0)
        mask_array = np.asarray(mask, dtype=np.float32) / 255.0
        desk_y = int(1080 * 0.65)
        self.assertLess(mask_array[desk_y:, :].mean(), 0.05)
        self.assertGreater(mask_array[:desk_y, :].mean(), 0.2)

    def test_rain_mask_032_not_confident_without_window(self) -> None:
        base = load_scene(_scene_path("assets/scenes/032-space-programming-sessio-deep-orbit/scene-base.png"))
        _, rain_auto, _ = detect_window_mask(base)
        self.assertFalse(rain_auto)

    def test_resolve_detection_returns_debug_info(self) -> None:
        base = load_scene(_scene_path("assets/scenes/034-space-programming-sessio-lunar-base/scene-base.png"))
        _, detection = resolve_detection(base, (820, 728), auto_rain=False, auto_steam=True)
        self.assertIsNotNone(detection.debug_info)
        assert detection.debug_info is not None
        self.assertEqual(detection.debug_info["steam_x"], detection.steam_x)
        self.assertTrue(detection.steam_auto)


if __name__ == "__main__":
    unittest.main()
