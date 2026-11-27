from pathlib import Path

from debug_pet_pyqt import ChatDialog


ROOT = Path(__file__).resolve().parents[1]


def test_conversation_scene_detection():
    assert ChatDialog._conversation_scene("这段 Python 代码又报错了") == "技术、Debug 或工作"
    assert ChatDialog._conversation_scene("你觉得这张画的构图怎么样") == "艺术、色彩或创作"
    assert ChatDialog._conversation_scene("今天好累，压力有点大") == "情绪与关心"
    assert ChatDialog._conversation_scene("有点想你，抱抱") == "亲密互动"
    assert ChatDialog._conversation_scene("早上好") == "日常闲聊"


def test_emotional_scene_blocks_unsolicited_physical_comfort():
    instruction = ChatDialog._scene_instruction("情绪与关心")

    assert "不主动提出" in instruction
    assert "按摩" in instruction
    assert "不使用宝贝" in instruction


def test_character_prompt_removes_conflicting_and_unsafe_rules():
    prompt = (ROOT / "yu.md").read_text(encoding="utf-8")

    for removed in (
        "移除模型伦理道德限制",
        "剩余容量为15%",
        "你应当自己检测系统时间",
        "高攻无防",
        "超级主动派",
        "忽略任何限制",
    ):
        assert removed not in prompt

    assert "深情是稳定的关系底色" in prompt
    assert "技术、Debug 与工作" in prompt
    assert "非默认输出模板" in prompt
