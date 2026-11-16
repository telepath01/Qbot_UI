"""Display stretch for the received 8-bit depth buffer.

The robot already mapped meters to uint8 with 0 m at 0 and 3 m at 255.
A normal scene therefore sits in the dark end of that range. This class
changes only the picture painted in the window.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class ShadedDepth:
    """RGB picture plus the raw uint8 range that produced it."""

    image: np.ndarray
    detail: str


class DepthShade:
    """Stretch the received depth bytes so the shapes in them are visible."""

    def shade(self, gray: np.ndarray) -> ShadedDepth:
        """Create a more visible color image without modifying the source depth data.

        Zero means "no depth reading", so it is excluded from the percentile
        calculation and painted black in the result.
        """
        plane = np.ascontiguousarray(gray, dtype=np.uint8)
        if plane.ndim == 3 and plane.shape[2] == 1:
            plane = plane.reshape(plane.shape[0], plane.shape[1])
        if plane.ndim != 2:
            raise ValueError("depth image must have one channel")

        raw_min = int(plane.min())
        raw_max = int(plane.max())
        valid = plane[plane > 0]
        if valid.size == 0:
            blank = np.zeros((plane.shape[0], plane.shape[1], 3), dtype=np.uint8)
            return ShadedDepth(blank, "raw 0–0, every pixel is 0")

        low = int(np.percentile(valid, 2))
        high = int(np.percentile(valid, 98))
        if high <= low:
            high = low + 1
        # Map the middle 96% of valid readings across the full display range.
        scaled = (plane.astype(np.float32) - low) * (255.0 / (high - low))
        scaled = np.clip(scaled, 0, 255).astype(np.uint8)
        scaled[plane == 0] = 0
        colored = cv2.applyColorMap(scaled, cv2.COLORMAP_TURBO)
        colored[plane == 0] = 0
        rgb = cv2.cvtColor(colored, cv2.COLOR_BGR2RGB)
        detail = f"raw {raw_min}–{raw_max}, display stretched"
        return ShadedDepth(np.ascontiguousarray(rgb), detail)
