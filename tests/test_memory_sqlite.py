import shutil

import pytest

from debugpet.services.memory import SQLiteMemoryService


def test_messages_persist_across_service_instances(tmp_path) -> None:
    database = tmp_path / "memory.sqlite3"
    first = SQLiteMemoryService(database)
    session = first.new_session_id()
    first.add_message("miaomiao", session, "user", "我喜欢海边散步")
    first.add_message("miaomiao", session, "assistant", "我记住了")

    reopened = SQLiteMemoryService(database)
    restored = reopened.recent_messages("miaomiao")

    assert [item.content for item in restored] == ["我喜欢海边散步", "我记住了"]
    assert {item.session_id for item in restored} == {session}
    assert all(item.created_at for item in restored)


def test_messages_share_a_session_until_a_new_save_is_created(tmp_path) -> None:
    database = tmp_path / "memory.sqlite3"
    service = SQLiteMemoryService(database)
    service.add_message("miaomiao", "save-one", "user", "今天看到了海鸥")
    service.add_message("miaomiao", "save-one", "assistant", "下次带我一起去。")

    assert [item.content for item in service.recent_messages(
        "miaomiao", session_id="save-one"
    )] == [
        "今天看到了海鸥", "下次带我一起去。",
    ]
    assert service.latest_session_id("miaomiao") == "save-one"
    sessions = service.list_conversation_sessions("miaomiao")
    assert len(sessions) == 1
    assert sessions[0]["message_count"] == 2

    service.add_message("miaomiao", "save-two", "user", "这是新存档")
    assert service.latest_session_id("miaomiao") == "save-two"
    assert [item.content for item in service.recent_messages(
        "miaomiao", session_id="save-two"
    )] == ["这是新存档"]
    assert len(service.list_conversation_sessions("miaomiao")) == 2


def test_one_conversation_save_can_be_deleted_without_affecting_others(tmp_path) -> None:
    service = SQLiteMemoryService(tmp_path / "memory.sqlite3")
    service.add_message("miaomiao", "save-one", "user", "保留我")
    service.add_message("miaomiao", "save-two", "user", "删除我")
    scoped = service.add_user_memory(
        "miaomiao", "跟随存档删除", "episodic", session_id="save-two"
    )

    assert service.delete_conversation_session("miaomiao", "save-two") == 2
    assert service.recent_messages("miaomiao", session_id="save-two") == []
    assert [entry.content for entry in service.recent_messages(
        "miaomiao", session_id="save-one"
    )] == ["保留我"]
    assert scoped.id not in {
        entry.id for entry in service.list_entries("miaomiao")
    }
    assert [item["session_id"] for item in service.list_conversation_sessions(
        "miaomiao"
    )] == ["save-one"]


def test_scoped_long_term_memory_is_only_injected_into_its_save(tmp_path) -> None:
    service = SQLiteMemoryService(tmp_path / "memory.sqlite3")
    general = service.add_user_memory(
        "miaomiao", "通用喜欢海边", "preference"
    )
    scoped = service.add_user_memory(
        "miaomiao", "只在存档一喜欢草莓", "preference", session_id="save-one"
    )

    save_one = service.build_context(
        "miaomiao", "我喜欢什么", "角色", session_id="save-one"
    )
    save_two = service.build_context(
        "miaomiao", "我喜欢什么", "角色", session_id="save-two"
    )

    assert general.id in save_one.injected_memory_ids
    assert general.id in save_two.injected_memory_ids
    assert scoped.id in save_one.injected_memory_ids
    assert scoped.id not in save_two.injected_memory_ids
    assert service.latest_session_id("miaomiao") == "save-one"


def test_character_memories_are_isolated(tmp_path) -> None:
    service = SQLiteMemoryService(tmp_path / "memory.sqlite3")
    service.add_message("miaomiao", "one", "user", "只属于喵喵鱼的秘密")
    service.add_message("another", "two", "user", "另一个角色的秘密")

    assert [entry.content for entry in service.search("miaomiao", "秘密")] == ["只属于喵喵鱼的秘密"]
    assert [entry.content for entry in service.search("another", "秘密")] == ["另一个角色的秘密"]


def test_fts_or_like_retrieval_and_deleted_memory_exclusion(tmp_path) -> None:
    service = SQLiteMemoryService(tmp_path / "memory.sqlite3")
    entry = service.add_user_memory("miaomiao", "用户最喜欢草莓冰淇淋", "preference")
    assert entry.id in {item.id for item in service.search("miaomiao", "草莓冰淇淋")}

    assert service.delete_entry(entry.id, "miaomiao")
    assert entry.id not in {item.id for item in service.search("miaomiao", "草莓冰淇淋")}
    context = service.build_context("miaomiao", "我喜欢什么冰淇淋", "角色设定")
    assert "草莓冰淇淋" not in context.system_prompt


