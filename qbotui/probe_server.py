"""One TCP probe listener. One accepted client at a time."""

from __future__ import annotations

import socket
import threading
import time

from PySide6.QtCore import QObject, Signal

from qbotui.bind_policy import BindPolicy
from qbotui.contract import ProbeStream
from qbotui.reassembly import FrameReassembly


class PortState:
    """Status vocabulary for one probe port."""

    STOPPED = "stopped"
    LISTENING = "listening"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    BIND_FAILURE = "bind failure"


class TimedSocketReader:
    """Read socket bytes until data arrives, the peer closes, or stop is set.

    The socket uses a timeout so the thread periodically checks whether it
    should stop instead of waiting forever for incoming data.
    """

    def __init__(self, sock: socket.socket, stop: threading.Event, timeout: float = 0.5) -> None:
        """Store the socket and stop signal used for bounded waiting reads."""
        self._sock = sock
        self._stop = stop
        self._timeout = timeout

    def read(self, size: int) -> bytes:
        """Return received bytes, retrying timeouts until data or a stop occurs."""
        while not self._stop.is_set():
            try:
                return self._sock.recv(size)
            except socket.timeout:
                continue
            except OSError:
                return b""
        return b""


class _CountingReader:
    """Count socket bytes so the status line can show that a port is receiving."""

    def __init__(self, reader: TimedSocketReader, on_bytes) -> None:
        """Wrap a reader so each successful read also updates activity counters."""
        self._reader = reader
        self._on_bytes = on_bytes

    def read(self, size: int) -> bytes:
        """Read a chunk and report its length when at least one byte arrived."""
        chunk = self._reader.read(size)
        if chunk:
            self._on_bytes(len(chunk))
        return chunk


class ProbeServer(QObject):
    """Bind one confirmed address and port, then hand each full frame to the window."""

    frame_ready = Signal(bytes)
    activity = Signal(str, str)
    state_changed = Signal(str, str)

    def __init__(
        self,
        stream: ProbeStream,
        policy: BindPolicy,
        parent: QObject | None = None,
    ) -> None:
        """Prepare server state; no socket is opened until ``start`` is called."""
        super().__init__(parent)
        self._stream = stream
        self._policy = policy
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._listen: socket.socket | None = None
        self._client: socket.socket | None = None
        self._state = PortState.STOPPED

    @property
    def label(self) -> str:
        """Return the human-readable name for this server's stream."""
        return self._stream.label

    @property
    def port(self) -> int:
        """Return the TCP port this server listens on."""
        return self._stream.port

    @property
    def stream(self) -> ProbeStream:
        """Return the fixed size and image details for this server's stream."""
        return self._stream

    @property
    def state(self) -> str:
        """Return the current connection state in a thread-safe way."""
        with self._lock:
            return self._state

    def start(self, host: str) -> None:
        """Validate the address and launch this server's background thread."""
        authorized_host, port = self._policy.authorize_bind(host, self._stream.port)
        with self._lock:
            alive = self._thread is not None and self._thread.is_alive()
        if alive:
            return
        self._stop.clear()
        thread = threading.Thread(
            target=self._run,
            args=(authorized_host, port),
            name=f"probe-{port}",
            daemon=True,
        )
        with self._lock:
            self._thread = thread
        thread.start()

    def mark_bind_failure(self) -> None:
        """Publish a bind-failure state when the viewer cannot authorize startup."""
        self._set_state(PortState.BIND_FAILURE)

    def request_stop(self) -> None:
        """Signal the worker and close sockets so blocked reads/waits can finish."""
        self._stop.set()
        self._close_client()
        self._close_listen()

    def join(self, timeout: float) -> None:
        """Wait briefly for the worker thread to finish, unless called by that thread."""
        with self._lock:
            thread = self._thread
        if thread is not None and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=timeout)

    def mark_stopped(self) -> None:
        """Publish the stopped status after shutdown has been requested."""
        self._set_state(PortState.STOPPED)

    def stop(self) -> None:
        """Request shutdown, wait for the worker, and publish the final state."""
        self.request_stop()
        self.join(3.0)
        self.mark_stopped()

    def _run(self, host: str, port: int) -> None:
        """Bind one TCP port, accept clients, and serve each client in turn."""
        listen = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            listen.bind((host, port))
            listen.listen(1)
        except OSError:
            try:
                listen.close()
            except OSError:
                pass
            if not self._stop.is_set():
                self._set_state(PortState.BIND_FAILURE)
            return

        with self._lock:
            if self._stop.is_set():
                listen.close()
                return
            self._listen = listen
        if self._stop.is_set():
            self._close_listen()
            return
        self._set_state(PortState.LISTENING)

        while not self._stop.is_set():
            try:
                client, _peer = listen.accept()
            except OSError:
                if not self._stop.is_set():
                    self._set_state(PortState.DISCONNECTED)
                break
            if self._stop.is_set():
                try:
                    client.close()
                except OSError:
                    pass
                break
            self._serve_client(client)
        self._close_listen()

    def _serve_client(self, client: socket.socket) -> None:
        """Collect exact-size frames from one client and emit each complete frame."""
        with self._lock:
            if self._client is not None:
                try:
                    client.close()
                except OSError:
                    pass
                return
            self._client = client
        client.settimeout(0.5)
        self._set_state(PortState.CONNECTED)
        received = 0
        frames = 0
        last_note = 0.0

        def note_bytes(count: int) -> None:
            """Update the activity display at most five times per second."""
            nonlocal received, last_note
            received += count
            now = time.monotonic()
            if now - last_note >= 0.2:
                last_note = now
                self.activity.emit(self.label, f"{received} bytes, {frames} frames")

        reader = _CountingReader(TimedSocketReader(client, self._stop), note_bytes)
        # TCP can split or combine frames arbitrarily; reassembly uses the known size.
        reassembly = FrameReassembly(self._stream.byte_count)
        try:
            while not self._stop.is_set():
                try:
                    frame = reassembly.read_frame(reader)
                except ConnectionError:
                    break
                frames += 1
                last_note = time.monotonic()
                self.activity.emit(self.label, f"{received} bytes, {frames} frames")
                self.frame_ready.emit(bytes(frame))
        finally:
            self._close_client()
            if not self._stop.is_set():
                self._set_state(PortState.DISCONNECTED)

    def _close_listen(self) -> None:
        """Detach and close the listening socket safely if one is open."""
        with self._lock:
            sock = self._listen
            self._listen = None
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass

    def _close_client(self) -> None:
        """Detach and close the connected client's socket safely if it is open."""
        with self._lock:
            sock = self._client
            self._client = None
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass

    def _set_state(self, state: str) -> None:
        """Store a port status under lock, then notify the user interface."""
        with self._lock:
            self._state = state
        self.state_changed.emit(self._stream.label, state)
