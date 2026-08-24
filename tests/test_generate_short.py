#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from generate_short import build_mpt_script, resolve_production_dir


class GenerateShortTests(unittest.TestCase):
    def test_resolve_production_by_number(self) -> None:
        path = resolve_production_dir("110")
        self.assertTrue(path.name.startswith("110-"))
        self.assertTrue((path / "meta.json").exists())

    def test_mpt_script_mentions_channel(self) -> None:
        script = build_mpt_script(
            {
                "series": "Deep Work Sessions",
                "mood": "Pomodoro • 25min Cycles",
                "durationLabel": "2 HOURS",
            }
        )
        self.assertIn("Deep Work Sessions", script)
        self.assertIn("channel", script.lower())


if __name__ == "__main__":
    unittest.main()
