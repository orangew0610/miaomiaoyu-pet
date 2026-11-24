from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

import keyring


APP_ID = "DebugPet"
KEYRING_SERVICE = "DebugPet.ModelService"


def default_config_dir() -> Path:
    root = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
    return Path(root) / APP_ID if root else Path.home() / ".debugpet"


@dataclass(slots=True)
class ModelConfig:
    provider: str = "deepseek"
    api_url: str = "https://api.deepseek.com/chat/completions"
    model: str = "deepseek-chat"
    ai_enabled: bool = False
    allow_code_upload: bool = False
    timeout_seconds: int = 30


class ConfigService:
    """Store non-secret settings as JSON and credentials in the OS keyring."""

    def __init__(self, config_dir: Path | None = None) -> None:
        self.config_dir = config_dir or default_config_dir()
        self.config_path = self.config_dir / "config.json"

    def load(self) -> ModelConfig:
        config = ModelConfig()
        if self.config_path.exists():
            try:
                values = json.loads(self.config_path.read_text(encoding="utf-8"))
                allowed = ModelConfig.__dataclass_fields__.keys()
                config = ModelConfig(**{k: v for k, v in values.items() if k in allowed})
            except (OSError, ValueError, TypeError):
                pass

        # Read-only compatibility with the 1.x environment variables.
        config.api_url = os.environ.get("API_URL", config.api_url)
        config.model = os.environ.get("AI_MODEL", config.model)
        return config

    def save(self, config: ModelConfig) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        temporary = self.config_path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(asdict(config), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.config_path)

    def get_api_key(self, provider: str) -> str:
        try:
            return keyring.get_password(KEYRING_SERVICE, provider) or ""
        except keyring.errors.KeyringError:
            env_name = f"{provider.upper()}_API_KEY"
            return os.environ.get(env_name, "")

    def set_api_key(self, provider: str, api_key: str) -> None:
        try:
            if api_key:
                keyring.set_password(KEYRING_SERVICE, provider, api_key)
            else:
                keyring.delete_password(KEYRING_SERVICE, provider)
        except keyring.errors.PasswordDeleteError:
            return
