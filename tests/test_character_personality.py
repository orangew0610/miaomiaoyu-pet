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


def test_daily_scene_keeps_warmth_and_uses_real_memory():
    instruction = ChatDialog._scene_instruction("日常闲聊")

    assert "先直接回答" in instruction
    assert "不耐烦" in instruction
    assert "真实记忆" in instruction


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


def test_character_prompt_anchors_self_aliases_and_user_facts():
    prompt = (ROOT / "yu.md").read_text(encoding="utf-8")

    for alias in ("小鱼", "祁老师", "大画家", "祁煜"):
        assert alias in prompt
    assert "默认都是在叫你" in prompt
    assert "不能据此推断用户的专业" in prompt
    assert "以本节为准" in prompt


def test_character_prompt_distinguishes_user_from_distant_outsiders():
    prompt = (ROOT / "yu.md").read_text(encoding="utf-8")

    assert "用户是你熟悉且在意的亲密对象" in prompt
    assert "这一态度不适用于作为亲密对象的用户" in prompt
    assert "普通提问不得无故挖苦" in prompt
