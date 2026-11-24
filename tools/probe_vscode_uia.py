#!/usr/bin/env python3
"""Probe VSCode UI Automation exposure without changing editor state."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from pywinauto import Desktop


def main() -> int:
    report: dict[str, object] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "backend": "uia",
        "windows": [],
    }
    windows = []
    for window in Desktop(backend="uia").windows():
        title = window.window_text()
        if "Visual Studio Code" not in title:
            continue
        descendants = []
        for control in window.descendants():
            control_type = control.element_info.control_type
            if control_type not in {"Document", "Edit", "Text"}:
                continue
            rectangle = control.rectangle()
            descendants.append(
                {
                    "control_type": control_type,
                    "name": control.window_text()[:120],
                    "rectangle": [
                        rectangle.left,
                        rectangle.top,
                        rectangle.right,
                        rectangle.bottom,
                    ],
                }
            )
        rectangle = window.rectangle()
        windows.append(
            {
                "title": title,
                "rectangle": [rectangle.left, rectangle.top, rectangle.right, rectangle.bottom],
                "text_controls": descendants,
            }
        )
    report["windows"] = windows
    report["precise_text_rectangles_available"] = any(
        item["text_controls"] for item in windows
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if windows else 2


if __name__ == "__main__":
    raise SystemExit(main())
