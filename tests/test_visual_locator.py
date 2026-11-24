from PIL import Image, ImageDraw

from debugpet.services.visual_locator import locate_marker_in_image


def test_marker_maps_image_pixels_to_screen_coordinates() -> None:
    image = Image.new("RGB", (300, 200), "#202020")
    draw = ImageDraw.Draw(image)
    draw.rectangle((100, 80, 180, 96), outline="#ff00fe", width=2)

    target = locate_marker_in_image(image, screen_left=-1920, screen_top=120)

    assert target is not None
    assert -1820 <= target.x <= -1740
    assert 200 <= target.y <= 216
    assert target.pixel_count >= 6


def test_marker_locator_rejects_unmarked_image() -> None:
    image = Image.new("RGB", (100, 100), "#202020")
    assert locate_marker_in_image(image) is None
