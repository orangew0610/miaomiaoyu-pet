"""Opt-in real-model smoke test for cross-session memory.

This script uses a temporary SQLite database and the API credential already
stored by ConfigService. It never persists the synthetic test fact or key in
the application's normal memory database.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from debugpet.services.api import ModelApiClient
from debugpet.services.config import ConfigService
from debugpet.services.memory import SQLiteMemoryService


def main() -> int:
    config_service = ConfigService()
    config = config_service.load()
    api_key = config_service.get_api_key(config.provider)
    if not api_key:
        raise RuntimeError(f"missing credential for provider {config.provider!r}")

    fact = "海星7421"
    character_id = "real-model-smoke"
    first_question = f"请记住：我的测试代号是{fact}。只需确认你记住了。"
    second_question = "我的测试代号是什么？只回答代号。"
    character_prompt = "你是 DebugPet。只使用提供的真实记忆作答，不要编造。"

    with tempfile.TemporaryDirectory(
        prefix="debugpet-memory-smoke-", ignore_cleanup_errors=True
    ) as temp_dir:
        database_path = Path(temp_dir) / "memory.sqlite3"
        first_service = SQLiteMemoryService(database_path)
        first_session = first_service.new_session_id()
        first_service.add_message(character_id, first_session, "user", first_question)

        first_context = first_service.build_context(
            character_id, first_question, character_prompt, budget_tokens=1200
        )
        client = ModelApiClient(config, api_key)
        first_reply = client.chat(first_context.system_prompt, first_context.messages).reply
        first_service.add_message(character_id, first_session, "assistant", first_reply)

        # A new service object and session simulate closing and reopening chat.
        second_service = SQLiteMemoryService(database_path)
        second_session = second_service.new_session_id()
        second_service.add_message(character_id, second_session, "user", second_question)
        second_context = second_service.build_context(
            character_id, second_question, character_prompt, budget_tokens=1200
        )
        second_reply = client.chat(second_context.system_prompt, second_context.messages).reply

        remembered = fact in second_reply
        print(f"provider={config.provider}")
        print(f"model={config.model}")
        print(f"cross_session_memory={remembered}")
        print(f"injected_memory_count={len(second_context.injected_memory_ids)}")
        return 0 if remembered else 1


if __name__ == "__main__":
    raise SystemExit(main())
