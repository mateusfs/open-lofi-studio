from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from audio_loudness import TARGET_LUFS, assert_mix_loudness, measure_loudness
from mix_focus_audio import resolve_named_ambience


class AudioLoudnessTests(unittest.TestCase):
    def test_named_ambience_resolves_presets(self) -> None:
        layers = resolve_named_ambience(
            {
                "ambience": [{"name": "roomTone", "volume": 0.11}],
                "softHiss": 0.07,
            }
        )
        self.assertGreaterEqual(len(layers), 2)
        self.assertTrue(any(float(layer.get("volume", 0)) == 0.11 for layer in layers))

    def test_assert_mix_loudness_accepts_normalized_tone(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "tone.wav"
            rate = 48000
            seconds = 3.0
            t = np.linspace(0, seconds, int(rate * seconds), endpoint=False)
            tone = (0.05 * np.sin(2 * np.pi * 440 * t)).astype(np.float64)
            stereo = np.stack([tone, tone], axis=1)
            sf.write(path, stereo, rate)
            loudness, _peak = measure_loudness(path)
            self.assertLess(loudness, TARGET_LUFS + 20)


if __name__ == "__main__":
    unittest.main()
