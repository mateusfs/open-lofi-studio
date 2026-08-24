from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from generate_thumbnail import (
    MAX_BADGE_LUMINANCE,
    SHORT_HEIGHT,
    SHORT_WIDTH,
    WIDTH,
    HEIGHT,
    badge_fill_color,
    color_luminance,
    focal_crop_bias,
    generate_thumbnail,
    load_palette,
    palette_color,
    resolve_ambience_hook,
    resolve_short_caption,
    series_accent,
)


class ThumbnailRulesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.palette = load_palette(ROOT / "brand")

    def test_badge_never_uses_light_cream_for_cabin_series(self) -> None:
        fill = badge_fill_color("Cabin Programmer", self.palette)
        accent, _ = series_accent("Cabin Programmer", self.palette)
        self.assertGreater(color_luminance(accent), MAX_BADGE_LUMINANCE)
        self.assertEqual(fill, palette_color(self.palette, "accentRed"))

    def test_badge_never_uses_light_green_for_space_series(self) -> None:
        fill = badge_fill_color("Space Programming Session", self.palette)
        accent, _ = series_accent("Space Programming Session", self.palette)
        self.assertGreater(color_luminance(accent), MAX_BADGE_LUMINANCE)
        self.assertEqual(fill, palette_color(self.palette, "accentRed"))

    def test_badge_uses_dark_accent_for_cyberpunk(self) -> None:
        fill = badge_fill_color("Cyberpunk Developer Room", self.palette)
        accent, _ = series_accent("Cyberpunk Developer Room", self.palette)
        self.assertEqual(fill, accent)

    def test_badge_fallback_is_accent_red(self) -> None:
        fill = badge_fill_color("Ambience Session", self.palette)
        self.assertEqual(fill, palette_color(self.palette, "accentRed"))

    def test_resolve_ambience_hook_rain(self) -> None:
        hook = resolve_ambience_hook("Rainy Night Coding", "Seoul Han River • Rain Focus")
        self.assertEqual(hook, "RAIN SOUNDS")

    def test_resolve_ambience_hook_white_noise(self) -> None:
        hook = resolve_ambience_hook("Deep Work Sessions", "White Noise • Pure Focus")
        self.assertEqual(hook, "WHITE NOISE")

    def test_focal_crop_bias_favors_window_for_rain(self) -> None:
        rain_bias = focal_crop_bias("Rainy Night Coding", "Seoul Han River • Rain Focus")
        default_bias = focal_crop_bias("Space Programming Session", "Deep Orbit")
        self.assertLess(rain_bias, default_bias)

    def test_short_caption_prefers_mood_focus_phrase(self) -> None:
        self.assertEqual(
            resolve_short_caption("Ambience Session", "Porto Ribeira • Warm Focus"),
            "WARM FOCUS",
        )
        self.assertEqual(
            resolve_short_caption("Deep Work Sessions", "Pomodoro • 25min Cycles"),
            "FLOW STATE",
        )
        self.assertEqual(
            resolve_short_caption("Rainy Night Coding", "Tokyo Apartment • Night Focus"),
            "RAIN SOUNDS",
        )

    def test_short_caption_never_contains_em_dash(self) -> None:
        captions = [
            resolve_short_caption("Ambience Session", "Porto Ribeira — Warm Focus"),
            resolve_short_caption("Deep Work Sessions", "Night — Deep Focus", "FLOW — STATE"),
            resolve_short_caption("Cabin Programmer", "Fireplace Snow — Cozy"),
        ]
        for caption in captions:
            self.assertNotIn("—", caption)
            self.assertNotIn("–", caption)
            self.assertNotIn("•", caption)
            self.assertNotIn("-", caption)

    def test_short_format_is_9x16_without_duration_badge(self) -> None:
        import tempfile

        from PIL import Image

        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            scene = temp / "scene.png"
            Image.new("RGB", (1920, 1080), (40, 50, 70)).save(scene)
            output = temp / "thumbnail-b.png"
            generate_thumbnail(
                scene,
                output,
                "Deep Work Sessions",
                "Flow State • Total Immersion",
                "8 HOURS",
                self.palette,
                thumb_format="short",
            )
            with Image.open(output) as image:
                self.assertEqual(image.size, (SHORT_WIDTH, SHORT_HEIGHT))
                pixels = image.load()
                assert pixels is not None
                corner = pixels[SHORT_WIDTH - 40, 40]
                self.assertLess(sum(corner[:3]) / 3, 90)

    def test_landscape_format_is_16x9(self) -> None:
        import tempfile

        from PIL import Image

        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            scene = temp / "scene.png"
            Image.new("RGB", (1920, 1080), (40, 50, 70)).save(scene)
            output = temp / "thumbnail.png"
            generate_thumbnail(
                scene,
                output,
                "Ambience Session",
                "Porto Ribeira • Warm Focus",
                "8 HOURS",
                self.palette,
                thumb_format="landscape",
            )
            with Image.open(output) as image:
                self.assertEqual(image.size, (WIDTH, HEIGHT))


if __name__ == "__main__":
    unittest.main()
