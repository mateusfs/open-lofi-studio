#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from effect_mask import ensure_effect_mask, generate_effect_mask
from queue_catalog import max_completed_thresholds, pick_next_catalog_entry


class PipelineAutonomyTests(unittest.TestCase):
    def test_generate_effect_mask(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            scene = temp / "scene-base.png"
            Image.fromarray(np.full((1080, 1920, 3), 120, dtype=np.uint8), mode="RGB").save(scene)
            output = temp / "effect-mask.png"
            generate_effect_mask(scene, output)
            self.assertTrue(output.exists())
            self.assertGreater(output.stat().st_size, 1_000)
            mask = Image.open(output)
            self.assertEqual(mask.size, (1920, 1080))
            self.assertEqual(mask.mode, "L")

    def test_ensure_effect_mask_reuses_existing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            scene = temp / "scene-base.png"
            Image.fromarray(np.full((1080, 1920, 3), 80, dtype=np.uint8), mode="RGB").save(scene)
            output = temp / "effect-mask.png"
            first = ensure_effect_mask(scene, output)
            self.assertIsNotNone(first)
            mtime = output.stat().st_mtime_ns
            second = ensure_effect_mask(scene, output)
            self.assertEqual(second, output)
            self.assertEqual(output.stat().st_mtime_ns, mtime)

    def test_pick_next_keeps_regular_and_seasonal_separate(self) -> None:
        videos = [
            {
                "number": "S04",
                "productionId": "s04-seasonal-summer-remote-work-vibes",
                "status": "produzido",
            },
            {
                "number": "081",
                "productionId": "081-silent-library-for-deep--university-night",
                "status": "produzido",
            },
            {
                "number": "082",
                "productionId": "082-silent-library-for-deep--rooftop-reading-room",
                "status": "preview",
            },
        ]
        catalog = [
            {
                "number": "082",
                "productionId": "082-silent-library-for-deep--rooftop-reading-room",
                "titleEn": "082",
            },
            {
                "number": "090",
                "productionId": "090-startup-office-at-midnig-empty-open-space",
                "titleEn": "090",
            },
            {
                "number": "S05",
                "productionId": "s05-seasonal-halloween-late-night-code",
                "titleEn": "S05",
            },
        ]

        import queue_catalog

        original = queue_catalog.catalog_entries
        queue_catalog.catalog_entries = lambda: catalog
        try:

            def is_complete(video: dict) -> bool:
                return video["productionId"] in {
                    "s04-seasonal-summer-remote-work-vibes",
                    "081-silent-library-for-deep--university-night",
                }

            regular, seasonal = max_completed_thresholds(videos, is_complete)
            self.assertEqual(regular, 81)
            self.assertEqual(seasonal, 10004)
            next_entry = pick_next_catalog_entry(videos, is_complete)
            self.assertIsNotNone(next_entry)
            assert next_entry is not None
            self.assertEqual(next_entry["number"], "090")
        finally:
            queue_catalog.catalog_entries = original


if __name__ == "__main__":
    unittest.main()
