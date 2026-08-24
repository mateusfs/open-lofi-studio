#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from ambient_presets import (
    default_ambient_loop_seconds,
    resolve_ambient_effects,
)


class AmbientPresetsTests(unittest.TestCase):
    def test_base_effects_always_present(self) -> None:
        effects = resolve_ambient_effects("Deep Work Sessions", "Deep Focus", {})
        self.assertIn("monitor_glow", effects)
        self.assertIn("desk_lamp_breathe", effects)
        self.assertIn("dust_motes", effects)

    def test_rainy_mood_adds_rain_and_city_haze(self) -> None:
        effects = resolve_ambient_effects(
            "Rainy Night Coding",
            "Rainy Desk • Deep Focus",
            {},
        )
        self.assertIn("rain", effects)
        self.assertIn("city_haze", effects)

    def test_homelab_mood_adds_keyboard_underglow(self) -> None:
        effects = resolve_ambient_effects(
            "Linux Hacker Room",
            "Homelab Server • Deep Focus",
            {},
        )
        self.assertIn("keyboard_underglow", effects)
        self.assertIn("rgb_breathe", effects)

    def test_explicit_effects_override_preset(self) -> None:
        effects = resolve_ambient_effects(
            "Deep Work Sessions",
            "Rainy Desk",
            {"effects": ["screen_bloom"]},
        )
        self.assertEqual(effects, ["screen_bloom"])

    def test_no_rain_removes_rain(self) -> None:
        effects = resolve_ambient_effects(
            "Rainy Night Coding",
            "Rainy Desk",
            {"noRain": True},
        )
        self.assertNotIn("rain", effects)
        self.assertIn("city_haze", effects)

    def test_no_steam_removes_steam(self) -> None:
        effects = resolve_ambient_effects(
            "Ambience Session",
            "Coffee Warm • Cozy",
            {},
        )
        self.assertIn("steam", effects)
        filtered = resolve_ambient_effects(
            "Ambience Session",
            "Coffee Warm • Cozy",
            {"noSteam": True},
        )
        self.assertNotIn("steam", filtered)

    def test_never_includes_slow_zoom(self) -> None:
        effects = resolve_ambient_effects(
            "Deep Work Sessions",
            "Deep Focus",
            {"effects": ["slow_zoom", "monitor_glow"]},
        )
        self.assertNotIn("slow_zoom", effects)
        self.assertEqual(effects, ["monitor_glow"])

    def test_default_loop_seconds_is_24(self) -> None:
        self.assertEqual(default_ambient_loop_seconds({}), 24)

    def test_explicit_loop_seconds_preserved(self) -> None:
        self.assertEqual(default_ambient_loop_seconds({"loopSeconds": 30}), 30)


if __name__ == "__main__":
    unittest.main()
