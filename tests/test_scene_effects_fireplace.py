from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from scene_effects import render_fireplace_flicker


def _fireplace_base() -> np.ndarray:
    base = np.full((1080, 1920, 3), 18, dtype=np.uint8)
    base[200:560, 420:1200] = [40, 70, 95]
    base[520:860, 1450:1820] = [170, 90, 35]
    return base


class FireplaceFlickerTests(unittest.TestCase):
    def test_fireplace_flicker_is_slow_and_gentle(self) -> None:
        base = _fireplace_base()
        a = render_fireplace_flicker(base, 0, 480)
        near = render_fireplace_flicker(base, 3, 480)
        mid = render_fireplace_flicker(base, 120, 480)
        self.assertLessEqual(abs(int(a[700, 1600, 0]) - int(near[700, 1600, 0])), 12)
        self.assertFalse(np.array_equal(a, mid))
        self.assertLessEqual(int(mid[300, 700, 0]) - int(base[300, 700, 0]), 10)


if __name__ == "__main__":
    unittest.main()
