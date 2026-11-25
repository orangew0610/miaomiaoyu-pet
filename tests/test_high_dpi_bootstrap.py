from pathlib import Path


def test_application_uses_one_native_pixel_coordinate_system() -> None:
    source = Path("debug_pet_pyqt.py").read_text(encoding="utf-8")
    main_source = source[source.index("def main():") :]

    create_app = main_source.index("app = QApplication(sys.argv)")
    enable_native_dpi = main_source.index("enable_per_monitor_dpi_awareness()")

    assert enable_native_dpi < create_app
    assert "Qt.AA_EnableHighDpiScaling" not in main_source


def test_pet_uses_fixed_native_pixel_size_without_screen_resize_loop() -> None:
    source = Path("debug_pet_pyqt.py").read_text(encoding="utf-8")

    assert "self.pet_physical_width = 300" in source
    assert "self.pet_physical_height = 300" in source
    assert "self.pet_width = self.pet_physical_width" in source
    assert "self.pet_height = self.pet_physical_height" in source
    assert "self.setFixedSize(self.pet_width, self.pet_height)" in source
    assert "self.pet_label.setFixedSize(self.pet_width, self.pet_height)" in source
    assert "screenChanged.connect" not in source


def test_frames_and_small_ui_use_physical_pixel_targets() -> None:
    source = Path("debug_pet_pyqt.py").read_text(encoding="utf-8")

    assert "self.idle_movies.append((gif_name, frames))" in source
    assert "font_size = self._physical_px(24, screen)" in source
    assert "font_size = self._physical_px(22, screen)" in source
    assert "self.bubble_label.setMaximumWidth(self._physical_px(460, screen))" in source


def test_motion_callbacks_are_bound_to_a_generation_token() -> None:
    source = Path("debug_pet_pyqt.py").read_text(encoding="utf-8")

    assert "def _begin_motion(self, mode):" in source
    assert "token != self._motion_token" in source
    assert "self._motion_mode != 'walk'" in source
    assert "self._motion_mode != 'jump'" in source
    assert "self._motion_mode != 'parabola'" in source
    assert "lambda current=token: self._move_step(current)" in source


def test_cloud_bubble_has_state_background_and_float_animation() -> None:
    source = Path("debug_pet_pyqt.py").read_text(encoding="utf-8")

    assert "class CloudBubbleWindow(QWidget):" in source
    assert "STATE_BUBBLE_BACKGROUNDS" in source
    assert "math.sin(self._bubble_float_phase) * 3" in source
