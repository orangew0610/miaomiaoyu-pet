from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True, slots=True)
class DesktopRect:
    left: int
    top: int
    right: int
    bottom: int

    def contains(self, x: int, y: int) -> bool:
        return self.left <= x <= self.right and self.top <= y <= self.bottom


def union_rects(rectangles: Iterable[DesktopRect]) -> DesktopRect | None:
    items = list(rectangles)
    if not items:
        return None
    return DesktopRect(
        min(item.left for item in items),
        min(item.top for item in items),
        max(item.right for item in items),
        max(item.bottom for item in items),
    )


def nearest_rect(
    rectangles: Iterable[DesktopRect], x: int, y: int
) -> DesktopRect | None:
    items = list(rectangles)
    if not items:
        return None
    for item in items:
        if item.contains(x, y):
            return item

    def squared_distance(item: DesktopRect) -> int:
        dx = max(item.left - x, 0, x - item.right)
        dy = max(item.top - y, 0, y - item.bottom)
        return dx * dx + dy * dy

    return min(items, key=squared_distance)


def clamp_window(
    x: float, y: float, width: int, height: int, bounds: DesktopRect
) -> tuple[int, int]:
    max_x = max(bounds.left, bounds.right - width + 1)
    max_y = max(bounds.top, bounds.bottom - height + 1)
    return (
        int(max(bounds.left, min(x, max_x))),
        int(max(bounds.top, min(y, max_y))),
    )
