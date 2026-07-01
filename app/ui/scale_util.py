"""弹窗等比缩放工具。

真机窗口是原生分辨率, 弹窗(ModalView)内部卡片按 420x750 设计画布用固定像素,
在大屏上会显得很小。scale_wrap() 把卡片包进一个 ScatterLayout, 按屏幕等比缩放
(与主界面同一缩放比), 卡片在设计画布内居中, 触摸随缩放自动变换。桌面窗口即
420x750 时 scale=1, 无任何影响。
"""

from __future__ import annotations

from typing import Any

from kivy.core.window import Window
from kivy.uix.scatterlayout import ScatterLayout

from app.ui.tokens import LOGICAL_HEIGHT, LOGICAL_WIDTH


def scale_wrap(inner: Any) -> ScatterLayout:
    """把固定尺寸/居中定位的弹窗卡片包进按屏幕等比缩放的 ScatterLayout。

    Args:
        inner: 弹窗卡片 widget(通常 size_hint=(None,None) + pos_hint 居中)。

    Returns:
        ScatterLayout: 尺寸为设计画布(LOGICAL_WIDTH x LOGICAL_HEIGHT)、已按屏幕
        等比缩放并居中的容器, inner 作为其唯一子节点。
    """
    scale = min(Window.width / LOGICAL_WIDTH, Window.height / LOGICAL_HEIGHT)
    container = ScatterLayout(
        size=(LOGICAL_WIDTH, LOGICAL_HEIGHT),
        size_hint=(None, None),
        do_rotation=False,
        do_translation=False,
        do_scale=False,
    )
    container.scale = scale
    container.pos = (
        (Window.width - LOGICAL_WIDTH * scale) / 2.0,
        (Window.height - LOGICAL_HEIGHT * scale) / 2.0,
    )
    container.add_widget(inner)
    return container
