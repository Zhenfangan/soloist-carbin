"""CollapsibleGroup — 像素折叠分组组件。

像素三角箭头（▶ 折叠 / ▼ 展开），标题栏 + 可折叠内容区。
阶梯式展开动画（200ms，每 8px 一步）。
"""

from __future__ import annotations

from typing import Any

from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget

from app.ui.tokens import (
    BORDER_WIDTH,
    CARD_PADDING,
    CARD_WHITE,
    COLORS,
    FONT_SIZE_BODY,
    GRID_UNIT,
    SHADOW_BLACK,
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

        self._arrow_label = Label(
            text="[-]" if not collapsed else "[+]",
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(None, 1),
            width=24,
            halign="center",
            valign="middle",
        )

        self._title_label = Label(
            text=title,
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(1, 1),
            halign="left",
            valign="middle",
        )

        self._header.add_widget(self._arrow_label)
        self._header.add_widget(self._title_label)

        # 内容区
        self._content_box = BoxLayout(
            orientation="vertical",
            size_hint=(1, None),
            height=0 if collapsed else (content.height if content else 0),
            opacity=0 if collapsed else 1,
        )

        if content:
            self._content_box.add_widget(content)
            content.bind(height=self._on_content_size_change)

        self.add_widget(self._header)
        self.add_widget(self._content_box)

        self._update_height()
        self.bind(pos=self._redraw, size=self._redraw)
        self._redraw()

    @staticmethod
    def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
        h = hex_color.lstrip("#")
        return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, alpha)

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
        """展开内容区。"""
        if not self._collapsed:
            return
        self._collapsed = False
        self._arrow_label.text = "[-]"
        target_h = self._content_widget.height if self._content_widget else 0

        def _step_expand(step: int, total_steps: int, dt: float) -> None:
            progress = (step + 1) / total_steps
            self._content_box.height = target_h * progress
            self._content_box.opacity = progress
            self._update_height()

        steps = max(1, int(target_h) // GRID_UNIT)
        for i in range(steps):
            Clock.schedule_once(lambda dt, s=i: _step_expand(s, steps, dt), i * 0.2 / steps)
        Clock.schedule_once(lambda dt: self._finalize_expand(target_h), 0.2 + 0.05)

    def _finalize_expand(self, target_h: int) -> None:
        self._content_box.height = target_h
        self._content_box.opacity = 1
        self._update_height()

    def collapse(self) -> None:
        """折叠内容区。"""
        if self._collapsed:
            return
        self._collapsed = True
        self._arrow_label.text = "[+]"
        start_h = self._content_box.height

        def _step_collapse(step: int, total_steps: int, dt: float) -> None:
            progress = 1 - (step + 1) / total_steps
            self._content_box.height = start_h * max(0, progress)
            self._content_box.opacity = max(0, progress)
            self._update_height()

        steps = max(1, int(start_h) // GRID_UNIT)
        for i in range(steps):
            Clock.schedule_once(lambda dt, s=i: _step_collapse(s, steps, dt), i * 0.2 / steps)
        Clock.schedule_once(lambda dt: self._finalize_collapse(), 0.2 + 0.05)

    def _finalize_collapse(self) -> None:
        self._content_box.height = 0
        self._content_box.opacity = 0
        self._update_height()

    def set_content(self, widget: Widget) -> None:
        """替换内容区 Widget。"""
        self._content_box.clear_widgets()
        self._content_widget = widget
        self._content_box.add_widget(widget)
        widget.bind(height=self._on_content_size_change)
        if not self._collapsed:
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
        """绘制像素卡片边框。"""
        self.canvas.before.clear()
        x, y = self.pos
        w, h = self.size
        bw = BORDER_WIDTH

        with self.canvas.before:
            Color(*self._to_rgba(SHADOW_BLACK))
            Rectangle(pos=(x + 2, y - 2), size=(w, h))
            Color(*self._to_rgba(CARD_WHITE))
            Rectangle(pos=(x, y), size=(w, h))
            Color(*self._to_rgba("#FFFFFF"))
            Rectangle(pos=(x, y + h - bw), size=(w, bw))
            Rectangle(pos=(x, y), size=(bw, h))
            Color(*self._to_rgba(COLORS["CARD_SHADOW"]))
            Rectangle(pos=(x, y), size=(w, bw))
            Rectangle(pos=(x + w - bw, y), size=(bw, h))
