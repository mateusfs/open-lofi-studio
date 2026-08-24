#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from assemble_video import (
    SEAMLESS_VIDEO_MAX_SOURCE_SECONDS,
    VIDEO_LOOP_CROSSFADE_SECONDS,
    make_seamless_video_loop,
)
from mix_focus_audio import (
    MUSIC_TRACK_GAP_SECONDS,
    build_music_playlist,
    make_seamless_loop,
    probe_duration_seconds,
    seamless_crossfade_for_duration,
)


def write_tone(path: Path, frequency: float, seconds: float, rate: int = 44100) -> None:
    t = np.linspace(0, seconds, int(rate * seconds), endpoint=False)
    tone = (0.2 * np.sin(2 * np.pi * frequency * t)).astype(np.float32)
    stereo = np.stack([tone, tone], axis=1)
    sf.write(path, stereo, rate)


class MusicPlaylistTests(unittest.TestCase):
    def test_playlist_plays_tracks_in_sequence_without_silence_gap(self) -> None:
        self.assertEqual(MUSIC_TRACK_GAP_SECONDS, 0.0)
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            first = temp / "one.wav"
            second = temp / "two.wav"
            write_tone(first, 220.0, 2.0)
            write_tone(second, 880.0, 2.0)
            output = temp / "playlist.wav"
            build_music_playlist(
                [first, second],
                output,
                fade_seconds=0.4,
                gap_seconds=0.0,
            )
            duration = probe_duration_seconds(output)
            self.assertGreaterEqual(duration, 3.9)
            self.assertLess(duration, 4.2)

            audio, rate = sf.read(output)
            mono = audio.mean(axis=1) if audio.ndim > 1 else audio
            junction = int(2.0 * rate)
            window = mono[junction - rate // 20 : junction + rate // 20]
            self.assertLess(float(np.max(np.abs(window))), 0.08)

    def test_single_track_keeps_near_original_length(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            track = temp / "solo.wav"
            write_tone(track, 330.0, 1.5)
            output = temp / "solo-out.wav"
            build_music_playlist([track], output, fade_seconds=0.3, gap_seconds=0.0)
            duration = probe_duration_seconds(output)
            self.assertAlmostEqual(duration, 1.5, delta=0.15)

    def test_seamless_loop_keeps_energy_at_wrap(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            source = temp / "source.wav"
            output = temp / "loop.wav"
            write_tone(source, 440.0, 4.0)
            make_seamless_loop(source, output, 4, 1.0)
            audio, rate = sf.read(output)
            mono = audio.mean(axis=1) if audio.ndim > 1 else audio
            head = float(np.mean(np.abs(mono[: rate // 10])))
            tail = float(np.mean(np.abs(mono[-rate // 10 :])))
            self.assertGreater(head, 0.02)
            self.assertGreater(tail, 0.02)

    def test_crossfade_scales_with_duration(self) -> None:
        self.assertGreaterEqual(seamless_crossfade_for_duration(300), 8.0)
        self.assertGreaterEqual(seamless_crossfade_for_duration(1800), 16.0)
        self.assertLessEqual(seamless_crossfade_for_duration(1800), 24.0)


class SeamlessVideoLoopTests(unittest.TestCase):
    def test_skips_long_sources(self) -> None:
        source = Path("/tmp/long-loop.mp4")
        output = Path("/tmp/seamless.mp4")
        with mock.patch("assemble_video.get_duration", return_value=SEAMLESS_VIDEO_MAX_SOURCE_SECONDS + 1):
            result = make_seamless_video_loop(source, output)
        self.assertEqual(result, source)

    def test_default_crossfade_is_short(self) -> None:
        self.assertGreaterEqual(VIDEO_LOOP_CROSSFADE_SECONDS, 0.5)
        self.assertLessEqual(VIDEO_LOOP_CROSSFADE_SECONDS, 1.5)


if __name__ == "__main__":
    unittest.main()
