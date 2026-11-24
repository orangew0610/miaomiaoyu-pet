from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PyQt5.QtCore import QThread, pyqtSignal


class ApiRequestWorker(QThread):
    """Run a blocking model call outside the Qt UI thread."""

    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, request: Callable[[], Any], parent=None) -> None:
        super().__init__(parent)
        self._request = request

    def run(self) -> None:
        try:
            self.succeeded.emit(self._request())
        except Exception as exc:  # surfaced to the UI; worker must not crash Qt
            self.failed.emit(str(exc))
