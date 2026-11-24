from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import requests

from .config import ModelConfig


Message = dict[str, str]


def build_chat_messages(
    system_prompt: str,
    history: Sequence[Message],
    *,
    history_limit: int = 30,
) -> list[Message]:
    """Build a request without silently duplicating the current user turn."""

    return [{"role": "system", "content": system_prompt}, *history[-history_limit:]]


@dataclass(slots=True)
class ChatResult:
    reply: str
    raw: dict[str, Any]


class ModelApiClient:
    def __init__(self, config: ModelConfig, api_key: str = "") -> None:
        self.config = config
        self.api_key = api_key

    def chat(self, system_prompt: str, history: Sequence[Message]) -> ChatResult:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {
            "model": self.config.model,
            "messages": build_chat_messages(system_prompt, history),
            "temperature": 0.7,
        }
        response = requests.post(
            self.config.api_url,
            headers=headers,
            json=payload,
            timeout=self.config.timeout_seconds,
        )
        response.raise_for_status()
        raw = response.json()
        reply = raw.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not reply:
            raise ValueError("model response did not contain a reply")
        return ChatResult(reply=reply, raw=raw)
