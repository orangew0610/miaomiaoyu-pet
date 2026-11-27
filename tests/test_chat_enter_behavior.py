import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

from debug_pet_pyqt import ChatDialog


class ProbeChatDialog(ChatDialog):
    def _restore_memory_async(self):
        self.sent_count = 0
        self.memory_open_count = 0

    def _send_message(self):
        self.sent_count += 1

    def _show_memory_manager(self):
        self.memory_open_count += 1


def test_enter_sends_without_opening_memory_manager():
    app = QApplication.instance() or QApplication([])
    dialog = ProbeChatDialog()
    dialog.send_btn.setEnabled(True)
    dialog.memory_button.setEnabled(True)
    dialog.input_text.setText("测试发送")
    dialog.input_text.setFocus()

    QTest.keyClick(dialog.input_text, Qt.Key_Return)
    app.processEvents()

    assert dialog.sent_count == 1
    assert dialog.memory_open_count == 0
    dialog.close()


def test_reset_clears_visible_chat_immediately():
    app = QApplication.instance() or QApplication([])
    dialog = ProbeChatDialog()
    old_session = dialog.session_id
    dialog.message_history = [{"role": "user", "content": "旧对话"}]
    dialog.chat_history.append(dialog._make_user_bubble("旧对话"))

    dialog._reset_to_empty_session()

    assert dialog.session_id != old_session
    assert dialog.message_history == []
    assert "旧对话" not in dialog.chat_history.toPlainText()
    assert "重新开始" in dialog.chat_history.toPlainText()
    app.processEvents()
    dialog.close()
