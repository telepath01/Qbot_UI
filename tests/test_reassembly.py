"""Check how several TCP reads are combined into fixed-size frames."""

from __future__ import annotations

import unittest

from qbotui.reassembly import FrameReassembly


class ChunkReader:
    """A fake input source that returns preselected byte chunks one at a time."""

    def __init__(self, chunks: list[bytes]) -> None:
        """Save the chunks that future calls to ``read`` will return."""
        self._chunks = list(chunks)

    def read(self, size: int) -> bytes:
        """Return the next chunk; the test data controls how many bytes arrive."""
        del size
        if not self._chunks:
            return b""
        return self._chunks.pop(0)


class FrameReassemblyTest(unittest.TestCase):
    """Verify that frame boundaries come from the known byte count, not TCP reads."""

    def test_short_reads_rebuild_exact_frames(self) -> None:
        """Small reads should be combined, and leftover bytes form the next frame."""
        first = bytes(range(20))
        second = bytes((value * 3) % 256 for value in range(20))
        chunks = [first[:3], first[3:4], first[4:], second[:1], second[1:9], second[9:]]
        reader = ChunkReader(chunks)
        assembler = FrameReassembly(20)
        self.assertEqual(assembler.read_frame(reader), first)
        self.assertEqual(assembler.read_frame(reader), second)
        self.assertEqual(len(first), assembler.frame_size)

    def test_length_looking_bytes_stay_inside_the_payload(self) -> None:
        """Bytes that resemble a length header are still ordinary frame contents."""
        payload = b"\x00\x00\x00\x04ABCD"
        reader = ChunkReader([payload[:1], payload[1:3], payload[3:]])
        frame = FrameReassembly(8).read_frame(reader)
        self.assertEqual(frame, payload)
        self.assertEqual(len(frame), 8)

    def test_ended_stream_does_not_invent_a_frame(self) -> None:
        """If the connection ends early, the reader must report an incomplete frame."""
        reader = ChunkReader([b"abc"])
        with self.assertRaises(ConnectionError):
            FrameReassembly(8).read_frame(reader)
