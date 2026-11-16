"""Check how received depth pixels are made easier to see on screen."""

from __future__ import annotations

import unittest

import numpy as np
from PySide6.QtGui import QImage

from qbotui.contract import ProbeContract
from qbotui.depth_shade import DepthShade
from qbotui.frame_codec import FrameCodec


class DepthShadeTest(unittest.TestCase):
    """Verify depth shading and its use by the frame display code."""

    def test_flat_zero_stays_black_and_says_so(self) -> None:
        """An all-zero image means no readings, so it remains black."""
        shaded = DepthShade().shade(np.zeros((240, 320), dtype=np.uint8))
        self.assertEqual(shaded.image.shape, (240, 320, 3))
        self.assertEqual(int(shaded.image.max()), 0)
        self.assertIn("every pixel is 0", shaded.detail)

    def test_narrow_range_uses_the_full_color_scale(self) -> None:
        """A small range of useful readings should still have visible contrast."""
        plane = np.full((240, 320), 20, dtype=np.uint8)
        plane[80:160, 40:280] = 45
        shaded = DepthShade().shade(plane)
        near = shaded.image[10, 10].astype(int)
        far = shaded.image[100, 100].astype(int)
        self.assertGreater(int(np.abs(near - far).sum()), 80)
        self.assertIn("raw 20–45", shaded.detail)

    def test_present_depth_is_rgb_and_downward_stays_gray(self) -> None:
        """Depth is colorized, while the downward camera keeps its gray format."""
        codec = FrameCodec()
        depth = np.full((240, 320, 1), 30, dtype=np.uint8)
        depth[40:100, 40:100] = 70
        presented = codec.present(ProbeContract.DEPTH, depth.tobytes())
        self.assertEqual(presented.image.format(), QImage.Format.Format_RGB888)
        self.assertIn("raw 30–70", presented.detail)
        self.assertGreater(presented.image.pixelColor(50, 60).red(), 0)

        downward = np.full((200, 320, 1), 90, dtype=np.uint8)
        gray = codec.present(ProbeContract.DOWNWARD, downward.tobytes())
        self.assertEqual(gray.image.format(), QImage.Format.Format_Grayscale8)
        self.assertEqual(gray.detail, "")
        self.assertEqual(gray.image.pixelColor(0, 0).red(), 90)
