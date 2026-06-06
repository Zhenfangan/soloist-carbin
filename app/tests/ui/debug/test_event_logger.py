"""event_logger 单元测试 — 验证 env var gate + 幂等 install。"""

from __future__ import annotations

import os
from unittest import mock


class TestInstallEventLogger:
    """验证 install_event_logger 的开关 + 幂等行为。"""

    def setup_method(self) -> None:
        """每个测试前 reset _INSTALLED 状态 + 快照原方法。"""
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
        """每个测试后恢复原方法, 防止 monkey-patch 污染后续测试。"""
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

    def test_no_install_without_env_var(self) -> None:
        """SOLOIST_DEBUG != 1 时, install 不做任何事。"""
        from app.ui.debug.event_logger import install_event_logger

        with mock.patch.dict(os.environ, {"SOLOIST_DEBUG": "0"}, clear=False):
            installed = install_event_logger()

        assert installed is False, "未设置 SOLOIST_DEBUG=1 时不应安装"

    def test_install_with_env_var(self) -> None:
        """SOLOIST_DEBUG=1 时, install 成功返回 True。"""
        from app.ui.debug.event_logger import install_event_logger

        with mock.patch.dict(os.environ, {"SOLOIST_DEBUG": "1"}):
            installed = install_event_logger()

        assert installed is True, "设置 SOLOIST_DEBUG=1 时应安装成功"

    def test_install_is_idempotent(self) -> None:
        """重复调用 install 不重复装饰。"""
        from app.ui.debug.event_logger import install_event_logger

        with mock.patch.dict(os.environ, {"SOLOIST_DEBUG": "1"}):
            first = install_event_logger()
            second = install_event_logger()

        assert first is True
        assert second is False, "第二次 install 应返回 False (已安装)"

    def test_install_wraps_pixel_button_on_touch_down(self) -> None:
        """安装后 PixelButton.on_touch_down 被装饰。"""
        from app.ui.components.pixel_button import PixelButton
        from app.ui.debug.event_logger import install_event_logger

        original = PixelButton.on_touch_down

        with mock.patch.dict(os.environ, {"SOLOIST_DEBUG": "1"}):
            install_event_logger()

        assert PixelButton.on_touch_down is not original, (
            "PixelButton.on_touch_down 应被装饰替换"
        )

    def test_install_wraps_modal_view_open(self) -> None:
        """安装后 ModalView.open 被装饰。"""
        from kivy.uix.modalview import ModalView
        from app.ui.debug.event_logger import install_event_logger

        original = ModalView.open

        with mock.patch.dict(os.environ, {"SOLOIST_DEBUG": "1"}):
            install_event_logger()

        assert ModalView.open is not original, "ModalView.open 应被装饰替换"
