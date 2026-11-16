"""The single top-level window. It composes the viewer, coach, status, and safety pane."""

from __future__ import annotations

from PySide6.QtCore import QObject, Qt, Slot
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from qbotui.address_chooser import AddressChooser
from qbotui.bind_policy import BindPolicy, BindRejected
from qbotui.coach import Coach
from qbotui.contract import ProbeContract
from qbotui.feed_tile import FeedTile
from qbotui.frame_codec import FrameCodec
from qbotui.interface_directory import InterfaceDirectory
from qbotui.safety_panel import SafetyPanel
from qbotui.status_board import StatusBoard
from qbotui.viewer import Viewer


class _FrameSink(QObject):
    """GUI-thread receiver for one probe's raw frames."""

    def __init__(self, label: str, window: QbotMainWindow) -> None:
        """Remember which feed receives frames and which window displays them."""
        super().__init__(window)
        self._label = label
        self._window = window

    @Slot(bytes)
    def accept(self, payload: bytes) -> None:
        """Forward a complete network frame to the window's display method."""
        self._window._show_payload(self._label, payload)


class QbotMainWindow(QMainWindow):
    """Confirm one IPv4, then listen on the four probe ports and no others."""

    def __init__(self) -> None:
        """Create all panels, connect their signals, and populate the address list."""
        super().__init__()
        self.setWindowTitle("QBot Platform Probe Viewer")
        self.resize(1280, 860)

        self._directory = InterfaceDirectory()
        self._policy = BindPolicy()
        self._codec = FrameCodec()
        self._viewer = Viewer(self._policy, parent=self)

        self._feeds: dict[str, FeedTile] = {}
        grid_host = QWidget()
        grid = QGridLayout(grid_host)
        # Keep each stream's image tile in a two-column grid.
        for index, stream in enumerate(ProbeContract.STREAMS):
            tile = FeedTile(stream.label)
            self._feeds[stream.label] = tile
            grid.addWidget(tile, index // 2, index % 2)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setRowStretch(0, 1)
        grid.setRowStretch(1, 1)

        self._coach = Coach()
        self._status = StatusBoard([stream.label for stream in ProbeContract.STREAMS])
        self._safety = SafetyPanel()
        self._safety.stop_requested.connect(self._stop_listeners)

        self._sinks: list[_FrameSink] = []
        for server in self._viewer.servers:
            # Server signals arrive from worker threads; Qt delivers them to
            # these GUI-owned receivers so widgets are updated on the GUI thread.
            server.state_changed.connect(self._status.set_state)
            server.activity.connect(self._status.set_activity)
            sink = _FrameSink(server.label, self)
            self._sinks.append(sink)
            server.frame_ready.connect(sink.accept)

        self._address_list = AddressChooser()
        self._address_list.setObjectName("addressList")
        self._address_list.setMinimumHeight(96)
        self._refresh = QPushButton("Refresh addresses")
        self._refresh.clicked.connect(self._reload_addresses)
        self._confirm = QPushButton("Confirm address")
        self._confirm.setObjectName("confirmAddressButton")
        self._confirm.clicked.connect(self._confirm_address)
        self._ip_host = QLabel("ipHost: (not confirmed)")
        self._ip_host.setObjectName("ipHostLabel")
        self._ip_host.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._start = QPushButton("Start listeners")
        self._start.setObjectName("startListenersButton")
        self._start.clicked.connect(self._start_listeners)
        self._start.setEnabled(False)

        controls = QHBoxLayout()
        controls.addWidget(self._address_list, 1)
        controls.addWidget(self._refresh)
        controls.addWidget(self._confirm)
        controls.addWidget(self._ip_host)
        controls.addWidget(self._start)

        side = QVBoxLayout()
        side.addWidget(self._coach, 2)
        side.addWidget(self._status, 2)
        side.addWidget(self._safety, 3)
        side_host = QWidget()
        side_host.setLayout(side)

        body = QHBoxLayout()
        body.addWidget(grid_host, 3)
        body.addWidget(side_host, 2)

        outer = QVBoxLayout()
        outer.addLayout(controls)
        outer.addLayout(body, 1)
        central = QWidget()
        central.setLayout(outer)
        self.setCentralWidget(central)
        self._reload_addresses()
        self._sync_controls()

    @Slot(str, bytes)
    def _show_payload(self, label: str, payload: bytes) -> None:
        """Find the matching tile, decode the payload, and display its image."""
        tile = self._feeds.get(label)
        if tile is None:
            return
        stream = next(
            (item for item in ProbeContract.STREAMS if item.label == label),
            None,
        )
        if stream is None:
            return
        try:
            presented = self._codec.present(stream, payload)
        except Exception as exc:
            # Show decoding problems in the feed instead of silently hiding them.
            tile.set_detail(f"frame error: {exc}")
            return
        tile.show_frame(presented.image)
        if presented.detail:
            tile.set_detail(presented.detail)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Stop the PC listeners before allowing the main window to close."""
        self._viewer.stop()
        event.accept()

    def _reload_addresses(self) -> None:
        """Refresh the list of eligible local IPv4 addresses."""
        try:
            rows = self._directory.list_addresses()
        except OSError as exc:
            self._address_list.replace_rows([])
            self._status.show_note(f"Address enumeration failed: {exc}")
            return
        self._address_list.replace_rows(rows)
        if not rows:
            self._status.show_note(
                "No eligible IPv4 address was enumerated. Nothing was selected."
            )

    def _confirm_address(self) -> None:
        """Require an explicit list choice before authorizing a listen address."""
        chosen = self._address_list.chosen_address()
        if chosen is None:
            self._status.show_note(
                "Select one IPv4, then confirm it. The list is not selected automatically."
            )
            return
        try:
            confirmed = self._viewer.confirm_address(chosen)
        except BindRejected as exc:
            self._status.show_note(str(exc))
            return
        self._ip_host.setText(f"ipHost: {confirmed}")
        self._coach.set_ip_host(confirmed)
        self._status.show_note("Address confirmed. Listeners are still stopped.")
        self._sync_controls()

    def _start_listeners(self) -> None:
        """Ask the viewer to start all probe listeners on the confirmed address."""
        try:
            self._viewer.start()
        except BindRejected as exc:
            self._status.show_note(str(exc))
            return
        self._status.show_note(
            "Listeners were asked to bind the confirmed address only. "
            "The robot does not redial until its script is restarted."
        )
        self._sync_controls()

    def _stop_listeners(self) -> None:
        """Stop only this computer's viewer servers and refresh the controls."""
        self._viewer.stop()
        self._status.show_note("This stops the PC viewer servers only.")
        self._sync_controls()

    def _sync_controls(self) -> None:
        """Disable address controls while servers are active and gate the start button."""
        locked = self._viewer.listeners_active
        self._start.setEnabled(self._viewer.confirmed_address is not None and not locked)
        self._confirm.setEnabled(not locked)
        self._address_list.setEnabled(not locked)
