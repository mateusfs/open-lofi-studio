from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from hybrid_effects import (
    apply_blend,
    compose_hybrid_loop,
    parse_layer,
    refine_mask,
    render_dust_particles,
)


class HybridEffectsTests(unittest.TestCase):
    def test_refine_mask_softens_edges(self) -> None:
        mask = np.zeros((1080, 1920), dtype=np.float32)
        mask[100:400, 100:500] = 1.0
        refined = refine_mask(mask, erode=1, blur=5)
        self.assertGreater(float(refined[250, 300]), 0.8)
        self.assertLess(float(refined[100, 100]), 1.0)

    def test_dust_stays_inside_mask(self) -> None:
        mask = np.zeros((1080, 1920), dtype=np.float32)
        mask[80:500, 60:700] = 1.0
        overlay = render_dust_particles(12, 300, 7, 0.6, mask)
        outside = overlay.copy()
        outside[80:500, 60:700] = 0
        self.assertEqual(int(outside.max()), 0)
        self.assertGreater(int(overlay[80:500, 60:700].max()), 0)

    def test_screen_blend_respects_amount(self) -> None:
        base = np.full((4, 4, 3), 40, dtype=np.uint8)
        overlay = np.full((4, 4, 3), 200, dtype=np.uint8)
        amount = np.zeros((4, 4), dtype=np.float32)
        amount[:, 2:] = 0.5
        out = apply_blend(base, overlay, amount, "screen")
        self.assertTrue(np.array_equal(out[:, :2], base[:, :2]))
        self.assertGreater(int(out[0, 3, 0]), 40)

    def test_parse_layer_and_compose_short_loop(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            source = temp / "source"
            source.mkdir()
            scene = source / "scene-base.png"
            mask = source / "effect-mask.png"
            Image.new("RGB", (1920, 1080), (12, 14, 18)).save(scene)
            arr = np.zeros((1080, 1920), dtype=np.uint8)
            arr[100:500, 100:800] = 255
            Image.fromarray(arr, mode="L").save(mask)
            layer = parse_layer(
                {
                    "id": "dust",
                    "kind": "procedural",
                    "effect": "dust_particles",
                    "mask": "effect-mask.png",
                    "opacity": 0.4,
                    "intensity": 0.5,
                },
                temp,
            )
            output = source / "loop.mp4"
            compose_hybrid_loop(
                scene,
                output,
                [layer],
                seconds=0.5,
                fps=10,
                seed=3,
                encode_preset="ultrafast",
            )
            self.assertTrue(output.exists())
            self.assertGreater(output.stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()
