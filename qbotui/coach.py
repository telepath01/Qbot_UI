"""Operator instructions. This widget never starts the robot script."""

from __future__ import annotations

from PySide6.QtWidgets import QPlainTextEdit, QVBoxLayout, QWidget


class Coach(QWidget):
    """Show ipHost and the four-step order the operator runs by hand."""

    STEPS = (
        "1. Confirm one IPv4. The window shows it as ipHost. The servers stay down until listeners start.",
        "2. Start listeners. That binds ports 18801, 18802, 18803, and 18601 on that address only.",
        "3. Start the robot script yourself. This application does not start it.",
        "4. Status tracks each port.",
    )
    RULES = (
        "ipHost in the robot copy must be the address shown here.",
        "On the robot, ipDriver stays localhost.",
        "On the robot, in /home/nvidia/Desktop, run python3 quick_start_qbot_platform.py only after the four servers are listening.",
        "Do not start that script on this Windows PC.",
        "Do not run the lab observer.py while this viewer is listening.",
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        """Build a read-only panel with manual startup instructions."""
        super().__init__(parent)
        self._view = QPlainTextEdit()
        self._view.setObjectName("coachText")
        self._view.setReadOnly(True)
        layout = QVBoxLayout(self)
        layout.addWidget(self._view)
        self.set_ip_host(None)

    def set_ip_host(self, address: str | None) -> None:
        """Update the instructions with the confirmed address, or its empty state."""
        shown = address if address else "(not confirmed)"
        lines = [
            "Startup order",
            *self.STEPS,
            "",
            f"ipHost: {shown}",
            "",
            *self.RULES,
        ]
        self._view.setPlainText("\n".join(lines))
