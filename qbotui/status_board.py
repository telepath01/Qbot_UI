"""Per-port listener status and an unparsed terminal paste box."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QPlainTextEdit, QVBoxLayout, QWidget


class StatusBoard(QWidget):
    """Show listener state. Pasted robot terminal text is never parsed or sent."""

    INSTRUCTION = "The robot does not redial until its script is restarted."

    def __init__(self, labels: list[str], parent: QWidget | None = None) -> None:
        """Create one status row per stream and a box for optional pasted text."""
        super().__init__(parent)
        self._instruction = QLabel(self.INSTRUCTION)
        self._instruction.setObjectName("redialInstruction")
        self._instruction.setWordWrap(True)
        self._note = QLabel("")
        self._note.setObjectName("statusNote")
        self._note.setWordWrap(True)
        self._rows: dict[str, QLabel] = {}
        self._states: dict[str, str] = {}
        self._activity: dict[str, str] = {}
        layout = QVBoxLayout(self)
        layout.addWidget(self._instruction)
        layout.addWidget(self._note)
        for label in labels:
            row = QLabel(f"{label}: stopped")
            row.setWordWrap(True)
            self._rows[label] = row
            layout.addWidget(row)
        self._paste = QPlainTextEdit()
        self._paste.setObjectName("robotTerminalPaste")
        self._paste.setPlaceholderText(
            "Paste robot terminal text here. This viewer does not parse it, "
            "does not treat it as a password, and does not send it."
        )
        self._paste.setMinimumHeight(90)
        layout.addWidget(self._paste)

    def set_state(self, label: str, state: str) -> None:
        """Update a known stream's connection state and redraw its status row."""
        if label not in self._rows:
            return
        self._states[label] = state
        self._render(label)

    def set_activity(self, label: str, text: str) -> None:
        """Update a known stream's byte/frame activity message."""
        if label not in self._rows:
            return
        self._activity[label] = text
        self._render(label)

    def _render(self, label: str) -> None:
        """Combine a stream's latest state and activity into its visible row."""
        state = self._states.get(label, "stopped")
        extra = self._activity.get(label, "")
        if extra:
            self._rows[label].setText(f"{label}: {state} — {extra}")
        else:
            self._rows[label].setText(f"{label}: {state}")

    def show_note(self, text: str) -> None:
        """Show a short message above the per-stream status rows."""
        self._note.setText(text)
