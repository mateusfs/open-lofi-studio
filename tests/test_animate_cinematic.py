from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from animate_cinematic import OverlayLayer, build_filter_complex, resolve_overlay


class AnimateCinematicTests(unittest.TestCase):
    def test_resolve_overlay_defaults_to_assets_dir(self) -> None:
        layer = resolve_overlay({"file": "dust-floating-black.mp4", "opacity": 0.2})
        self.assertTrue(layer.path.exists())
        self.assertEqual(layer.blend, "screen")
        self.assertAlmostEqual(layer.opacity, 0.2)

    def test_build_filter_complex_includes_ken_burns_and_blend(self) -> None:
        overlays = [
            OverlayLayer(
                path=ROOT / "assets/images/overlays/dust-floating-black.mp4",
                opacity=0.2,
                blend="screen",
            )
        ]
        graph = build_filter_complex(
            overlays=overlays,
            zoom_amount=0.03,
            pan_x=20.0,
            pan_y=12.0,
            breathe=0.008,
            total_frames=576,
        )
        self.assertIn("zoompan=", graph)
        self.assertIn("blend=all_mode=screen", graph)
        self.assertIn("[outv]", graph)

    def test_cinematic_loop_has_motion(self) -> None:
        scene = ROOT / "productions/070-dark-mode-workspace-dual-monitor/source/scene-base.png"
        if not scene.exists():
            self.skipTest("scene-base.png do #070 ausente")

        overlays = json.dumps(
            [
                {"file": "dust-floating-black.mp4", "opacity": 0.22, "blend": "screen"},
                {"file": "light-leaks.mp4", "opacity": 0.08, "blend": "screen"},
            ]
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            output = temp_path / "cinematic-loop.mp4"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/animate_cinematic.py"),
                    "--scene",
                    str(scene),
                    "--output",
                    str(output),
                    "--overlays",
                    overlays,
                    "--seconds",
                    "4",
                    "--zoom",
                    "0.04",
                    "--breathe",
                    "0.01",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output.exists())
            self.assertGreater(output.stat().st_size, 50_000)

            frame_a = temp_path / "a.png"
            frame_b = temp_path / "b.png"
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-ss",
                    "0.1",
                    "-i",
                    str(output),
                    "-frames:v",
                    "1",
                    str(frame_a),
                ],
                check=True,
                capture_output=True,
            )
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-ss",
                    "2.0",
                    "-i",
                    str(output),
                    "-frames:v",
                    "1",
                    str(frame_b),
                ],
                check=True,
                capture_output=True,
            )

            a = np.asarray(Image.open(frame_a).convert("RGB"), dtype=np.int16)
            b = np.asarray(Image.open(frame_b).convert("RGB"), dtype=np.int16)
            mean_delta = float(np.mean(np.abs(a - b)))
            self.assertGreater(mean_delta, 0.8)


if __name__ == "__main__":
    unittest.main()
