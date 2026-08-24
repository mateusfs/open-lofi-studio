#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from animate_mode import apply_calibration_to_meta, resolve_animate_mode


class AnimateModeTests(unittest.TestCase):
    def test_default_is_locked(self) -> None:
        self.assertEqual(resolve_animate_mode({}), "locked")
        self.assertEqual(resolve_animate_mode({"mode": ""}), "locked")
        self.assertEqual(resolve_animate_mode({"mode": "auto"}), "locked")

    def test_explicit_procedural_and_cinematic_kept(self) -> None:
        self.assertEqual(resolve_animate_mode({"mode": "procedural"}), "procedural")
        self.assertEqual(resolve_animate_mode({"mode": "cinematic"}), "cinematic")

    def test_layers_force_hybrid(self) -> None:
        self.assertEqual(
            resolve_animate_mode({"mode": "locked", "layers": [{"id": "dust"}]}),
            "hybrid",
        )

    def test_calibration_disables_weak_steam(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            production = Path(temp_dir)
            meta_path = production / "meta.json"
            meta_path.write_text(
                json.dumps({"animate": {"autoSteam": True}}),
                encoding="utf-8",
            )
            apply_calibration_to_meta(
                production,
                {
                    "steam": {
                        "confidence": 0.01,
                        "used_fallback": True,
                        "detected_x": 10,
                        "detected_y": 20,
                    }
                },
            )
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            self.assertFalse(meta["animate"]["autoSteam"])
            self.assertTrue(meta["animate"]["noSteam"])


if __name__ == "__main__":
    unittest.main()
