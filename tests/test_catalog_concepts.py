#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from ambient_presets import resolve_ambient_effects
from catalog_concepts import CONCEPTS, scene_prompt_for
from queue_catalog import pick_next_catalog_entry


class CatalogConceptsTests(unittest.TestCase):
    def test_one_hundred_unique_numbers_from_122(self) -> None:
        self.assertEqual(len(CONCEPTS), 100)
        numbers = [concept.number for concept in CONCEPTS]
        self.assertEqual(len(set(numbers)), 100)
        parsed = [int(number) for number in numbers]
        self.assertEqual(min(parsed), 122)
        self.assertEqual(max(parsed), 221)
        self.assertEqual(parsed, list(range(122, 222)))

    def test_unique_titles_and_visuals(self) -> None:
        titles = [concept.title for concept in CONCEPTS]
        visuals = [concept.visual for concept in CONCEPTS]
        self.assertEqual(len(set(titles)), 100)
        self.assertEqual(len(set(visuals)), 100)

    def test_scene_prompts_forbid_baked_steam(self) -> None:
        for concept in CONCEPTS:
            prompt = scene_prompt_for(concept).lower()
            self.assertIn("no steam", prompt)
            self.assertNotIn("steaming", prompt)

    def test_moods_cover_ambient_preset_families(self) -> None:
        families = {
            "rain": False,
            "snow": False,
            "sunrise": False,
            "homelab": False,
            "steam": False,
            "water": False,
            "space": False,
        }
        for concept in CONCEPTS:
            effects = resolve_ambient_effects(concept.series, concept.mood, {})
            if "rain" in effects:
                families["rain"] = True
            if "snow" in effects or "fireplace_flicker" in effects:
                families["snow"] = True
            if "sunrise_glow" in effects:
                families["sunrise"] = True
            if "keyboard_underglow" in effects:
                families["homelab"] = True
            if "steam" in effects:
                families["steam"] = True
            if "water_shimmer" in effects:
                families["water"] = True
            if "screen_bloom" in effects:
                families["space"] = True
        self.assertTrue(all(families.values()), families)

    def test_pick_next_skips_completed_through_121(self) -> None:
        videos = [
            {
                "number": "121",
                "productionId": "121-lounge-coding-sessions-blues-rainy-window",
                "status": "produzido",
            }
        ]
        catalog = [
            {
                "number": "122",
                "productionId": "122-ambience-session-porto-ribeira-cafe",
                "titleEn": "122",
                "animate": {"mode": "ambient", "loopSeconds": 24},
            }
        ]
        import queue_catalog

        original = queue_catalog.catalog_entries
        queue_catalog.catalog_entries = lambda: catalog
        try:

            def is_complete(video: dict) -> bool:
                return video["status"] == "produzido"

            next_entry = pick_next_catalog_entry(videos, is_complete)
        finally:
            queue_catalog.catalog_entries = original
        self.assertIsNotNone(next_entry)
        assert next_entry is not None
        self.assertEqual(next_entry["number"], "122")
        self.assertEqual(next_entry["animate"]["mode"], "ambient")
        self.assertEqual(next_entry["animate"]["loopSeconds"], 24)


if __name__ == "__main__":
    unittest.main()
