from __future__ import annotations

import ctypes
from ctypes import wintypes


def find_vscode_anchor() -> tuple[int, int] | None:
    """Return a safe desktop-pet target near a visible VSCode window edge."""

    if not hasattr(ctypes, "windll"):
        return None
    user32 = ctypes.windll.user32
    candidates: list[tuple[int, int, int, int]] = []

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
            candidates.append((rect.left, rect.top, rect.right, rect.bottom))
        return True

    user32.EnumWindows(callback, 0)
    if not candidates:
        return None
    left, top, right, bottom = max(
        candidates,
        key=lambda rect: max(0, rect[2] - rect[0]) * max(0, rect[3] - rect[1]),
    )
    return max(left, right - 320), max(top, bottom - 340)
