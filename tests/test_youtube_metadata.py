#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from youtube_metadata import (
    MAX_TITLE_CHARS,
    REQUIRED_TAG_COUNT,
    build_youtube_metadata,
    build_youtube_title,
    validate_youtube_metadata,
    write_youtube_metadata,
)


class YoutubeMetadataTests(unittest.TestCase):
    def test_title_format(self) -> None:
        title = build_youtube_title(
            "Linux Hacker Room",
            "Homelab • Fan Hum",
            "4 HOURS",
        )
        self.assertIn("Linux Hacker Room |", title)
        self.assertIn("for Developers", title)
        self.assertLessEqual(len(title), MAX_TITLE_CHARS)

    def test_metadata_has_fifteen_tags(self) -> None:
        metadata = build_youtube_metadata(
            {
                "series": "Deep Work Sessions",
                "mood": "Flow State",
                "durationLabel": "8 HOURS",
                "durationSeconds": 28800,
            }
        )
        validate_youtube_metadata(metadata)
        self.assertEqual(len(metadata["tags"]), REQUIRED_TAG_COUNT)
        self.assertLessEqual(metadata["titleChars"], MAX_TITLE_CHARS)

    def test_write_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            production = Path(temp_dir)
            path = write_youtube_metadata(
                production,
                {
                    "series": "Ambience Session",
                    "mood": "Rainy Evening",
                    "durationLabel": "3 HOURS",
                    "durationSeconds": 10800,
                },
            )
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(path.name, "youtube-metadata.json")
            self.assertEqual(len(data["tags"]), REQUIRED_TAG_COUNT)


if __name__ == "__main__":
    unittest.main()
