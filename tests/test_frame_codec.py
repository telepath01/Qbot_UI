"""Check that raw stream bytes are decoded into the expected image and lidar data."""

from __future__ import annotations

import unittest

import numpy as np

from qbotui.frame_codec import FrameCodec


class FrameCodecRoundTripTest(unittest.TestCase):
    """Test the codec with small generated examples instead of a robot feed."""

    def setUp(self) -> None:
        """Give each test a fresh codec instance."""
        self.codec = FrameCodec()

    def test_downward_grayscale_round_trip(self) -> None:
        """Decoding grayscale bytes should preserve every pixel and its shape."""
        image = np.arange(64000, dtype=np.uint8).reshape(200, 320, 1)
        decoded = self.codec.decode_image(image.tobytes(), 200, 320, 1)
        self.assertEqual(decoded.shape, (200, 320, 1))
        np.testing.assert_array_equal(decoded, image)

    def test_depth_grayscale_round_trip(self) -> None:
        """The depth camera's grayscale payload should also preserve its pixels."""
        image = (np.arange(76800, dtype=np.uint16) % 251).astype(np.uint8).reshape(240, 320, 1)
        decoded = self.codec.decode_image(image.tobytes(), 240, 320, 1)
        self.assertEqual(decoded.shape, (240, 320, 1))
        np.testing.assert_array_equal(decoded, image)

    def test_realsense_bgr_bytes_become_rgb(self) -> None:
        """Network BGR channel order must be converted to display RGB order."""
        rgb = np.zeros((240, 320, 3), dtype=np.uint8)
        rgb[..., 0] = 10
        rgb[..., 1] = 80
        rgb[..., 2] = 200
        # Reverse the channels to simulate the BGR bytes sent over the network.
        wire = np.ascontiguousarray(rgb[..., ::-1]).tobytes()
        self.assertEqual(len(wire), 230400)
        decoded = self.codec.decode_image(wire, 240, 320, 3)
        self.assertEqual(decoded.shape, (240, 320, 3))
        np.testing.assert_array_equal(decoded, rgb)

    def test_lidar_little_endian_column_order(self) -> None:
        """Lidar bytes contain 210 distance/angle pairs in little-endian order."""
        distances = np.linspace(0.25, 2.5, 210, dtype=np.float32)
        angles = np.linspace(-1.0, 1.0, 210, dtype=np.float32)
        points = np.empty((210, 2), dtype=np.dtype("<f4"))
        points[:, 0] = distances
        points[:, 1] = angles
        payload = np.ascontiguousarray(points, dtype=np.dtype("<f4")).tobytes()
        self.assertEqual(len(payload), 1680)
        decoded = self.codec.decode_lidar(payload)
        self.assertEqual(decoded.shape, (210, 2))
        self.assertEqual(decoded.dtype.str, "<f4")
        self.assertTrue(decoded.flags["C_CONTIGUOUS"])
        flat = np.frombuffer(payload, dtype=np.dtype("<f4"))
        self.assertEqual(float(flat[0]), float(decoded[0, 0]))
        self.assertEqual(float(flat[1]), float(decoded[0, 1]))
        np.testing.assert_array_equal(decoded[:, 0], points[:, 0])
        np.testing.assert_array_equal(decoded[:, 1], points[:, 1])

    def test_short_payload_is_rejected(self) -> None:
        """Incomplete image or lidar data must not be treated as a full frame."""
        with self.assertRaises(ValueError):
            self.codec.decode_image(b"\x00" * 10, 200, 320, 1)
        with self.assertRaises(ValueError):
            self.codec.decode_lidar(b"\x00" * 16)

    def test_qimage_copy_owns_its_bytes(self) -> None:
        """A Qt image must retain its pixels after the original NumPy array changes."""
        from PySide6.QtGui import QImage

        source = np.full((8, 8, 1), 40, dtype=np.uint8)
        image = self.codec.qimage_from_gray(source)
        self.assertFalse(image.isNull())
        self.assertEqual(image.format(), QImage.Format.Format_Grayscale8)
        self.assertEqual(image.pixelColor(0, 0).red(), 40)
        source[:] = 0
        self.assertEqual(image.pixelColor(0, 0).red(), 40)

        rgb = np.zeros((4, 4, 3), dtype=np.uint8)
        rgb[..., 0] = 1
        rgb[..., 1] = 2
        rgb[..., 2] = 3
        color = self.codec.qimage_from_rgb(rgb)
        self.assertEqual(color.format(), QImage.Format.Format_RGB888)
        self.assertEqual(color.pixelColor(0, 0).red(), 1)
        self.assertEqual(color.pixelColor(0, 0).green(), 2)
        self.assertEqual(color.pixelColor(0, 0).blue(), 3)
        rgb[:] = 0
        self.assertEqual(color.pixelColor(0, 0).red(), 1)
