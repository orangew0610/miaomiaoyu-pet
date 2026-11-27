import sys
from types import SimpleNamespace

import debugpet.services.config as config


class FakeKey:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def fake_winreg():
    values = {}

    def query(_key, name):
        if name not in values:
            raise FileNotFoundError
        return values[name], 1

    def delete(_key, name):
        if name not in values:
            raise FileNotFoundError
        del values[name]

    module = SimpleNamespace(
        HKEY_CURRENT_USER=object(), REG_SZ=1, values=values,
        OpenKey=lambda *_args: FakeKey(), CreateKey=lambda *_args: FakeKey(),
        QueryValueEx=query,
        SetValueEx=lambda _key, name, _reserved, _kind, value: values.__setitem__(name, value),
        DeleteValue=delete,
    )
    return module


def test_windows_startup_switch_writes_and_removes_current_user_entry(monkeypatch):
    registry = fake_winreg()
    monkeypatch.setitem(sys.modules, "winreg", registry)
    monkeypatch.setattr(config.sys, "platform", "win32")
    monkeypatch.setattr(config.sys, "frozen", True, raising=False)
    monkeypatch.setattr(config.sys, "executable", r"D:\Apps\DebugPet.exe")

    assert not config.is_startup_enabled()
    config.set_startup_enabled(True)
    assert config.is_startup_enabled()
    assert registry.values[config.STARTUP_VALUE_NAME] == '"D:\\Apps\\DebugPet.exe"'

    config.set_startup_enabled(False)
    assert not config.is_startup_enabled()
