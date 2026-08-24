from __future__ import annotations

import unittest

import numpy as np

from animate_scene import (
    DEFAULT_STEAM_COLOR,
    STEAM_SCALE_MIN,
    parse_steam_color,
    render_steam,
    steam_scale_at_time,
    steam_scale_for_progress,
)
from assemble_video import steam_decay_segment_count


class SteamDecayTests(unittest.TestCase):
    def test_scale_at_start_is_full(self) -> None:
        self.assertAlmostEqual(steam_scale_for_progress(0.0), 1.0)

    def test_scale_at_end_is_minimum(self) -> None:
        self.assertAlmostEqual(steam_scale_for_progress(1.0), STEAM_SCALE_MIN)

    def test_scale_decreases_monotonically(self) -> None:
        samples = [steam_scale_for_progress(p / 10) for p in range(11)]
        for earlier, later in zip(samples, samples[1:]):
            self.assertGreaterEqual(earlier, later)

    def test_scale_clamps_out_of_range(self) -> None:
        self.assertAlmostEqual(steam_scale_for_progress(-1.0), 1.0)
        self.assertAlmostEqual(steam_scale_for_progress(1.5), STEAM_SCALE_MIN)

    def test_scale_at_time_matches_progress(self) -> None:
        duration = 120.0
        self.assertAlmostEqual(steam_scale_at_time(0.0, duration), 1.0)
        self.assertAlmostEqual(steam_scale_at_time(duration, duration), STEAM_SCALE_MIN)
        self.assertAlmostEqual(
            steam_scale_at_time(60.0, duration),
            steam_scale_for_progress(0.5),
        )

    def test_scale_at_time_decreases_over_timeline(self) -> None:
        duration = 30.0
        samples = [steam_scale_at_time(second, duration) for second in range(0, 31, 3)]
        for earlier, later in zip(samples, samples[1:]):
            self.assertGreaterEqual(earlier, later)

    def test_preview_uses_single_segment(self) -> None:
        self.assertEqual(steam_decay_segment_count(30), 1)

    def test_short_hour_uses_minimum_segment_count(self) -> None:
        self.assertEqual(steam_decay_segment_count(3600), 8)

    def test_long_video_caps_segment_count(self) -> None:
        self.assertEqual(steam_decay_segment_count(36000), 10)

    def test_render_steam_anchor_stable_across_scales(self) -> None:
        origin = (292, 778)
        bottoms: list[int] = []
        for scale in (1.0, 0.55, 0.2):
            frame = render_steam(origin, scale, 0)
            alpha = np.array(frame)[:, :, 3]
            visible = np.where(alpha > 4)
            if visible[0].size:
                bottoms.append(int(visible[0].max()))
        self.assertGreaterEqual(len(bottoms), 2)
        self.assertLessEqual(max(bottoms) - min(bottoms), 24)

    def test_parse_steam_color_from_list_and_csv(self) -> None:
        self.assertEqual(parse_steam_color(None), DEFAULT_STEAM_COLOR)
        self.assertEqual(parse_steam_color([200, 148, 110]), (200, 148, 110))
        self.assertEqual(parse_steam_color("200,148,110"), (200, 148, 110))

    def test_render_steam_uses_custom_color(self) -> None:
        warm = render_steam((960, 800), 1.0, 0, color=(200, 148, 110))
        cool = render_steam((960, 800), 1.0, 0, color=DEFAULT_STEAM_COLOR)
        warm_arr = np.array(warm)
        cool_arr = np.array(cool)
        visible = warm_arr[:, :, 3] > 40
        self.assertTrue(visible.any())
        warm_mean = warm_arr[:, :, :3][visible].mean(axis=0)
        cool_mean = cool_arr[:, :, :3][cool_arr[:, :, 3] > 40].mean(axis=0)
        self.assertGreater(warm_mean[0] - warm_mean[2], 40)
        self.assertGreater(cool_mean[2], warm_mean[2])


if __name__ == "__main__":
    unittest.main()
