"""Check that lidar distance/angle readings land at the right image pixels."""

from __future__ import annotations

import unittest

import numpy as np

from qbotui.frame_codec import FrameCodec


class LidarRasterTest(unittest.TestCase):
    """Verify the simple coordinate conversion used to draw lidar points."""

    def test_center_and_one_meter_at_angle_zero(self) -> None:
        """Zero distance is at the center; one meter forward is 50 pixels above it."""
        points = np.zeros((210, 2), dtype=np.dtype("<f4"))
        points[0, 0] = 0.0
        points[0, 1] = 0.0
        points[1, 0] = 1.0
        points[1, 1] = 0.0
        canvas = FrameCodec().raster_lidar(points)
        self.assertEqual(canvas.shape, (400, 400))
        self.assertEqual(canvas.dtype, np.uint8)
        self.assertEqual(int(canvas[200, 200]), 255)
        self.assertEqual(int(canvas[150, 200]), 255)
        self.assertEqual(int(canvas[200, 150]), 0)
        self.assertEqual(int(canvas.sum()), 255 * 2)
