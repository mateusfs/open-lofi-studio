from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from animate_scene import render_steam
from scene_effects import _apply_window_mask, render_fireplace_flicker


class FireplaceAndSteamPathTests(unittest.TestCase):
    def test_steam_overlay_is_subtle(self) -> None:
        steam = render_steam((235, 838), 0.5, 40)
        alpha = np.asarray(steam.split()[-1])
        self.assertGreater(int(alpha.max()), 8)
        self.assertLessEqual(int(alpha.max()), 48)
        self.assertGreater(int((alpha > 4).sum()), 80)

    def test_fireplace_flicker_changes_warm_region(self) -> None:
        base = np.full((1080, 1920, 3), 18, dtype=np.uint8)
        base[520:860, 1500:1820] = [210, 110, 30]
        a = render_fireplace_flicker(base, 0, 480)
        b = render_fireplace_flicker(base, 12, 480)
        self.assertGreater(
            float(
                np.mean(
                    np.abs(
                        a[520:860, 1500:1820].astype(np.int16)
                        - b[520:860, 1500:1820].astype(np.int16)
                    )
                )
            ),
            4.0,
        )

    def test_rain_requires_detected_window_when_auto(self) -> None:
        from animate_scene import should_enable_rain, should_enable_steam

        self.assertFalse(should_enable_rain(True, True, False))
        self.assertTrue(should_enable_rain(True, True, True))
        self.assertTrue(should_enable_rain(True, False, False))
        self.assertFalse(should_enable_rain(False, True, True))
        self.assertFalse(should_enable_steam(True, True, False))
        self.assertTrue(should_enable_steam(True, False, False))
        self.assertTrue(should_enable_steam(True, True, True))

    def test_window_mask_keeps_overlay_alpha(self) -> None:
        overlay = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
        overlay.putpixel((100, 100), (255, 255, 255, 180))
        overlay.putpixel((900, 500), (255, 255, 255, 180))
        mask = Image.new("L", (1920, 1080), 0)
        for y in range(80, 200):
            for x in range(50, 200):
                mask.putpixel((x, y), 255)
        masked = _apply_window_mask(overlay, mask)
        self.assertGreater(masked.getpixel((100, 100))[3], 100)
        self.assertEqual(masked.getpixel((900, 500))[3], 0)


if __name__ == "__main__":
    unittest.main()
