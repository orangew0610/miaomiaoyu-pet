from __future__ import annotations

import hmac
import json
import secrets
from pathlib import Path

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtNetwork import QHostAddress, QTcpServer

from .config import default_config_dir


PROTOCOL_VERSION = 1
MAX_MESSAGE_BYTES = 256 * 1024


class DiagnosticIpcServer(QObject):
    """Authenticated, loopback-only newline-delimited JSON server."""

    diagnostic_received = pyqtSignal(dict)
    protocol_error = pyqtSignal(str)

    def __init__(self, endpoint_path: Path | None = None, parent=None) -> None:
        super().__init__(parent)
        self.endpoint_path = endpoint_path or default_config_dir() / "ipc.json"
        self.token = secrets.token_urlsafe(32)
        self.server = QTcpServer(self)
        self.server.newConnection.connect(self._accept_connections)
        self._buffers: dict[object, bytearray] = {}

    def start(self) -> bool:
        if not self.server.listen(QHostAddress.LocalHost, 0):
            self.protocol_error.emit(self.server.errorString())
            return False
        self.endpoint_path.parent.mkdir(parents=True, exist_ok=True)
        self.endpoint_path.write_text(
            json.dumps(
                {
                    "version": PROTOCOL_VERSION,
                    "host": "127.0.0.1",
                    "port": self.server.serverPort(),
                    "token": self.token,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return True

    def stop(self) -> None:
        self.server.close()
        try:
            self.endpoint_path.unlink(missing_ok=True)
        except OSError:
            pass

    def _accept_connections(self) -> None:
        while self.server.hasPendingConnections():
            socket = self.server.nextPendingConnection()
            self._buffers[socket] = bytearray()
            socket.readyRead.connect(lambda sock=socket: self._read_socket(sock))
            socket.disconnected.connect(lambda sock=socket: self._drop_socket(sock))

    def _drop_socket(self, socket) -> None:
        self._buffers.pop(socket, None)
        socket.deleteLater()

    def _read_socket(self, socket) -> None:
        buffer = self._buffers.setdefault(socket, bytearray())
        buffer.extend(bytes(socket.readAll()))
        if len(buffer) > MAX_MESSAGE_BYTES:
            self.protocol_error.emit("IPC message exceeded size limit")
            socket.abort()
            return
        while b"\n" in buffer:
            raw, _, remaining = buffer.partition(b"\n")
            buffer[:] = remaining
            self._process_line(socket, raw)

    def _process_line(self, socket, raw: bytes) -> None:
        try:
            message = json.loads(raw.decode("utf-8"))
            if message.get("version") != PROTOCOL_VERSION:
                raise ValueError("unsupported protocol version")
            if not hmac.compare_digest(str(message.get("token", "")), self.token):
                raise ValueError("authentication failed")
            if message.get("type") != "diagnostic":
                raise ValueError("unsupported message type")
            payload = message.get("payload")
            if not isinstance(payload, dict):
                raise ValueError("diagnostic payload must be an object")
            self.diagnostic_received.emit(payload)
            socket.write(b'{"ok":true}\n')
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            self.protocol_error.emit(str(exc))
            socket.write(b'{"ok":false}\n')
