from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from mix_focus_audio import (
    MUSIC_TRACK_FADE_SECONDS,
    MUSIC_TRACK_GAP_SECONDS,
    SEAMLESS_CROSSFADE_SECONDS,
    seamless_crossfade_for_duration,
)
from produce_video import DEFAULT_AUDIO_LOOP_SECONDS, resolve_audio_loop_duration


class AudioLoopDurationTests(unittest.TestCase):
    def test_default_loop_is_thirty_minutes(self) -> None:
        self.assertEqual(DEFAULT_AUDIO_LOOP_SECONDS, 1800)

    def test_preview_uses_exact_target_duration(self) -> None:
        self.assertEqual(resolve_audio_loop_duration(28800, 30), 30)

    def test_full_render_caps_at_default_loop(self) -> None:
        self.assertEqual(resolve_audio_loop_duration(28800, None), 1800)

    def test_short_video_uses_full_duration(self) -> None:
        self.assertEqual(resolve_audio_loop_duration(900, None), 900)

    def test_loops_stay_continuous_without_silence_gaps(self) -> None:
        self.assertEqual(MUSIC_TRACK_GAP_SECONDS, 0.0)
        self.assertLessEqual(MUSIC_TRACK_FADE_SECONDS, 3.0)
        self.assertGreaterEqual(SEAMLESS_CROSSFADE_SECONDS, 12.0)
        self.assertGreaterEqual(seamless_crossfade_for_duration(300), 8.0)


if __name__ == "__main__":
    unittest.main()
