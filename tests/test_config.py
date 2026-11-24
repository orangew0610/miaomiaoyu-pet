import json

from debugpet.services.config import ConfigService, ModelConfig


def test_non_secret_config_round_trip(tmp_path) -> None:
    service = ConfigService(tmp_path)
    expected = ModelConfig(
        provider="custom",
        api_url="http://127.0.0.1:8080/v1/chat/completions",
        model="local-model",
        ai_enabled=True,
        allow_code_upload=False,
    )
    service.save(expected)

    assert service.load() == expected
    persisted = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert "api_key" not in persisted
