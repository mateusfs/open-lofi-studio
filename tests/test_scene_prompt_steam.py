#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest

ROOT = __import__("pathlib").Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from scene_prompt import sanitize_scene_prompt


class ScenePromptSteamTests(unittest.TestCase):
    def test_strips_steam_and_appends_ban(self) -> None:
        prompt = sanitize_scene_prompt(
            "cozy desk with steaming coffee mug and rising steam near laptop"
        )
        lower = prompt.lower()
        self.assertNotIn("steaming", lower)
        self.assertIn("no steam", lower)
        self.assertIn("no smoke", lower)
        self.assertIn("no vapor", lower)


if __name__ == "__main__":
    unittest.main()
