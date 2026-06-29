"""TimeControlPanel — 虚拟时钟调试面板。

浮动在屏幕顶部,可手动设置任意日期/时间 + 快进/快退,方便测试不同时段行为。
"""

from __future__ import annotations

from typing import Any

from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput

from app.ui.components.pixel_button import PixelButton
from app.ui.tokens import (
    BORDER_WIDTH,
    CARD_WHITE,
    COLORS,
    FONT_SIZE_BODY,
    FONT_SIZE_SMALL,
    GRID_UNIT,
    SHADOW_BLACK,
    TEXT_BROWN,
)


class TimeControlPanel(BoxLayout):  # type: ignore[misc]
    """虚拟时钟控制条 — 可设置任意日期/时间 + 快进快退。

    布局 (垂直两行):
      Row 1: [日期输入 100px] [时间输入 60px] [Set] [当前显示]
      Row 2: [-1d] [-1h] [+15m] [+30m] [+1h] [+1d]
    """

    def __init__(self, on_time_changed: Any = None, **kwargs: Any) -> None:
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("size_hint", (1, None))
        kwargs.setdefault("height", 64)
        kwargs.setdefault("padding", [GRID_UNIT // 2, 3])
        kwargs.setdefault("spacing", 3)
        super().__init__(**kwargs)

        self._on_time_changed = on_time_changed

        # ── Row 1: 日期 + 时间 + Set + 当前显示 ──────────────────
        row1 = BoxLayout(orientation="horizontal", size_hint=(1, None), height=26, spacing=3)

        from app.utils.clock import get_clock
        c = get_clock()
        cur_date = c.today_str()
        cur_time = c.current_time_str()[:5]

        self._date_input = TextInput(
            text=cur_date,
            font_size=FONT_SIZE_SMALL,
            size_hint=(None, 1),
            width=100,
            multiline=False,
            hint_text="YYYY-MM-DD",
            padding=[4, 4],
        )
        row1.add_widget(self._date_input)

        self._time_input = TextInput(
            text=cur_time,
            font_size=FONT_SIZE_SMALL,
            size_hint=(None, 1),
            width=60,
            multiline=False,
            hint_text="HH:MM",
            padding=[4, 4],
        )
        row1.add_widget(self._time_input)

        set_btn = PixelButton(
            text="Set",
            color=COLORS["PRIMARY_YELLOW"],
            size_mode="small",
            size_hint=(None, 1),
            width=40,
        )
        set_btn.bind(on_press=self._apply_set)
        row1.add_widget(set_btn)

        self._time_label = Label(
            text=self._current_time_text(),
            font_size=FONT_SIZE_SMALL,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(1, 1),
            halign="center",
            valign="middle",
        )
        self._time_label.bind(size=lambda i, _: setattr(i, "text_size", i.size))
        row1.add_widget(self._time_label)

        self.add_widget(row1)

        # ── Row 2: 快退/快进按钮 ──────────────────────────────────
        row2 = BoxLayout(orientation="horizontal", size_hint=(1, None), height=24, spacing=2)

        steps = [
            ("-1d", -1440),
            ("-1h", -60),
            ("+15m", 15),
            ("+30m", 30),
            ("+1h", 60),
            ("+1d", 1440),
        ]
        for label_text, minutes in steps:
            color = COLORS["PRIMARY_YELLOW"] if minutes < 0 else COLORS["CARD_SHADOW"]
            btn = PixelButton(
                text=label_text,
                color=color,
                size_mode="small",
                size_hint=(1, 1),
            )
            btn.bind(on_press=lambda _, m=minutes: self._advance(m))
            row2.add_widget(btn)

        self.add_widget(row2)

        # 像素边框
        self.bind(pos=self._redraw, size=self._redraw)

        # 每秒刷新时间显示
        self._tick_ev = Clock.schedule_interval(lambda dt: self._tick(), 1)

    def _current_time_text(self) -> str:
        c = _get_clock()
        return f"{c.today_str()} {c.current_time_str()[:5]}"

    def _tick(self) -> None:
        self._time_label.text = self._current_time_text()

    def _refresh_inputs(self) -> None:
        """同步输入框到当前时钟值。"""
        c = _get_clock()
        self._date_input.text = c.today_str()
        self._time_input.text = c.current_time_str()[:5]

    def _apply_set(self, *args: Any) -> None:
        """应用用户输入的日期/时间到虚拟时钟。"""
        from app.utils.clock import get_clock
        d = self._date_input.text.strip()
        t = self._time_input.text.strip()
        if not d or not t:
            return
        c = get_clock()
        if hasattr(c, "set_date_and_time"):
            try:
                c.set_date_and_time(d, t)
                self._time_label.text = self._current_time_text()
                if self._on_time_changed:
                    self._on_time_changed()
            except Exception:
                self._refresh_inputs()  # 格式错误回退

    def _advance(self, minutes: int) -> None:
        c = _get_clock()
        if hasattr(c, "advance"):
            c.advance(minutes=minutes)
            self._time_label.text = self._current_time_text()
            self._refresh_inputs()
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


def _get_clock() -> Any:
    from app.utils.clock import get_clock
    return get_clock()
