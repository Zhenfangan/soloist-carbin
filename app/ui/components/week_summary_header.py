"""WeekSummaryHeader — 本周总结浮层。

始终可见的顶部浮层 2px 边框卡片，显示已完成/超额/预计奖励/完成率。
数值变化时触发数字跳动动画 (300ms)。
"""

from __future__ import annotations

from typing import Any

from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label

from app.ui.tokens import (
    BORDER_WIDTH,
    CARD_WHITE,
    COLORS,
    DOPAMINE_COLORS,
    FONT_SIZE_BODY,
    FONT_SIZE_TITLE,
    GRID_UNIT,
    PRIMARY_YELLOW,
    SHADOW_BLACK,
    TEXT_BROWN,
)


class WeekSummaryHeader(FloatLayout):  # type: ignore[misc]
    """本周总结浮层。

    属性:
        summary: 包含 week_start / total_tasks / completed / completed_count /
                 extra_count / completion_rate / total_reward / config 的字典
    """

    PAGE_PADDING: int = GRID_UNIT * 2

    def __init__(self, summary: dict[str, object] | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = 72
        self._summary: dict[str, object] = summary or {}

        # --- 左侧: 已完成 / 超额 ---
        self._completed_label = Label(
            text="",
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(DOPAMINE_COLORS["mint"]["light"]),
            size_hint=(None, None),
            halign="left",
            valign="middle",
            pos_hint={"x": 0, "y": 0.55},
            shorten=False,
        )

        self._reward_label = Label(
            text="",
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(PRIMARY_YELLOW),
            size_hint=(None, None),
            halign="left",
            valign="middle",
            pos_hint={"x": 0, "y": 0.15},
            bold=True,
            shorten=False,
        )

        # --- 右侧: 完成率 ---
        self._rate_label = Label(
            text="",
            font_size=FONT_SIZE_TITLE,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(None, None),
            halign="right",
            valign="middle",
            pos_hint={"x": 0, "y": 0.35},
            bold=True,
            shorten=False,
        )

        self.add_widget(self._completed_label)
        self.add_widget(self._reward_label)
        self.add_widget(self._rate_label)

        self.bind(pos=self._redraw, size=self._redraw)
        self.bind(size=self._reposition_labels)

        if summary:
            self.update_summary(summary)

    @staticmethod
    def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
        h = hex_color.lstrip("#")
        return (
            int(h[0:2], 16) / 255.0,
            int(h[2:4], 16) / 255.0,
            int(h[4:6], 16) / 255.0,
            alpha,
        )

    def update_summary(self, summary: dict[str, object], animate: bool = True) -> None:
        """更新所有数据，可选数字跳动动画。"""
        self._summary = summary
        completed = summary.get("completed", 0)
        extra_count = summary.get("extra_count", 0)
        total_reward = summary.get("total_reward", 0.0)
        completion_rate = summary.get("completion_rate", 0.0)

        assert isinstance(completed, int)
        assert isinstance(extra_count, int)
        assert isinstance(total_reward, (int, float))
        assert isinstance(completion_rate, (int, float))

        # Direct set (no animation)
        self._completed_label.text = f"已完成 {completed}  超额 {extra_count}"
        self._reward_label.text = f"预计奖励: {int(total_reward):+d}"
        self._rate_label.text = f"{int(completion_rate)}%"

        if not animate:
            return

        # Determine previous values for animation
        old_completed = 0
        old_extra = 0
        old_reward = 0.0
        old_rate = 0.0

        completed_text = self._completed_label.text
        if completed_text:
            import re

            m = re.search(r"已完成\s*(\d+)\s*超额\s*(\d+)", completed_text)
            if m:
                old_completed = int(m.group(1))
                old_extra = int(m.group(2))

        reward_text = self._reward_label.text
        if reward_text:
            import re

            m = re.search(r"[+-]?(\d+(?:\.\d+)?)", reward_text.replace("预计奖励: ", ""))
            if m:
                old_reward = float(m.group(1))

        rate_text = self._rate_label.text
        if rate_text:
            import re

            m = re.search(r"(\d+(?:\.\d+)?)%", rate_text)
            if m:
                old_rate = float(m.group(1))

        # Animate numbers
        self._animate_count(self._completed_label, old_completed, completed,
                            old_extra, extra_count)
        self._animate_reward(old_reward, total_reward)
        self._animate_rate(old_rate, completion_rate)

    def _animate_count(
        self, label: Label, old_c: int, new_c: int, old_e: int, new_e: int
    ) -> None:
        """动画显示已完成/超额数字变化。"""
        steps = 10
        interval = 0.03  # 10 steps × 30ms = 300ms total

        for i in range(steps + 1):
            progress = i / steps
            cur_c = int(old_c + (new_c - old_c) * progress)
            cur_e = int(old_e + (new_e - old_e) * progress)
            Clock.schedule_once(
                lambda dt, cc=cur_c, ce=cur_e: self._set_count_text(label, cc, ce),
                i * interval,
            )

    def _set_count_text(self, label: Label, completed: int, extra: int) -> None:
        label.text = f"已完成 {completed}  超额 {extra}"

    def _animate_reward(self, old_val: float, new_val: float) -> None:
        steps = 10
        interval = 0.03

        for i in range(steps + 1):
            progress = i / steps
            cur = old_val + (new_val - old_val) * progress
            Clock.schedule_once(
                lambda dt, v=cur: self._set_reward_text(v), i * interval
            )

    def _set_reward_text(self, value: float) -> None:
        sign = "+" if value >= 0 else ""
        self._reward_label.text = f"预计奖励: {sign}{int(value)}"

    def _animate_rate(self, old_val: float, new_val: float) -> None:
        steps = 10
        interval = 0.03

        for i in range(steps + 1):
            progress = i / steps
            cur = old_val + (new_val - old_val) * progress
            Clock.schedule_once(
                lambda dt, v=cur: self._set_rate_text(v), i * interval
            )

    def _set_rate_text(self, value: float) -> None:
        self._rate_label.text = f"{int(value)}%"

    def _redraw(self, *args: Any) -> None:
        """绘制 2px 像素边框卡片 + 2px 黑色偏移阴影。"""
        self.canvas.before.clear()
        x, y = self.pos
        w, h = self.size
        bw = BORDER_WIDTH

        with self.canvas.before:
            # 2px 黑色阴影 (右下偏移)
            Color(*self._to_rgba(SHADOW_BLACK))
            Rectangle(pos=(x + 2, y - 2), size=(w, h))

            # 卡片背景填充
            Color(*self._to_rgba(CARD_WHITE))
            Rectangle(pos=(x, y), size=(w, h))

            # 凸起边框: 亮面 top+left
            Color(*self._to_rgba("#FFFFFF"))
            Rectangle(pos=(x, y + h - bw), size=(w, bw))
            Rectangle(pos=(x, y), size=(bw, h))

            # 暗面 bottom+right
            Color(*self._to_rgba(COLORS["CARD_SHADOW"]))
            Rectangle(pos=(x, y), size=(w, bw))
            Rectangle(pos=(x + w - bw, y), size=(bw, h))

        self._reposition_labels()

    def _reposition_labels(self, *args: Any) -> None:
        """重排 3 个 label 位置, 确保无水平重叠。"""
        w = self.width
        h = self.height
        pad = 8  # 左右留白

        # completed_label: 左上
        self._completed_label.pos = (self.x + pad, self.y + h * 0.7)
        self._completed_label.size = (w * 0.55, 20)

        # rate_label: 右侧中部
        self._rate_label.pos = (self.x + w * 0.65, self.y + h * 0.3)
        self._rate_label.size = (w * 0.35 - pad, 24)

        # reward_label: 左下, 确保右边界在 rate_label 左边界之前
        self._reward_label.pos = (self.x + pad, self.y + h * 0.05)
        self._reward_label.size = (w * 0.55, 24)
