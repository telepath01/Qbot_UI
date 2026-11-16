"""Start the QBot viewer when run with ``python -m qbotui``."""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    """Create the Qt application, show its main window, and run its event loop.

    ``argv`` lets tests or other callers supply command-line arguments; normal
    command-line use passes the arguments from Python's ``sys.argv``.
    """
    from PySide6.QtWidgets import QApplication

    from qbotui.main_window import QbotMainWindow

    # Qt needs one application object to manage windows and respond to events.
    app = QApplication(sys.argv if argv is None else argv)
    window = QbotMainWindow()
    window.show()
    # The event loop keeps the window responsive until the user closes it.
    return int(app.exec())


if __name__ == "__main__":
    raise SystemExit(main())
