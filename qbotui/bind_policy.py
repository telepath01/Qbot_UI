"""Listen-address rules. Illegal hosts and ports are rejected before bind."""

from __future__ import annotations

import ipaddress

from qbotui.contract import ProbeContract


class BindRejected(Exception):
    """The operator's address or port is not a legal listen target."""


class BindPolicy:
    """The only legal listen address is the single confirmed IPv4."""

    ALLOWED_PORTS = ProbeContract.ports()

    def __init__(self) -> None:
        """Start with no network address authorized for listening."""
        self._confirmed: str | None = None

    @property
    def allowed_ports(self) -> frozenset[int]:
        """Return the fixed set of ports reserved for probe streams."""
        return self.ALLOWED_PORTS

    @property
    def confirmed_address(self) -> str | None:
        """Return the confirmed address, if the operator has chosen one."""
        return self._confirmed

    def validated_host(self, host: object) -> str:
        """Check that ``host`` is a usable IPv4 address and return its normalized form."""
        if host == "":
            raise BindRejected("empty host")
        if not isinstance(host, str):
            raise BindRejected("not an IPv4 address")
        try:
            parsed = ipaddress.IPv4Address(host)
        except ipaddress.AddressValueError as exc:
            raise BindRejected("not an IPv4 address") from exc
        normalized = str(parsed)
        if normalized == "0.0.0.0":
            raise BindRejected("0.0.0.0")
        if normalized == "127.0.0.1":
            raise BindRejected("127.0.0.1")
        return normalized

    def confirm(self, host: str) -> str:
        """Record one address; refuse attempts to replace it without release."""
        normalized = self.validated_host(host)
        if self._confirmed is not None and normalized != self._confirmed:
            raise BindRejected("second address")
        self._confirmed = normalized
        return normalized

    def release(self) -> None:
        """Drop the confirmed address. Callers may do this only while servers are stopped."""
        self._confirmed = None

    def authorize_bind(self, host: str, port: int) -> tuple[str, int]:
        """Validate a server bind request against the address and port allowlist."""
        normalized = self.validated_host(host)
        if port not in self.ALLOWED_PORTS:
            raise BindRejected("port is outside the probe set")
        if self._confirmed is None:
            raise BindRejected("no confirmed address")
        if normalized != self._confirmed:
            raise BindRejected("second address")
        return normalized, port
