"""TimeControlPanel — 虚拟时钟调试面板。

浮动在屏幕顶部，可手动快进时间，方便测试不同时段的行为。
"""

from __future__ import annotations

from typing import Any

from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

from app.ui.components.pixel_button import PixelButton
from app.ui.tokens import (
    BORDER_WIDTH,
    CARD_WHITE,
    COLORS,
    DOPAMINE_COLORS,
    FONT_SIZE_BODY,
    FONT_SIZE_SMALL,
    GRID_UNIT,
    SHADOW_BLACK,
    TEXT_BROWN,
    TEXT_GRAY,
)


class TimeControlPanel(BoxLayout):  # type: ignore[misc]
    """虚拟时钟控制条 — 可快进时间，方便测试。

    显示当前模拟时间 + 快进按钮: +15m, +30m, +1h, +2h, +1d。
    """

    def __init__(self, on_time_changed: Any = None, **kwargs: Any) -> None:
        kwargs.setdefault("orientation", "horizontal")
        kwargs.setdefault("size_hint", (1, None))
        kwargs.setdefault("height", 42)
        kwargs.setdefault("padding", [GRID_UNIT // 2, 4])
        kwargs.setdefault("spacing", GRID_UNIT // 2)
        super().__init__(**kwargs)

        self._on_time_changed = on_time_changed

        # 当前时间标签
        self._time_label = Label(
            text=self._current_time_text(),
            font_size=FONT_SIZE_SMALL,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(None, 1),
            width=140,
            halign="left",
            valign="middle",
        )
        self._time_label.bind(size=lambda i, _: setattr(i, "text_size", i.size))
        self.add_widget(self._time_label)

        # 快进按钮
        steps = [
            ("+15m", 15),
            ("+30m", 30),
            ("+1h", 60),
            ("+2h", 120),
            ("+1d", 1440),
        ]
        for label_text, minutes in steps:
            btn = PixelButton(
                text=label_text,
                color=COLORS["CARD_SHADOW"],
                size_mode="small",
                size_hint=(1, 1),
            )
            btn.bind(on_press=lambda _, m=minutes: self._advance(m))
            self.add_widget(btn)

        # 像素边框
        self.bind(pos=self._redraw, size=self._redraw)

        # 每秒刷新时间显示
        self._tick_ev = Clock.schedule_interval(lambda dt: self._tick(), 1)

    def _current_time_text(self) -> str:
        from app.utils.clock import get_clock
        c = get_clock()
        return f"{c.today_str()} {c.current_time_str()[:5]}"

    def _tick(self) -> None:
        self._time_label.text = self._current_time_text()

    def _advance(self, minutes: int) -> None:
        from app.utils.clock import get_clock
        c = get_clock()
        if hasattr(c, "advance"):
            c.advance(minutes=minutes)
            self._time_label.text = self._current_time_text()
            if self._on_time_changed:
                self._on_time_changed()

    @staticmethod
    def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
        h = hex_color.lstrip("#")
        return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, alpha)

    def _redraw(self, *args: Any) -> None:
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
