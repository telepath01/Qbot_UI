"""Checklist and exit facts. Stop closes only the PC viewer servers."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget


class SafetyPanel(QWidget):
    """Show the hardware checklist. The window does not perform those steps."""

    stop_requested = Signal()

    CHECKLIST = (
        "The QBot is powered on with the silver button. The LCD IP has been read, ping from the PC succeeds, and the PC is on that same subnet.",
        "The floor is clear.",
        "This is the physical QBot Platform hardware setup. It is not QLabs and not the digital twin.",
        "The Logitech F710 is plugged into the robot and is in mode D.",
        "The real-time model is already on the robot next to quick_start_qbot_platform.py. This PC app does not install it.",
        "This viewer is running and all four ports are listening on the one robot-subnet IPv4 shown for ipHost, and on no other address.",
        "The lab observer.py is not also running on this PC.",
        "ipHost in the robot copy is that same address. On the robot, ipDriver stays localhost.",
        "The robot script is started on the robot only after the viewer is listening, from /home/nvidia/Desktop, with python3 quick_start_qbot_platform.py.",
        "quick_start_qbot_platform.py is not started on the Windows PC.",
        "A person is at the F710. Right bumper, or Ctrl+C in the robot script's terminal, is how that script leaves its loop. This window does not do that job.",
        "The script's own limit is 90 seconds.",
        "Closing this window does not stop the wheels and does not unload the QUARC model.",
        "The legacy stream is unauthenticated. Anyone on that one subnet can connect. That residual is accepted. The robot script is not edited to add authentication.",
    )
    STATEMENTS = (
        "After the robot script has connected, its connected flag does not clear when the PC servers go away, so the robot loop can keep applying the gamepad.",
        "On exit the robot script does not send a final zero motor command, does not unload the QUARC model, and does not release the gamepad.",
        "The robot script stops its own loop at 90 seconds.",
        "Closing this window does not disarm the robot.",
        "Driving stays on the Logitech F710 on the robot, in mode D. Left bumper arms. Right stick commands fore and aft. Left stick turns. Right bumper leaves the robot script loop. This window sends no wheel commands.",
    )
    STOP_SCOPE = "This stops the PC viewer servers only."

    def __init__(self, parent: QWidget | None = None) -> None:
        """Build the checklist and connect Stop to the viewer-server shutdown signal."""
        super().__init__(parent)
        self._stop = QPushButton("Stop")
        self._stop.setObjectName("stopServersButton")
        self._stop.clicked.connect(self.stop_requested.emit)
        self._scope = QLabel(self.STOP_SCOPE)
        self._scope.setObjectName("stopScopeLabel")
        self._scope.setWordWrap(True)
        self._text = QTextEdit()
        self._text.setObjectName("safetyText")
        self._text.setReadOnly(True)
        self._text.setPlainText(self.render_text())

        button_row = QHBoxLayout()
        button_row.addWidget(self._stop)
        button_row.addWidget(self._scope, 1)

        layout = QVBoxLayout(self)
        layout.addLayout(button_row)
        layout.addWidget(self._text)

    def render_text(self) -> str:
        """Return the full safety checklist and explanatory statements as text."""
        lines = ["Checklist. This window does not perform these steps."]
        lines.extend(self.CHECKLIST)
        lines.append("")
        lines.extend(self.STATEMENTS)
        return "\n".join(lines)
