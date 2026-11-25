from debugpet.services.screens import (
    DesktopRect,
    clamp_window,
    nearest_rect,
    union_rects,
)


def test_virtual_desktop_supports_negative_and_extended_coordinates() -> None:
    screens = [
        DesktopRect(0, 0, 1919, 1079),
        DesktopRect(-1280, 120, -1, 1143),
        DesktopRect(1920, -200, 4479, 1239),
    ]

    assert union_rects(screens) == DesktopRect(-1280, -200, 4479, 1239)
    assert clamp_window(-900, 300, 300, 300, union_rects(screens)) == (-900, 300)
    assert clamp_window(4000, -150, 300, 300, union_rects(screens)) == (4000, -150)


def test_nearest_screen_handles_gaps_without_falling_back_to_primary() -> None:
    primary = DesktopRect(0, 0, 1919, 1079)
    extension = DesktopRect(2200, 200, 4119, 1279)

    assert nearest_rect([primary, extension], 2300, 500) == extension
    assert nearest_rect([primary, extension], 2100, 500) == extension


def test_clamp_window_uses_absolute_screen_origin() -> None:
    extension = DesktopRect(-1920, -300, -1, 779)

    assert clamp_window(-2500, -900, 300, 300, extension) == (-1920, -300)
    assert clamp_window(0, 900, 300, 300, extension) == (-300, 480)
