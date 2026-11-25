from pathlib import Path


def test_application_uses_one_native_pixel_coordinate_system() -> None:
    source = Path("debug_pet_pyqt.py").read_text(encoding="utf-8")
    main_source = source[source.index("def main():") :]

    create_app = main_source.index("app = QApplication(sys.argv)")
    enable_native_dpi = main_source.index("enable_per_monitor_dpi_awareness()")

    assert enable_native_dpi < create_app
    assert "Qt.AA_EnableHighDpiScaling" not in main_source


def test_application_rejects_a_second_pet_process() -> None:
    source = Path("debug_pet_pyqt.py").read_text(encoding="utf-8")
    main_source = source[source.index("def main():") :]

    assert "QLockFile" in source
    assert "DebugPet-v2-single-instance.lock" in main_source
    assert "if not instance_lock.tryLock(0):" in main_source


def test_pet_uses_fixed_native_pixel_size_without_screen_resize_loop() -> None:
    source = Path("debug_pet_pyqt.py").read_text(encoding="utf-8")

    assert "self.pet_physical_width = 300" in source
    assert "self.pet_physical_height = 300" in source
    assert "self.pet_width = self.pet_physical_width" in source
    assert "self.pet_height = self.pet_physical_height" in source
    assert "self.setFixedSize(self.pet_width, self.pet_height)" in source
    assert "self.pet_label.setFixedSize(self.pet_width, self.pet_height)" in source
    assert "screenChanged.connect" not in source


def test_pet_moves_through_one_native_geometry_gateway() -> None:
    source = Path("debug_pet_pyqt.py").read_text(encoding="utf-8")

    assert "def _place_pet_window(self, x, y):" in source
    assert "ctypes.windll.user32.SetWindowPos(" in source
    # One pre-show placement and one implementation call are the only direct
    # QWidget.move usages; animation, dragging and arrival use the gateway.
    assert source.count("self.move(") == 2


def test_frames_and_small_ui_use_physical_pixel_targets() -> None:
    source = Path("debug_pet_pyqt.py").read_text(encoding="utf-8")

    assert "self.idle_movies.append((gif_name, frames))" in source
    assert "font_size = self._physical_px(24, screen)" in source
    assert "font_size = self._physical_px(22, screen)" in source
    assert "QFontMetrics(text_font)" in source
    assert "max_text_width = self._physical_px(420, screen)" in source
    assert "pet_x, pet_y = self.x(), self.y()" in source


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


def test_bubble_measures_text_at_the_same_width_it_assigns() -> None:
    source = Path("debug_pet_pyqt.py").read_text(encoding="utf-8")

    assert "QRect(0, 0, label_width, 10000)" in source
    assert "self.bubble_label.setFixedSize(label_width, label_height)" in source
    assert "text_rect.width() + 8" not in source
    assert "cloud_pad_x = self._physical_px(70, screen)" in source
    assert "QTimer.singleShot(0, self._stabilize_bubble_geometry)" in source
