from __future__ import annotations

from dataclasses import dataclass

from PIL import Image, ImageGrab

from .window_locator import WindowRect, is_foreground_window


@dataclass(frozen=True, slots=True)
class LocatedTarget:
    x: int
    y: int
    confidence: float
    pixel_count: int
    method: str = "decoration-color"


def locate_marker_in_image(
    image: Image.Image,
    *,
    screen_left: int = 0,
    screen_top: int = 0,
    minimum_pixels: int = 6,
) -> LocatedTarget | None:
    """Locate the extension's #ff00fe border using deterministic RGB bounds."""

    rgb = image.convert("RGB")
    points: list[tuple[int, int]] = []
    for y in range(rgb.height):
        for x in range(rgb.width):
            red, green, blue = rgb.getpixel((x, y))
            if red >= 240 and green <= 35 and blue >= 225:
                points.append((x, y))
    if len(points) < minimum_pixels:
        return None

    # Use the densest horizontal band so an unrelated magenta icon elsewhere
    # in VSCode cannot drag the target toward a distant point.
    bands: dict[int, list[tuple[int, int]]] = {}
    for point in points:
        band = point[1] // 12
        bands.setdefault(band, []).append(point)
    selected = max(bands.values(), key=len)
    if len(selected) < minimum_pixels:
        return None
    left = min(point[0] for point in selected)
    right = max(point[0] for point in selected)
    top = min(point[1] for point in selected)
    bottom = max(point[1] for point in selected)
    density = min(1.0, len(selected) / max(1, (right - left + 1) * (bottom - top + 1)))
    return LocatedTarget(
        x=screen_left + (left + right) // 2,
        y=screen_top + (top + bottom) // 2,
        confidence=density,
        pixel_count=len(selected),
    )


def locate_vscode_decoration(window: WindowRect) -> LocatedTarget | None:
    # Electron returns black frames through PrintWindow when occluded. Never
    # focus the editor ourselves; wait until VSCode is already foreground.
    if window.hwnd and not is_foreground_window(window):
        return None
    image = ImageGrab.grab(
        bbox=(window.left, window.top, window.right, window.bottom),
        all_screens=True,
    )
    return locate_marker_in_image(
        image,
        screen_left=window.left,
        screen_top=window.top,
    )
