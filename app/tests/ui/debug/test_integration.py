"""main 接入 + dev_panel 按钮集成测试。"""

from __future__ import annotations

import os
from unittest import mock


class TestMainAutoInstall:
    """启动时 env var 控制 install_event_logger 行为。"""

    def setup_method(self) -> None:
        from app.ui.components.pixel_button import PixelButton
        from kivy.uix.modalview import ModalView
        from kivy.uix.textinput import TextInput
        from app.ui.debug import event_logger

        self._orig = (
            PixelButton.on_touch_down,
            ModalView.open,
            ModalView.dismiss,
            TextInput.__init__,
        )
        event_logger._INSTALLED = False

    def teardown_method(self) -> None:
        from app.ui.components.pixel_button import PixelButton
        from kivy.uix.modalview import ModalView
        from kivy.uix.textinput import TextInput
        from app.ui.debug import event_logger

        (
            PixelButton.on_touch_down,
            ModalView.open,
            ModalView.dismiss,
            TextInput.__init__,
        ) = self._orig
        event_logger._INSTALLED = False

    def test_main_calls_install_when_debug_env_set(self) -> None:
        """SOLOIST_DEBUG=1 时, _setup_debug_hooks 后 _INSTALLED 应为 True."""
        from app.ui.debug import event_logger
        from app.main import _setup_debug_hooks

        with mock.patch.dict(os.environ, {"SOLOIST_DEBUG": "1"}):
            _setup_debug_hooks()

        assert event_logger._INSTALLED is True

    def test_main_skips_install_when_debug_env_unset(self) -> None:
        """SOLOIST_DEBUG 未设时, _INSTALLED 应保持 False."""
        from app.ui.debug import event_logger
        from app.main import _setup_debug_hooks

        with mock.patch.dict(os.environ, {"SOLOIST_DEBUG": "0"}, clear=False):
            _setup_debug_hooks()

        assert event_logger._INSTALLED is False
