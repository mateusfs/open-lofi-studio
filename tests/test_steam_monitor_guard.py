#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from animate_scene import detect_steam_origin


class SteamMonitorGuardTests(unittest.TestCase):
    def test_rejects_laptop_screen_and_prefers_warm_mug(self) -> None:
        base = np.full((1080, 1920, 3), 38, dtype=np.uint8)
        base[430:760, 980:1380, 0] = 150
        base[430:760, 980:1380, 1] = 190
        base[430:760, 980:1380, 2] = 230
        base[620:760, 760:930, 0] = 206
        base[620:760, 760:930, 1] = 178
        base[620:760, 760:930, 2] = 152
        origin, auto, confidence = detect_steam_origin(base, (760, 720))
        self.assertTrue(auto)
        self.assertGreater(confidence, 0.05)
        self.assertLess(origin[0], 980)
        self.assertGreater(origin[0], 700)

    def test_porto_scene_prefers_mug_over_laptop(self) -> None:
        scene_path = ROOT / "productions/122-ambience-session-porto-ribeira-cafe/source/scene-base.png"
        if not scene_path.exists():
            self.skipTest("cena local ausente")
        from animate_scene import load_scene

        base = load_scene(scene_path)
        origin, auto, confidence = detect_steam_origin(base, (760, 720))
        self.assertTrue(auto)
        self.assertLess(origin[0], 1100)
        self.assertGreater(origin[0], 760)
        self.assertGreater(origin[1], 600)


if __name__ == "__main__":
    unittest.main()
