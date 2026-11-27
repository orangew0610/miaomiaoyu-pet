import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication

import debug_pet_pyqt
from debugpet.services.config import ModelConfig


class FakeConfigService:
    instance = None

    def __init__(self):
        type(self).instance = self
        self.keys = {"deepseek": "deepseek-saved", "glm": "glm-saved"}
        self.saved_keys = {}
        self.saved_config = None

    def load(self):
        return ModelConfig(
            provider="glm",
            api_url="https://open.bigmodel.cn/api/paas/v4/chat/completions",
            model="glm-4-flash",
        )

    def get_api_key(self, provider):
        return self.keys.get(provider, "")

    def set_api_key(self, provider, api_key):
        self.saved_keys[provider] = api_key

    def save(self, config):
        self.saved_config = config


def test_switching_provider_restores_each_key_and_saves_both(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(debug_pet_pyqt, "ConfigService", FakeConfigService)
    monkeypatch.setattr(debug_pet_pyqt, "is_startup_enabled", lambda: False)
    startup_changes = []
    monkeypatch.setattr(
        debug_pet_pyqt, "set_startup_enabled", startup_changes.append
    )
    dialog = debug_pet_pyqt.SettingsDialog()

    assert dialog.api_key_input.text() == "glm-saved"
    dialog.api_key_input.setText("glm-edited")

    dialog.service_combo.setCurrentText("DeepSeek")
    assert dialog.api_key_input.text() == "deepseek-saved"
    dialog.api_key_input.setText("deepseek-edited")

    dialog.service_combo.setCurrentText("GLM-4.7-Flash")
    assert dialog.api_key_input.text() == "glm-edited"
    dialog._save_settings()

    service = FakeConfigService.instance
    assert service.saved_keys == {
        "deepseek": "deepseek-edited",
        "glm": "glm-edited",
    }
    assert service.saved_config.provider == "glm"
    assert startup_changes == [False]
    app.processEvents()
