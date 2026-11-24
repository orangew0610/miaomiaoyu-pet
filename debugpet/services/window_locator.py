from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WindowRect:
    left: int
    top: int
    right: int
    bottom: int
    title: str
    hwnd: int = 0

    @property
    def width(self) -> int:
        return max(0, self.right - self.left)

    @property
    def height(self) -> int:
        return max(0, self.bottom - self.top)


def enable_per_monitor_dpi_awareness() -> bool:
    """Opt the process into per-monitor-v2 coordinates before QApplication."""
    if not hasattr(ctypes, "windll"):
        return False
    try:
        # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 == (HANDLE)-4
        return bool(ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)))
    except (AttributeError, OSError):
        return False


def list_vscode_windows() -> list[WindowRect]:
    if not hasattr(ctypes, "windll"):
        return []
    user32 = ctypes.windll.user32
    candidates: list[WindowRect] = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def callback(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if not length:
            return True
        title = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, title, length + 1)
        if "Visual Studio Code" not in title.value:
            return True
        rect = wintypes.RECT()
        if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            item = WindowRect(
                rect.left, rect.top, rect.right, rect.bottom, title.value, int(hwnd)
            )
            if item.width > 0 and item.height > 0:
                candidates.append(item)
        return True

    user32.EnumWindows(callback, 0)
    return candidates


def find_vscode_window(document_name: str | None = None) -> WindowRect | None:
    windows = list_vscode_windows()
    if document_name:
        lowered = document_name.lower()
        matches = [item for item in windows if lowered in item.title.lower()]
        if matches:
            windows = matches
    if not windows:
        return None
    return max(windows, key=lambda item: item.width * item.height)


def is_foreground_window(window: WindowRect) -> bool:
    if not window.hwnd or not hasattr(ctypes, "windll"):
        return False
    return int(ctypes.windll.user32.GetForegroundWindow()) == window.hwnd


def find_vscode_anchor(document_name: str | None = None) -> tuple[int, int] | None:
    window = find_vscode_window(document_name)
    if not window:
        return None
    return max(window.left, window.right - 320), max(window.top, window.bottom - 340)
