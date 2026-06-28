"""CollapsibleGroup — 像素折叠分组组件。

标题栏（点击折叠/展开） + 可折叠内容区。
玻璃板（Minecraft 玻璃质感）卡片背景覆盖整个组件，折叠态也有框。
"""

from __future__ import annotations

from typing import Any

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget

from app.ui.components.glass_bg import draw_glass_card_bg
from app.ui.tokens import (
    CARD_PADDING,
    FONT_SIZE_BODY,
    GRID_UNIT,
    TEXT_BROWN,
)


class CollapsibleGroup(BoxLayout):  # type: ignore[misc]
    """像素折叠分组 — 垂直排列：标题栏 + 可折叠内容区。

    属性:
        title: 分组标题
        content: 折叠内容 Widget（由调用方传入）
        collapsed: 初始是否折叠 (默认 False，即展开)
    """

    def __init__(
        self,
        title: str = "",
        content: Widget | None = None,
        collapsed: bool = False,
        **kwargs: Any,
    ) -> None:
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("size_hint_y", None)
        super().__init__(**kwargs)

        self._collapsed = collapsed
        self._content_widget = content
        self._header_height = 48

        # 标题栏
        self._header = BoxLayout(
            orientation="horizontal",
            size_hint=(1, None),
            height=self._header_height,
            padding=[CARD_PADDING, 0],
            spacing=GRID_UNIT,
        )

        self._title_label = Label(
            text=title,
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(1, 1),
            halign="left",
            valign="middle",
        )
        self._header.add_widget(self._title_label)

        # 内容区
        self._content_box = BoxLayout(
            orientation="vertical",
            size_hint=(1, None),
            height=0 if collapsed else (content.height if content else 0),
            opacity=0 if collapsed else 1,
        )

        if content and not collapsed:
            self._content_box.add_widget(content)
        if content:
            content.bind(height=self._on_content_size_change)

        self.add_widget(self._header)
        self.add_widget(self._content_box)

        # 整个组件的玻璃板背景（折叠/展开都有框，使用默认亮色边框）
        self.bind(pos=self._redraw, size=self._redraw)

        self._update_height()
        self._redraw()

    @staticmethod
    def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
        h = hex_color.lstrip("#")
        return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, alpha)

    # ── 折叠/展开 ──

    @property
    def collapsed(self) -> bool:
        return self._collapsed

    def on_touch_down(self, touch: Any) -> bool:
        """头部点击切换折叠/展开。"""
        if self._header.collide_point(*touch.pos):
            self.toggle()
            return True
        return super().on_touch_down(touch)

    def toggle(self) -> None:
        """切换展开/折叠状态。"""
        if self._collapsed:
            self.expand()
        else:
            self.collapse()

    def expand(self) -> None:
        """展开内容区（直接到位，无逐帧动画）。"""
        if not self._collapsed:
            return
        self._collapsed = False
        # 重新添加内容 widget（折叠时被移除了）
        if self._content_widget:
            self._content_box.add_widget(self._content_widget)
        target_h = self._content_widget.height if self._content_widget else 0
        self._content_box.height = target_h
        self._content_box.opacity = 1
        self._update_height()

    def collapse(self) -> None:
        """折叠内容区（移除子 widget 防止触摸泄漏，直接到位，无逐帧动画）。"""
        if self._collapsed:
            return
        self._collapsed = True
        # 移除内容区子 widget，防止折叠态误触透传到其他区域
        self._content_box.clear_widgets()
        self._content_box.height = 0
        self._content_box.opacity = 0
        self._update_height()

    def set_content(self, widget: Widget) -> None:
        """替换内容区 Widget。"""
        self._content_box.clear_widgets()
        self._content_widget = widget
        widget.bind(height=self._on_content_size_change)
        if not self._collapsed:
            self._content_box.add_widget(widget)
            self._content_box.height = widget.height
        self._update_height()

    def _on_content_size_change(self, instance: Any, value: Any) -> None:
        if not self._collapsed and self._content_widget:
            self._content_box.height = self._content_widget.height
        self._update_height()

    def _update_height(self, *args: Any) -> None:
        visible_content = self._content_box.height if not self._collapsed else 0
        self.height = self._header_height + visible_content
        if self.parent and hasattr(self.parent, "_trigger_layout"):
            self.parent._trigger_layout()
        self._redraw()

    def _redraw(self, *args: Any) -> None:
        """在整个组件上绘制 Minecraft 玻璃板卡片背景。

        使用默认亮色像素边框（白色亮面 + 浅灰蓝暗面），
        与 BetTaskItem / StatusBox / TaskInlineList 玻璃框效果一致。
        折叠和展开状态都有玻璃框。
        """
        draw_glass_card_bg(self)
