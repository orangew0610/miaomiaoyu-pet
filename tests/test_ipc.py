import json
import socket
import time

from PyQt5.QtCore import QCoreApplication

from debugpet.services.ipc import DiagnosticIpcServer


def test_authenticated_loopback_diagnostic(tmp_path) -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    server = DiagnosticIpcServer(tmp_path / "ipc.json")
    received = []
    server.diagnostic_received.connect(received.append)
    assert server.start()

    endpoint = json.loads((tmp_path / "ipc.json").read_text(encoding="utf-8"))
    message = {
        "version": 1,
        "token": endpoint["token"],
        "type": "diagnostic",
        "payload": {"uri": "file:///main.py", "version": 1},
    }
    client = socket.create_connection((endpoint["host"], endpoint["port"]), timeout=2)
    client.sendall(json.dumps(message).encode("utf-8") + b"\n")

    deadline = time.monotonic() + 2
    while not received and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)

    client.close()
    server.stop()
    assert received == [{"uri": "file:///main.py", "version": 1}]
