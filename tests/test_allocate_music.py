#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from audio_registry import (
    MusicRegistryError,
    allocate_playlist_slugs,
    available_track_slugs,
    ensure_audio_json_playlist,
)


class AllocateMusicTests(unittest.TestCase):
    def test_allocate_uses_free_local_tracks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            music = temp / "music"
            music.mkdir()
            for slug in ("alpha-loop", "bravo-loop", "charlie-loop", "delta-loop"):
                (music / f"{slug}.mp3").write_bytes(b"ID3fake")
            registry = {
                "rules": {"playlistSizeMin": 3, "playlistSizeMax": 4},
                "productions": {
                    "locked-prod": {"tracks": ["alpha-loop"], "files": ["assets/audio/music/alpha-loop.mp3"]}
                },
                "blockedSlugs": [],
            }
            registry_path = temp / "music-registry.json"
            registry_path.write_text(json.dumps(registry) + "\n", encoding="utf-8")

            with mock.patch("audio_registry.ROOT", temp), mock.patch(
                "audio_registry.DEFAULT_REGISTRY", registry_path
            ), mock.patch("audio_registry.locked_production_ids", return_value={"locked-prod"}):
                free = available_track_slugs(
                    exclude_production_id="new-prod",
                    registry_path=registry_path,
                    music_dir=music,
                )
                self.assertIn("bravo-loop", free)
                chosen = allocate_playlist_slugs(
                    "new-prod",
                    count=3,
                    preferred=["bravo-loop", "used-elsewhere"],
                    registry_path=registry_path,
                    music_dir=music,
                )
                self.assertEqual(len(chosen), 3)
                self.assertEqual(chosen[0], "bravo-loop")
                self.assertNotIn("alpha-loop", chosen)

    def test_ensure_audio_json_rewrites_short_playlist(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            music = temp / "assets" / "audio" / "music"
            music.mkdir(parents=True)
            for slug in ("one-track", "two-track", "three-track", "four-track"):
                (music / f"{slug}.mp3").write_bytes(b"ID3fake")
            production = temp / "productions" / "demo"
            production.mkdir(parents=True)
            audio_path = production / "audio.json"
            audio_path.write_text(
                json.dumps(
                    {
                        "productionId": "demo",
                        "tracks": ["assets/audio/music/one-track.mp3"],
                        "musicVolume": 1.0,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            registry = {
                "rules": {"playlistSizeMin": 3, "playlistSizeMax": 4},
                "productions": {},
                "blockedSlugs": [],
            }
            registry_path = temp / "assets" / "audio" / "music-registry.json"
            registry_path.parent.mkdir(parents=True, exist_ok=True)
            registry_path.write_text(json.dumps(registry) + "\n", encoding="utf-8")

            with mock.patch("audio_registry.ROOT", temp), mock.patch(
                "audio_registry.DEFAULT_REGISTRY", registry_path
            ), mock.patch("audio_registry.locked_production_ids", return_value=set()), mock.patch(
                "audio_registry.prune_unlocked_registry_entries", return_value=[]
            ):
                files = ensure_audio_json_playlist(
                    production,
                    "demo",
                    preferred_slugs=["one-track"],
                    registry_path=registry_path,
                )
                payload = json.loads(audio_path.read_text(encoding="utf-8"))
                self.assertEqual(len(files), 4)
                self.assertEqual(len(payload["tracks"]), 4)
                self.assertAlmostEqual(float(payload["musicVolume"]), 0.065)
                validate_ok = True
                try:
                    from audio_registry import validate_playlist

                    validate_playlist("demo", files, registry_path)
                except MusicRegistryError:
                    validate_ok = False
                self.assertTrue(validate_ok)

    def test_allocate_replenishes_when_pool_is_short(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            music = temp / "music"
            music.mkdir()
            for slug in ("only-one", "only-two"):
                (music / f"{slug}.mp3").write_bytes(b"ID3fake")
            registry_path = temp / "music-registry.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "rules": {"playlistSizeMin": 3, "playlistSizeMax": 4},
                        "productions": {},
                        "blockedSlugs": [],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            def fake_ensure(needed: int, exclude_production_id: str | None = None) -> int:
                for slug in ("auto-three", "auto-four"):
                    (music / f"{slug}.mp3").write_bytes(b"ID3fake")
                return 4

            with mock.patch("audio_registry.ROOT", temp), mock.patch(
                "audio_registry.DEFAULT_REGISTRY", registry_path
            ), mock.patch(
                "audio_registry.locked_production_ids", return_value=set()
            ), mock.patch(
                "replenish_music.ensure_free_track_count", side_effect=fake_ensure
            ) as ensure_mock:
                chosen = allocate_playlist_slugs(
                    "short-pool-prod",
                    count=4,
                    registry_path=registry_path,
                    music_dir=music,
                )
                ensure_mock.assert_called_once()
                self.assertEqual(len(chosen), 4)
                self.assertTrue({"auto-three", "auto-four"} <= set(chosen))


if __name__ == "__main__":
    unittest.main()
