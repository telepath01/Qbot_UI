"""Check address selection rules without accessing the Windows network API."""

from __future__ import annotations

import unittest

from qbotui.interface_directory import InterfaceDirectory


class InterfaceFilterTest(unittest.TestCase):
    """Verify which local IPv4 addresses can be offered to the user."""

    def test_drops_loopback_apipa_and_down_adapters(self) -> None:
        """Hide local-only, self-assigned, and inactive network addresses."""
        directory = InterfaceDirectory()
        rows = (
            ("loopback", "127.0.0.1", 1),
            ("loopback-other", "127.0.0.2", 1),
            ("apipa", "169.254.5.5", 1),
            ("down", "10.0.0.8", 2),
            ("up", "10.0.0.8", 1),
        )
        # Apply the same filter to sample adapter rows and keep only accepted ones.
        kept = [
            (name, ip)
            for name, ip, status in rows
            if directory.keep_address(ip, status)
        ]
        self.assertEqual(kept, [("up", "10.0.0.8")])
        self.assertFalse(hasattr(directory, "selected"))

    def test_ipv4_is_bytes_two_through_six_of_sa_data(self) -> None:
        """Read the four IPv4 bytes from their documented position in Windows data."""
        directory = InterfaceDirectory()
        usable = bytes([0x00, 0x50, 10, 1, 2, 3]) + bytes(8)
        loopback = bytes([0x00, 0x00, 127, 0, 0, 1]) + bytes(8)
        self.assertEqual(directory.ipv4_from_sa_data(usable), "10.1.2.3")
        self.assertEqual(directory.ipv4_from_sa_data(loopback), "127.0.0.1")
        self.assertFalse(directory.keep_address(directory.ipv4_from_sa_data(loopback), 1))
