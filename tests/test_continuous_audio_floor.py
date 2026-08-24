#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from mix_focus_audio import (
    CONTINUOUS_FLOOR_VOLUME,
    DEFAULT_ROOM_TONE,
    assert_no_long_silence,
    ensure_continuous_floor,
    mix_focus_audio,
)


def write_tone(path: Path, frequency: float, seconds: float, rate: int = 44100) -> None:
    t = np.linspace(0, seconds, int(rate * seconds), endpoint=False)
    tone = (0.2 * np.sin(2 * np.pi * frequency * t)).astype(np.float32)
    stereo = np.stack([tone, tone], axis=1)
    sf.write(path, stereo, rate)


class ContinuousFloorTests(unittest.TestCase):
    def test_injects_room_tone_when_mix_would_be_music_only(self) -> None:
        layers = ensure_continuous_floor(
            [],
            has_rain=False,
            has_cafe=False,
            has_white_noise=False,
        )
        self.assertEqual(len(layers), 1)
        self.assertEqual(layers[0].get("role"), "continuousFloor")
        self.assertGreater(float(layers[0]["volume"]), 0.0)
        self.assertLessEqual(float(layers[0]["volume"]), CONTINUOUS_FLOOR_VOLUME + 0.001)
        self.assertTrue(DEFAULT_ROOM_TONE.exists())

    def test_does_not_inject_when_rain_present(self) -> None:
        layers = ensure_continuous_floor(
            [],
            has_rain=True,
            has_cafe=False,
            has_white_noise=False,
        )
        self.assertEqual(layers, [])

    def test_music_only_mix_never_goes_silent(self) -> None:
        if not DEFAULT_ROOM_TONE.exists():
            self.skipTest("room tone asset missing")
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            first = temp / "one.wav"
            second = temp / "two.wav"
            write_tone(first, 220.0, 2.0)
            write_tone(second, 880.0, 2.0)
            output = temp / "mix.wav"
            layers = ensure_continuous_floor(
                [],
                has_rain=False,
                has_cafe=False,
                has_white_noise=False,
            )
            mix_focus_audio(
                output,
                8,
                [first, second],
                None,
                None,
                0.0,
                0.0,
                0.08,
                None,
                0.0,
                layers,
            )
            audio, rate = sf.read(output)
            mono = audio.mean(axis=1) if audio.ndim > 1 else audio
            win = max(1, rate // 4)
            for index in range(0, len(mono) - win, win):
                chunk = mono[index : index + win]
                rms = float(np.sqrt(np.mean(chunk**2)))
                self.assertGreater(rms, 0.001, msg=f"silence at {index / rate:.2f}s")
            assert_no_long_silence(output)

    def test_assert_no_long_silence_raises_on_gap(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            path = temp / "silent.wav"
            rate = 44100
            silence = np.zeros((rate * 2, 2), dtype=np.float32)
            sf.write(path, silence, rate)
            with self.assertRaises(RuntimeError):
                assert_no_long_silence(path)


if __name__ == "__main__":
    unittest.main()
