"""LoadingScreen — App 冷启动时的过渡加载页(Kivy 渲染, 真动画)。

原生 presplash.png 是静态图, Android 系统在 Python 启动前展示, 物理上无法
做成动态读条。这个组件是 Python/Kivy 启动后立刻接棒展示的"二级加载页",
读条用 Clock 驱动真实跑马灯动画(循环滑动点亮, 不依赖具体初始化进度百分
比 —— 冷启动耗时随设备/首次 JIT 编译不定, 循环动画保证观感"一直在动"
而非卡在固定百分比不动, 这正是要修的 bug)。
"""

from __future__ import annotations

from typing import Any

from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.widget import Widget

from app.ui.tokens import (
    COLORS,
    FONT_SIZE_SMALL,
    FONT_SIZE_TITLE,
    PRIMARY_YELLOW,
    TEXT_BROWN,
    TEXT_GRAY,
)

_STEP_INTERVAL = 0.12  # 跑马灯每步间隔(秒)


def _rgba(hex_color: str, a: float = 1.0) -> tuple[float, float, float, float]:
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, a)


class _SegmentBar(Widget):
    """分段像素读条 —— 循环跑马灯式点亮(2 段一组滑动), Clock 驱动真动画。"""

    segment_count = 10
    lit_span = 2  # 跑马灯亮段长度(相邻几段同时点亮, 视觉上像一节在跑)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._lit_start = 0
        self._event: Any = Clock.schedule_interval(self._advance, _STEP_INTERVAL)
        self.bind(pos=self._redraw, size=self._redraw)
        self._redraw()

    def _advance(self, dt: float) -> None:
        self._lit_start = (self._lit_start + 1) % self.segment_count
        self._redraw()

    def stop(self) -> None:
        """停止跑马灯(切到主界面前调用), 避免组件销毁后残留 Clock 事件。"""
        if self._event is not None:
            self._event.cancel()
            self._event = None

    def _redraw(self, *args: Any) -> None:
        self.canvas.clear()
        if self.width <= 0 or self.height <= 0:
            return
        gap = 4
        n = self.segment_count
        seg_w = (self.width - gap * (n - 1)) / n
        with self.canvas:
            for i in range(n):
                x = self.x + i * (seg_w + gap)
                dist = (i - self._lit_start) % n
                lit = dist < self.lit_span
                Color(*(_rgba(PRIMARY_YELLOW) if lit else _rgba(COLORS["CARD_SHADOW"])))
                Rectangle(pos=(x, self.y), size=(seg_w, self.height))


class LoadingScreen(FloatLayout):
    """冷启动加载页 —— 图标 + 标题 + 循环跑马灯读条, 与 presplash 视觉呼应。"""

    def __init__(self, icon_path: str, **kwargs: Any) -> None:
        kwargs.setdefault("size_hint", (1, 1))
        super().__init__(**kwargs)

        with self.canvas.before:
            Color(*_rgba(COLORS["BG_CREAM"]))
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._sync_bg, size=self._sync_bg)

        self._icon = Image(
            source=icon_path,
            size_hint=(None, None),
            size=(140, 140),
            pos_hint={"center_x": 0.5, "center_y": 0.58},
            allow_stretch=True,
        )
        self.add_widget(self._icon)

        self._title = Label(
            text="独奏者小屋",
            font_size=int(FONT_SIZE_TITLE * 1.3),
            color=_rgba(TEXT_BROWN),
            size_hint=(1, None),
            height=44,
            pos_hint={"center_x": 0.5, "center_y": 0.40},
            halign="center",
            valign="middle",
        )
        self._title.bind(size=lambda i, _: setattr(i, "text_size", i.size))
        self.add_widget(self._title)

        self._bar_wrap = FloatLayout(
            size_hint=(None, None),
            size=(180, 14),
            pos_hint={"center_x": 0.5, "center_y": 0.30},
        )
        self._bar = _SegmentBar(size_hint=(1, 1))
        self._bar_wrap.add_widget(self._bar)
        self.add_widget(self._bar_wrap)

        self._hint = Label(
            text="整理小屋中…",
            font_size=FONT_SIZE_SMALL,
            color=_rgba(TEXT_GRAY),
            size_hint=(1, None),
            height=24,
            pos_hint={"center_x": 0.5, "center_y": 0.22},
            halign="center",
            valign="middle",
        )
        self._hint.bind(size=lambda i, _: setattr(i, "text_size", i.size))
        self.add_widget(self._hint)

    def _sync_bg(self, *args: Any) -> None:
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size

    def stop(self) -> None:
        """切到主界面/引导前调用, 停止内部跑马灯动画。幂等, 可重复调用。"""
        self._bar.stop()
