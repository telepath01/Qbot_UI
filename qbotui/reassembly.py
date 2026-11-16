"""Accumulate a TCP byte stream until the known frame size is reached."""

from __future__ import annotations


class FrameReassembly:
    """Buffer TCP data until one known-size frame can be returned."""

    def __init__(self, frame_size: int) -> None:
        """Create a buffer for frames with the given fixed byte count."""
        if frame_size <= 0:
            raise ValueError("frame size must be the known byte count")
        self._frame_size = frame_size
        self._buffer = bytearray()

    @property
    def frame_size(self) -> int:
        """Return the number of bytes required for one frame."""
        return self._frame_size

    def read_frame(self, reader: object) -> bytes:
        """Read enough bytes for one frame, retaining any extra bytes for later.

        TCP is a byte stream, so one read is not guaranteed to match one frame.
        ``reader`` only needs to provide a ``read(size)`` method.
        """
        read = getattr(reader, "read", None)
        if not callable(read):
            raise TypeError("reader must provide read(size)")
        while len(self._buffer) < self._frame_size:
            chunk = read(self._frame_size - len(self._buffer))
            if not chunk:
                raise ConnectionError("stream ended before the exact frame byte count")
            if not isinstance(chunk, (bytes, bytearray)):
                raise TypeError("reader.read must return bytes")
            self._buffer.extend(chunk)
        frame = bytes(self._buffer[: self._frame_size])
        del self._buffer[: self._frame_size]
        return frame
