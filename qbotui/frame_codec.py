"""Decode raw probe payloads and copy them into Qt-owned images."""

from __future__ import annotations

import cv2
import numpy as np
from PySide6.QtGui import QImage

from qbotui.contract import ProbeContract, ProbeStream
from qbotui.depth_shade import DepthShade


class PresentedFrame:
    """One Qt image and an optional caption for the feed that produced it."""

    def __init__(self, image: QImage, detail: str = "") -> None:
        """Pair the display-ready Qt image with an optional explanatory caption."""
        self.image = image
        self.detail = detail


class FrameCodec:
    """Turn complete network payloads into images the Qt widgets can display."""

    CANVAS = 400
    PIXELS_PER_METER = 50
    OFFSET = 200
    LIDAR_ROWS = 210
    LIDAR_BYTES = 1680

    def __init__(self, depth_shade: DepthShade | None = None) -> None:
        self._depth_shade = depth_shade if depth_shade is not None else DepthShade()

    def decode_image(
        self,
        payload: bytes,
        height: int,
        width: int,
        channels: int,
    ) -> np.ndarray:
        """Check an image's byte count, reshape its bytes, and convert BGR to RGB."""
        expected = height * width * channels
        if channels not in (1, 3) or len(payload) != expected:
            raise ValueError("image payload is not the contracted byte count")
        image = np.frombuffer(payload, dtype=np.uint8).reshape((height, width, channels)).copy()
        if channels == 3:
            return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        return image

    def decode_lidar(self, payload: bytes) -> np.ndarray:
        """Interpret one lidar payload as 210 pairs of little-endian 32-bit floats."""
        if len(payload) != self.LIDAR_BYTES:
            raise ValueError("lidar payload is not 1680 bytes")
        points = np.frombuffer(payload, dtype=np.dtype("<f4")).reshape((self.LIDAR_ROWS, 2))
        if not points.flags["C_CONTIGUOUS"]:
            points = np.ascontiguousarray(points)
        return points.copy()

    def raster_lidar(self, points: np.ndarray) -> np.ndarray:
        """Plot distance/angle measurements as white pixels on a square gray image."""
        cloud = np.asarray(points, dtype=np.float64)
        if cloud.ndim != 2 or cloud.shape[1] != 2:
            raise ValueError("lidar points must be (N, 2)")
        canvas = np.zeros((self.CANVAS, self.CANVAS), dtype=np.uint8)
        distance = cloud[:, 0]
        angle = cloud[:, 1]
        # Convert polar coordinates (distance and angle) to image row and column.
        row = np.clip(
            self.OFFSET - self.PIXELS_PER_METER * distance * np.cos(angle),
            0,
            self.CANVAS - 1,
        ).astype(np.int32)
        col = np.clip(
            self.OFFSET - self.PIXELS_PER_METER * distance * np.sin(angle),
            0,
            self.CANVAS - 1,
        ).astype(np.int32)
        canvas[row, col] = 255
        return canvas

    def qimage_from_gray(self, image: np.ndarray) -> QImage:
        """Make a Qt grayscale image from a 2-D array (or a one-channel array)."""
        plane = np.ascontiguousarray(image, dtype=np.uint8)
        if plane.ndim == 3 and plane.shape[2] == 1:
            plane = plane.reshape(plane.shape[0], plane.shape[1])
        if plane.ndim != 2:
            raise ValueError("grayscale image must have one channel")
        return self._owned_qimage(plane, QImage.Format.Format_Grayscale8, channels=1)

    def qimage_from_rgb(self, image: np.ndarray) -> QImage:
        """Make a Qt RGB image, rejecting arrays that do not have three channels."""
        plane = np.ascontiguousarray(image, dtype=np.uint8)
        if plane.ndim != 3 or plane.shape[2] != 3:
            raise ValueError("RGB image must have three channels")
        return self._owned_qimage(plane, QImage.Format.Format_RGB888, channels=3)

    def present(self, stream: ProbeStream, payload: bytes) -> PresentedFrame:
        """Decode one stream frame and apply any stream-specific display processing."""
        if len(payload) != stream.byte_count:
            raise ValueError("payload is not one full frame")
        if stream.kind == "lidar":
            raster = self.raster_lidar(self.decode_lidar(payload))
            return PresentedFrame(self.qimage_from_gray(raster))
        height, width, channels = stream.shape
        decoded = self.decode_image(payload, height, width, channels)
        if channels == 3:
            return PresentedFrame(self.qimage_from_rgb(decoded))
        if stream.port == ProbeContract.DEPTH.port:
            shaded = self._depth_shade.shade(decoded)
            return PresentedFrame(self.qimage_from_rgb(shaded.image), shaded.detail)
        return PresentedFrame(self.qimage_from_gray(decoded))

    def frame_to_qimage(self, stream: ProbeStream, payload: bytes) -> QImage:
        """Convenience method for callers that need the image but not its caption."""
        return self.present(stream, payload).image

    def _owned_qimage(self, plane: np.ndarray, fmt: QImage.Format, channels: int) -> QImage:
        """Copy array bytes into Qt-owned memory so the image outlives the array."""
        contiguous = np.ascontiguousarray(plane, dtype=np.uint8)
        if channels == 1:
            height, width = contiguous.shape[:2]
        else:
            height, width = contiguous.shape[:2]
        qimage = QImage(width, height, fmt)
        if qimage.isNull():
            raise ValueError("Qt did not allocate the image")
        source = np.ascontiguousarray(contiguous, dtype=np.uint8)
        raw = source.reshape(height, width * channels).tobytes()
        target = qimage.bits()
        row_bytes = width * channels
        stride = qimage.bytesPerLine()
        # Qt may pad each row; copy row-by-row when its stride exceeds pixel data.
        if stride == row_bytes:
            target[: height * row_bytes] = raw
        else:
            for row in range(height):
                dest = row * stride
                src = row * row_bytes
                target[dest : dest + row_bytes] = raw[src : src + row_bytes]
        del target
        return qimage
