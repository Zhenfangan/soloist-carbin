"""HistoryTabs — 周/月/年 三 Tab 切换组件。

选中项明黄色高亮，未选中灰褐色。点击切换带 150ms 渐隐渐显动画。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from kivy.animation import Animation
from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button

from app.ui.tokens import (
    BORDER_WIDTH,
    BTN_HEIGHT,
    COLORS,
    FONT_SIZE_BODY,
    PRIMARY_YELLOW,
    TEXT_BROWN,
)


class HistoryTabs(BoxLayout):  # type: ignore[misc]
    """历史页顶部三 Tab 切换。

    属性:
        active_tab: 当前选中 Tab 索引 (0=周, 1=月, 2=年)
        on_tab_change: Tab 切换回调 (tab_index: int) -> None
    """

    def __init__(
        self,
        on_tab_change: Callable[[int], Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            orientation="horizontal",
            spacing=0,
            size_hint=(1, None),
            height=BTN_HEIGHT,
            **kwargs,
        )
        self._active_tab: int = 0
        self._on_tab_change: Callable[[int], Any] | None = on_tab_change
        self._tab_buttons: list[Button] = []

        tab_labels = ["周", "月", "年"]
        for i, label in enumerate(tab_labels):
            btn = Button(
                text=label,
                font_size=FONT_SIZE_BODY,
                background_normal="",
                background_down="",
                background_color=(0, 0, 0, 0),
                color=self._to_rgba(TEXT_BROWN),
                size_hint=(1, 1),
            )
            btn.bind(on_press=lambda _btn, idx=i: self._select_tab(idx))
            self._tab_buttons.append(btn)
            self.add_widget(btn)

        self.bind(pos=self._redraw_all, size=self._redraw_all)

    @property
    def active_tab(self) -> int:
        """当前选中的 tab 索引。"""
        return self._active_tab

    @active_tab.setter
    def active_tab(self, value: int) -> None:
        if 0 <= value <= 2 and value != self._active_tab:
            self._select_tab(value)

    def set_active(self, index: int) -> None:
        """公开方法：强制将指定 tab 设为 active，即使与当前 index 相同也刷新视觉。"""
        old_index = self._active_tab
        self._active_tab = index

        # 150ms 渐隐渐显动画（只在切换时触发）
        if old_index != index:
            if old_index < len(self._tab_buttons):
                anim_out = Animation(opacity=0.5, duration=0.15)
                anim_out.start(self._tab_buttons[old_index])
            if index < len(self._tab_buttons):
                anim_in = Animation(opacity=1.0, duration=0.15)
                anim_in.start(self._tab_buttons[index])

        self._redraw()
        self._redraw_tab_indicators()

    def _select_tab(self, tab_index: int) -> None:
        """选中指定 tab。"""
        if tab_index == self._active_tab:
            return

        self.set_active(tab_index)
        if self._on_tab_change:
            self._on_tab_change(tab_index)

    @staticmethod
    def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
        h = hex_color.lstrip("#")
        return (
            int(h[0:2], 16) / 255.0,
            int(h[2:4], 16) / 255.0,
            int(h[4:6], 16) / 255.0,
            alpha,
        )

    def _redraw_all(self, *args: Any) -> None:
        """pos/size 变化时同时重绘背景和 tab 指示器。"""
        self._redraw()
        self._redraw_tab_indicators()

    def _redraw(self, *args: Any) -> None:
        """重绘各 tab 的像素背景。"""
        self.canvas.before.clear()
        if not self._tab_buttons:
            return

        bw = BORDER_WIDTH

        with self.canvas.before:
            for i, btn in enumerate(self._tab_buttons):
                x, y = btn.pos
                w, h = btn.size

                is_active = i == self._active_tab
                bg_color = PRIMARY_YELLOW if is_active else COLORS["CARD_SHADOW"]
                border_color = TEXT_BROWN

                # 背景填充
                Color(*self._to_rgba(bg_color))
                Rectangle(pos=(x + bw, y + bw), size=(w - 2 * bw, h - 2 * bw))

                # 2px 边框
                Color(*self._to_rgba(border_color))
                # top
                Rectangle(pos=(x, y + h - bw), size=(w, bw))
                # bottom
                Rectangle(pos=(x, y), size=(w, bw))
                # left
                Rectangle(pos=(x, y), size=(bw, h))
                # right
                Rectangle(pos=(x + w - bw, y), size=(bw, h))

    def _redraw_tab_indicators(self, *args: Any) -> None:
        """在每个 tab button 的 canvas.after 绘制底边指示器。

        active tab 绘制 4px 黄色底边矩形；inactive tab 清空 canvas.after。
        """
        _INDICATOR_H = 4  # 底边指示器高度 (px)

        for i, btn in enumerate(self._tab_buttons):
            btn.canvas.after.clear()
            if i == self._active_tab:
                x, y = btn.pos
                w, _ = btn.size
                with btn.canvas.after:
                    Color(*self._to_rgba(PRIMARY_YELLOW))
                    Rectangle(pos=(x, y), size=(w, _INDICATOR_H))
