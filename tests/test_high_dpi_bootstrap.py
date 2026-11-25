from pathlib import Path


def test_high_dpi_attributes_are_set_before_qapplication() -> None:
    source = Path("debug_pet_pyqt.py").read_text(encoding="utf-8")
    main_source = source[source.index("def main():") :]

    create_app = main_source.index("app = QApplication(sys.argv)")
    enable_scaling = main_source.index("Qt.AA_EnableHighDpiScaling")
    enable_pixmaps = main_source.index("Qt.AA_UseHighDpiPixmaps")

    assert enable_scaling < create_app
    assert enable_pixmaps < create_app


def test_pet_restores_fixed_logical_size_after_screen_change() -> None:
    source = Path("debug_pet_pyqt.py").read_text(encoding="utf-8")

    assert "self.pet_physical_width = 300" in source
    assert "self.pet_physical_height = 300" in source
    assert "round(self.pet_physical_width / initial_dpr)" in source
    assert "round(self.pet_physical_width / dpr)" in source
    assert "self.setFixedSize(self.pet_width, self.pet_height)" in source
    assert "self.pet_label.setFixedSize(self.pet_width, self.pet_height)" in source
    assert "handle.screenChanged.connect(self._on_screen_changed)" in source


def test_frames_and_small_ui_use_physical_pixel_targets() -> None:
    source = Path("debug_pet_pyqt.py").read_text(encoding="utf-8")

    assert "rendered.setDevicePixelRatio" in source
    assert "self.idle_movies.append((gif_name, frames))" in source
    assert "font_size = self._physical_px(24, screen)" in source
    assert "font_size = self._physical_px(22, screen)" in source
    assert "self.bubble_label.setMaximumWidth(self._physical_px(520, screen))" in source
