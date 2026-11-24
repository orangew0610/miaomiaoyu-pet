from debugpet.services.api import build_chat_messages


def test_current_user_message_is_not_duplicated() -> None:
    history = [{"role": "user", "content": "hello"}]

    messages = build_chat_messages("system", history)

    assert messages == [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "hello"},
    ]


def test_history_is_bounded() -> None:
    history = [{"role": "user", "content": str(index)} for index in range(40)]
    messages = build_chat_messages("system", history, history_limit=3)
    assert [item["content"] for item in messages] == ["system", "37", "38", "39"]
