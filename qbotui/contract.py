"""Fixed probe streams. The frame boundary is the known byte count."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProbeStream:
    """One raw TCP probe: label, port, and the exact payload size."""

    label: str
    port: int
    byte_count: int
    kind: str
    shape: tuple[int, ...]

    def __post_init__(self) -> None:
        """Reject a stream definition whose size disagrees with its image layout."""
        if self.kind == "lidar":
            # Each lidar row contains two 32-bit floating-point values.
            expected = 210 * 2 * 4
        elif self.kind in ("gray", "bgr"):
            expected = 1
            for axis in self.shape:
                expected *= axis
        else:
            raise ValueError(f"unknown probe kind {self.kind}")
        if self.byte_count != expected:
            raise ValueError(
                f"{self.label} byte count {self.byte_count} does not match {expected}"
            )


class ProbeContract:
    """The four fixed ports, payload sizes, and shapes used by this viewer."""

    DOWNWARD = ProbeStream(
        "Downward Facing Image",
        18801,
        64000,
        "gray",
        (200, 320, 1),
    )
    RGB = ProbeStream(
        "RealSense RGB Image",
        18802,
        230400,
        "bgr",
        (240, 320, 3),
    )
    DEPTH = ProbeStream(
        "RealSense Depth Image",
        18803,
        76800,
        "gray",
        (240, 320, 1),
    )
    LIDAR = ProbeStream(
        "Leishen M10P Lidar",
        18601,
        1680,
        "lidar",
        (210, 2),
    )
    STREAMS: tuple[ProbeStream, ...] = (DOWNWARD, RGB, DEPTH, LIDAR)

    @classmethod
    def ports(cls) -> frozenset[int]:
        """Return the allowed listener ports as an immutable set."""
        return frozenset(stream.port for stream in cls.STREAMS)
