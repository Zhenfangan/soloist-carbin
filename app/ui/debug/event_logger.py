"""事件日志装饰器 — 装饰 PixelButton / ModalView / TextInput 关键方法。

启用方式: 设置环境变量 SOLOIST_DEBUG=1, app 启动时调 install_event_logger()。
默认 release 关闭, 无性能与日志噪音影响。

输出示例 (Kivy Logger.info):
    [EVT] PixelButton(text='+ 添加任务') touch_down at (210.0, 380.5) → hit
    [EVT] ModalView(AddTaskDialog).open() called
    [EVT] ModalView(AddTaskDialog) opened, pos=(20.0, 75.0), size=(380, 600)
    [EVT] TextInput focus=True, text=''
"""

from __future__ import annotations

import os
from typing import Any

from kivy.logger import Logger

_INSTALLED = False


def install_event_logger() -> bool:
    """全局安装事件日志拦截器。

    返回:
        True 表示安装成功 (env var SOLOIST_DEBUG=1 且首次调用)。
        False 表示未安装 (env var 未设或已经安装过)。
    """
    global _INSTALLED
    if _INSTALLED:
        return False
    if os.environ.get("SOLOIST_DEBUG", "0") != "1":
        return False

    _wrap_pixel_button()
    _wrap_modal_view()
    _wrap_text_input()

    _INSTALLED = True
    Logger.info("EventLogger: installed (PixelButton, ModalView, TextInput hooks active)")
    return True


def _wrap_pixel_button() -> None:
    """装饰 PixelButton.on_touch_down 记录 hit 事件。"""
    from app.ui.components.pixel_button import PixelButton

    original = PixelButton.on_touch_down

    def wrapped_on_touch_down(self: Any, touch: Any) -> bool:
        if not self.disabled and self.collide_point(*touch.pos):
            Logger.info(
                f"[EVT] PixelButton(text={self.text!r}) touch_down at {touch.pos} → hit"
            )
        return original(self, touch)

    PixelButton.on_touch_down = wrapped_on_touch_down  # type: ignore[method-assign]


def _wrap_modal_view() -> None:
    """装饰 ModalView.open / dismiss 记录显示/隐藏事件。"""
    from kivy.uix.modalview import ModalView

    original_open = ModalView.open

    def wrapped_open(self: Any, *args: Any, **kwargs: Any) -> Any:
        cls_name = type(self).__name__
        Logger.info(f"[EVT] ModalView({cls_name}).open() called")
        result = original_open(self, *args, **kwargs)
        parent_name = self.parent.__class__.__name__ if self.parent else "None"
        Logger.info(
            f"[EVT] ModalView({cls_name}) opened, "
            f"pos={self.pos}, size={self.size}, parent={parent_name}"
        )
        return result

    ModalView.open = wrapped_open  # type: ignore[method-assign]

    original_dismiss = ModalView.dismiss

    def wrapped_dismiss(self: Any, *args: Any, **kwargs: Any) -> Any:
        Logger.info(f"[EVT] ModalView({type(self).__name__}).dismiss() called")
        return original_dismiss(self, *args, **kwargs)

    ModalView.dismiss = wrapped_dismiss  # type: ignore[method-assign]


def _wrap_text_input() -> None:
    """装饰 TextInput.__init__ 添加 focus 变化监听。"""
    from kivy.uix.textinput import TextInput

    original_init = TextInput.__init__

    def wrapped_init(self: Any, *args: Any, **kwargs: Any) -> None:
        original_init(self, *args, **kwargs)
        self.fbind("focus", _on_text_input_focus)

    TextInput.__init__ = wrapped_init  # type: ignore[method-assign]


def _on_text_input_focus(instance: Any, value: bool) -> None:
    """TextInput focus 变化回调。"""
    Logger.info(f"[EVT] TextInput focus={value}, text={instance.text!r}")