def test_context_contains_recent_and_relevant_memory_with_budget(tmp_path) -> None:
    service = SQLiteMemoryService(tmp_path / "memory.sqlite3")
    service.add_user_memory("miaomiao", "用户偏好安静的海边", "preference")
    service.add_message("miaomiao", "old", "user", "去年我们聊过水母灯")
    service.add_message("miaomiao", "old", "assistant", "那盏灯是蓝色的")
    service.add_message("miaomiao", "new", "user", "今天心情不错")

    context = service.build_context("miaomiao", "还记得水母灯吗", "角色设定", budget_tokens=500)

    assert "用户偏好安静的海边" in context.system_prompt
    assert any("水母灯" in item["content"] for item in context.messages)
    assert context.estimated_tokens <= 500


def test_large_character_prompt_does_not_crowd_out_managed_memory(tmp_path) -> None:
    service = SQLiteMemoryService(tmp_path / "memory.sqlite3")
    memory = service.add_user_memory("miaomiao", "我想吃寿司", "preference")
    large_prompt = "人物设定" * 1800

    context = service.build_context(
        "miaomiao", "想吃我爱吃的", large_prompt, budget_tokens=8000,
        session_id="current-save",
    )

    assert memory.id in context.injected_memory_ids
    assert "我想吃寿司" in context.system_prompt
    assert context.estimated_tokens <= 8000
    assert context.injected_memory_ids


def test_extractive_summary_has_traceable_sources(tmp_path) -> None:
    service = SQLiteMemoryService(tmp_path / "memory.sqlite3")
    for index in range(40):
        service.add_message("miaomiao", "long", "user" if index % 2 == 0 else "assistant", f"真实消息 {index}")

    service.build_context("miaomiao", "真实消息", "角色设定", budget_tokens=1000)
    summaries = service.list_entries("miaomiao", kinds=("summary",))

    assert summaries
    summary = summaries[0]
    assert summary.source_ids
    assert all(f"[source:{source_id}]" in summary.content for source_id in summary.source_ids)
    assert "真实消息" in summary.content


def test_disable_memory_stops_storage_and_injection(tmp_path) -> None:
    service = SQLiteMemoryService(tmp_path / "memory.sqlite3")
    service.add_message("miaomiao", "before", "user", "开启时保存")
    service.set_enabled("miaomiao", False)
    disabled = service.add_message("miaomiao", "after", "user", "关闭后不保存")

    assert disabled.id == 0
    assert service.recent_messages("miaomiao") == []
    context = service.build_context("miaomiao", "当前问题", "角色设定")
    assert context.messages == ({"role": "user", "content": "当前问题"},)


def test_disabled_memory_rejects_managed_memory_instead_of_silent_success(tmp_path) -> None:
    service = SQLiteMemoryService(tmp_path / "memory.sqlite3")
    service.set_enabled("miaomiao", False)

    with pytest.raises(RuntimeError, match="记忆已关闭"):
        service.add_user_memory("miaomiao", "我喜欢海边", "preference")

    assert service.list_entries("miaomiao") == []


def test_deleting_summarized_source_invalidates_summary(tmp_path) -> None:
    service = SQLiteMemoryService(tmp_path / "memory.sqlite3")
    entries = []
    for index in range(40):
        entries.append(service.add_message(
            "miaomiao", "long", "user" if index % 2 == 0 else "assistant",
            f"可删除事实 {index}",
        ))
    service.build_context("miaomiao", "可删除事实", "角色设定", budget_tokens=1000)
    summary = service.list_entries("miaomiao", kinds=("summary",))[0]
    source_id = summary.source_ids[0]
    source = next(item for item in entries if item.id == source_id)

    assert service.delete_entry(source_id, "miaomiao")
    assert service.list_entries("miaomiao", kinds=("summary",)) == []
    context = service.build_context("miaomiao", source.content, "角色设定", budget_tokens=1000)
    assert source.content not in context.system_prompt


def test_database_connections_are_closed_after_operations(tmp_path) -> None:
    database_dir = tmp_path / "database"
    service = SQLiteMemoryService(database_dir / "memory.sqlite3")
    service.add_message("miaomiao", "session", "user", "temporary fact")
    service.recent_messages("miaomiao")

    # Windows refuses this removal when any SQLite handle is still open.
    shutil.rmtree(database_dir)
    assert not database_dir.exists()
