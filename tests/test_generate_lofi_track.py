#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from generate_lofi_track import (
    fallback_recipe,
    generate_unique_tracks,
    midi_to_hz,
    normalize_recipe,
    synthesize_recipe,
    unique_slug,
)
from replenish_music import ensure_free_track_count


class GenerateLofiTrackTests(unittest.TestCase):
    def test_midi_to_hz_a4(self) -> None:
        self.assertAlmostEqual(midi_to_hz(69), 440.0, places=3)

    def test_fallback_recipes_are_unique(self) -> None:
        first = fallback_recipe(1, set())
        second = fallback_recipe(2, set())
        self.assertNotEqual(first["title"], second["title"])
        self.assertNotEqual(first["bpm"], second["bpm"])
        self.assertNotEqual(first["midiChords"], second["midiChords"])

    def test_normalize_recipe_fills_invalid_chords(self) -> None:
        recipe = normalize_recipe({"title": "Quiet Desk!!", "bpm": 200, "midiChords": []}, 4)
        self.assertEqual(recipe["title"], "quiet-desk")
        self.assertLessEqual(recipe["bpm"], 92)
        self.assertGreaterEqual(len(recipe["midiChords"]), 3)

    def test_synthesize_short_buffer(self) -> None:
        recipe = fallback_recipe(8, set())
        left, right = synthesize_recipe(recipe, 0.3)
        self.assertEqual(left.size, right.size)
        self.assertGreater(left.size, 1000)
        peak = max(float(np.max(np.abs(left))), float(np.max(np.abs(right))))
        self.assertLessEqual(peak, 0.93)
        self.assertGreater(peak, 0.1)

    def test_unique_slug_avoids_collision(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            music = Path(temp_dir)
            (music / "csc-quiet-window-0003.mp3").write_bytes(b"ID3")
            slug = unique_slug("quiet-window", 3, music)
            self.assertEqual(slug, "csc-quiet-window-0003-2")

    def test_generate_unique_tracks_writes_mp3(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            music = temp / "music"
            music.mkdir()
            state = temp / "state.json"
            state.write_text(
                json.dumps({"importedPackIds": [], "generatedTrackSerial": 0}) + "\n",
                encoding="utf-8",
            )

            def fake_encode(wav_path: Path, mp3_path: Path) -> None:
                mp3_path.write_bytes(b"ID3fake" * 2000)

            with mock.patch("generate_lofi_track.STATE_PATH", state), mock.patch(
                "generate_lofi_track.recipe_from_openai", return_value=None
            ), mock.patch("generate_lofi_track.encode_wav_to_mp3", side_effect=fake_encode), mock.patch(
                "generate_lofi_track.LICENSES_PATH", temp / "LICENSES.md"
            ):
                slugs = generate_unique_tracks(2, music_dir=music, duration_seconds=0.2)
            self.assertEqual(len(slugs), 2)
            self.assertEqual(len(set(slugs)), 2)
            for slug in slugs:
                self.assertTrue((music / f"{slug}.mp3").exists())


class ReplenishMusicFallbackTests(unittest.TestCase):
    def test_ensure_generates_when_packs_are_exhausted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            music = temp / "music"
            music.mkdir()
            (music / "only-one.mp3").write_bytes(b"ID3fake")
            registry_path = temp / "music-registry.json"
            registry_path.write_text(
                json.dumps({"productions": {}, "blockedSlugs": []}) + "\n",
                encoding="utf-8",
            )

            def fake_generate(missing: int, music_dir: Path) -> list[str]:
                created: list[str] = []
                for index in range(missing):
                    slug = f"generated-focus-{index}"
                    (music_dir / f"{slug}.mp3").write_bytes(b"ID3fake")
                    created.append(slug)
                return created

            with mock.patch("replenish_music.import_next_unused_pack", return_value=[]), mock.patch(
                "replenish_music.generate_original_tracks", side_effect=fake_generate
            ), mock.patch("audio_registry.DEFAULT_REGISTRY", registry_path), mock.patch(
                "replenish_music.load_state",
                return_value={"importedPackIds": ["openlofi"], "generatedTrackSerial": 0},
            ):
                total = ensure_free_track_count(4, music_dir=music)
            self.assertGreaterEqual(total, 4)


if __name__ == "__main__":
    unittest.main()
