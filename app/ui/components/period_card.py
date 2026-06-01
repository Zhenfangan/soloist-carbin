"""PeriodCard — 时段卡片组件。

三种状态:
- collapsed: 折叠小条，显示时段名+时间
- expanded: 展开，含签到/签退按钮+请假入口
- completed: 完成，显示 ✅ + 摘要
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label

from app.ui.components.pixel_button import PixelButton
from app.ui.tokens import (
    BORDER_WIDTH,
    CARD_PADDING,
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

# 时段标签映射
PERIOD_LABELS: dict[str, str] = {
    "morning": "上午",
    "afternoon": "下午",
    "evening": "晚上",
    "night": "晚上",
}

# 时段图标
PERIOD_ICONS: dict[str, str] = {
    "morning": "☀️",  # ☀️
    "afternoon": "☀️",  # ☀️
    "evening": "\U0001f319",     # 🌙
    "night": "\U0001f319",       # 🌙
}

# 时段时间范围
PERIOD_TIME_RANGES: dict[str, tuple[str, str]] = {
    "morning": ("09:00", "12:00"),
    "afternoon": ("14:00", "18:00"),
    "evening": ("", ""),
    "night": ("", ""),
}


class PeriodCard(FloatLayout):  # type: ignore[misc]
    """时段卡片组件。

    属性:
        period_name: 时段标识 (morning/afternoon/evening/night)
        on_checkin: 签到回调 (period_name) -> None
        on_checkout: 签退回调 (period_name) -> None
        on_leave: 请假回调 (period_name) -> None
        is_current: 是否为当前时段
        card_state: 卡片状态 (collapsed/expanded/completed)
        status: 时段状态 (pending/normal/late/...)
        has_checked_in: 是否已签到
        has_checked_out: 是否已签退
        checkin_time: 签到时间
        checkout_time: 签退时间
        leave_enabled: 请假按钮是否可用
    """

    _ANIMATION_DURATION = 0.3  # 动画持续时间（秒）
    _EXPANDED_HEIGHT = 180    # 展开态卡片高度
    _COLLAPSED_HEIGHT = 48    # 折叠态卡片高度

    def __init__(
        self,
        period_name: str = "morning",
        on_checkin: Callable[[str], Any] | None = None,
        on_checkout: Callable[[str], Any] | None = None,
        on_leave: Callable[[str], Any] | None = None,
        is_current: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.size_hint = (1, None)
        self.height = self._COLLAPSED_HEIGHT

        self._period_name = period_name
        self._on_checkin_cb = on_checkin
        self._on_checkout_cb = on_checkout
        self._on_leave_cb = on_leave
        self._is_current = is_current
        self._card_state = "collapsed"
        self._status = "pending"
        self._has_checked_in = False
        self._has_checked_out = False
        self._checkin_time: str | None = None
        self._checkout_time: str | None = None
        self._leave_enabled = False
        self._target_height = self._COLLAPSED_HEIGHT

        # 外观
        self._period_label = PERIOD_LABELS.get(period_name, period_name)
        self._period_icon = PERIOD_ICONS.get(period_name, "")
        start, end = PERIOD_TIME_RANGES.get(period_name, ("", ""))
        self._start_time = start
        self._end_time = end

        # 构建头部行（始终显示）
        self._header = BoxLayout(
            orientation="horizontal",
            size_hint=(1, None),
            height=self._COLLAPSED_HEIGHT,
            pos_hint={"x": 0, "y": 0},
            padding=[CARD_PADDING, 0],
            spacing=GRID_UNIT,
        )

        # 图标
        self._icon_label = Label(
            text=self._period_icon,
            font_size=FONT_SIZE_BODY,
            size_hint=(None, 1),
            width=30,
            halign="center",
            valign="middle",
        )

        # 时段名称
        self._name_label = Label(
            text=self._period_label,
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(None, 1),
            width=50,
            halign="left",
            valign="middle",
        )

        # 时间范围 / 摘要
        self._summary_label = Label(
            text=self._get_time_range_text(),
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(TEXT_GRAY),
            size_hint=(1, 1),
            halign="left",
            valign="middle",
        )

        self._header.add_widget(self._icon_label)
        self._header.add_widget(self._name_label)
        self._header.add_widget(self._summary_label)
        self.add_widget(self._header)

        # 展开区域内容（仅 expanded 时显示）
        self._content_area = FloatLayout(
            size_hint=(1, None),
            height=0,
            pos_hint={"x": 0, "y": 0},
            opacity=0,
        )

        # 签到/签退大按钮
        self._action_btn = PixelButton(
            text="签到",
            color=COLORS["PRIMARY_YELLOW"],
            size_mode="large",
            size_hint=(0.8, None),
            pos_hint={"center_x": 0.5, "center_y": 0.55},
        )
        self._action_btn.bind(on_press=lambda _: self._on_action())
        self._content_area.add_widget(self._action_btn)

        # 请假入口
        self._leave_label = Label(
            text="请假",
            font_size=FONT_SIZE_SMALL,
            color=self._to_rgba(TEXT_GRAY),
            size_hint=(None, None),
            size=(60, 24),
            pos_hint={"center_x": 0.5, "y": 0.05},
            halign="center",
            valign="middle",
        )
        self._leave_label.bind(on_touch_down=self._on_leave_touch)
        self._content_area.add_widget(self._leave_label)

        self.add_widget(self._content_area)

        # 状态完成图标（completed 状态时显示）
        self._check_label = Label(
            text="",
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(DOPAMINE_COLORS["mint"]["light"]),
            size_hint=(None, 1),
            width=100,
            pos_hint={"x": 0.65, "y": 0},
            halign="left",
            valign="middle",
        )
        self.add_widget(self._check_label)

        self.bind(pos=self._redraw, size=self._redraw)

    @staticmethod
    def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
        h = hex_color.lstrip("#")
        return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, alpha)

    def _get_time_range_text(self) -> str:
        if self._start_time and self._end_time:
            return f"{self._start_time}-{self._end_time}"
        return self._period_label

    @property
    def card_state(self) -> str:
        return self._card_state

    @card_state.setter
    def card_state(self, state: str) -> None:
        if state == self._card_state:
            return
        self._card_state = state
        self._update_display()

    @property
    def status(self) -> str:
        return self._status

    @status.setter
    def status(self, value: str) -> None:
        self._status = value
        self._update_display()

    @property
    def has_checked_in(self) -> bool:
        return self._has_checked_in

    @has_checked_in.setter
    def has_checked_in(self, value: bool) -> None:
        self._has_checked_in = value
        self._update_display()

    @property
    def has_checked_out(self) -> bool:
        return self._has_checked_out

    @has_checked_out.setter
    def has_checked_out(self, value: bool) -> None:
        self._has_checked_out = value
        self._update_display()

    @property
    def checkin_time(self) -> str | None:
        return self._checkin_time

    @checkin_time.setter
    def checkin_time(self, value: str | None) -> None:
        self._checkin_time = value
        self._update_display()

    @property
    def checkout_time(self) -> str | None:
        return self._checkout_time

    @checkout_time.setter
    def checkout_time(self, value: str | None) -> None:
        self._checkout_time = value
        self._update_display()

    @property
    def leave_enabled(self) -> bool:
        return self._leave_enabled

    @leave_enabled.setter
    def leave_enabled(self, value: bool) -> None:
        self._leave_enabled = value
        self._update_display()

    @property
    def is_current(self) -> bool:
        return self._is_current

    @is_current.setter
    def is_current(self, value: bool) -> None:
        self._is_current = value
        self._update_display()

    def expand(self, animate: bool = True) -> None:
        """展开卡片。"""
        if self._card_state == "expanded":
            return
        self._card_state = "expanded"
        self._target_height = self._EXPANDED_HEIGHT
        self._animation_start(animate)

    def collapse(self, animate: bool = True) -> None:
        """折叠卡片。"""
        if self._card_state == "collapsed":
            return
        self._card_state = "collapsed"
        self._target_height = self._COLLAPSED_HEIGHT
        self._animation_start(animate)

    def complete(self, animate: bool = True) -> None:
        """标记为完成状态。"""
        self._card_state = "completed"
        self._target_height = self._COLLAPSED_HEIGHT
        self._animation_start(animate)

    def _animation_start(self, animate: bool) -> None:
        """开始动画。"""
        if not animate:
            self.height = self._target_height
            self._update_display()
            return

        start_h = self.height
        target_h = self._target_height
        diff = target_h - start_h
        steps = max(1, abs(diff) // GRID_UNIT)

        for i in range(steps):
            Clock.schedule_once(
                lambda dt, s=i, total=steps: self._animation_step(s, total, start_h, diff),
                i * self._ANIMATION_DURATION / steps,
            )
        # 最后确保到达目标
        Clock.schedule_once(
            lambda dt: self._animation_finalize(target_h),
            self._ANIMATION_DURATION + 0.01,
        )

    def _animation_step(self, step: int, total: int, start_h: int, diff: int) -> None:
        progress = (step + 1) / total
        self.height = start_h + int(diff * progress)
        self._update_display()

    def _animation_finalize(self, target_h: int) -> None:
        self.height = target_h
        self._update_display()

    def _update_display(self) -> None:
        """根据当前状态更新显示。"""
        # 更新摘要文字
        if self._card_state == "completed":
            parts = []
            if self._checkin_time:
                status_text = self._get_status_text()
                parts.append(f"{status_text} {self._checkin_time}")
            if self._checkout_time:
                parts.append(f"签退 {self._checkout_time}")
            self._summary_label.text = "  ".join(parts) if parts else "✅ 已完成"
            self._summary_label.color = self._to_rgba(DOPAMINE_COLORS["mint"]["light"])
        elif self._card_state == "collapsed":
            self._summary_label.text = self._get_time_range_text()
            self._summary_label.color = self._to_rgba(TEXT_GRAY)
        elif self._card_state == "expanded":
            self._summary_label.text = self._get_time_range_text()
            self._summary_label.color = self._to_rgba(TEXT_BROWN)

        # 更新内容区显示
        is_expanded = self._card_state == "expanded"
        self._content_area.height = self._EXPANDED_HEIGHT - self._COLLAPSED_HEIGHT if is_expanded else 0
        self._content_area.opacity = 1.0 if is_expanded else 0

        # 更新按钮文字和颜色
        if self._has_checked_in and not self._has_checked_out:
            self._action_btn.text = "签退"
            self._action_btn.set_color(DOPAMINE_COLORS["mint"]["light"])
        elif self._has_checked_out:
            self._action_btn.text = "✅ 已签退"
            self._action_btn.disabled = True
        else:
            self._action_btn.text = "签到"
            self._action_btn.set_color(COLORS["PRIMARY_YELLOW"])
            self._action_btn.disabled = not self._is_current

        # 更新请假入口
        if self._card_state == "expanded":
            self._leave_label.color = self._to_rgba(TEXT_BROWN if self._leave_enabled else TEXT_GRAY)
            self._leave_label.opacity = 1.0
        else:
            self._leave_label.opacity = 0

        # 完成标签
        if self._card_state == "completed":
            self._check_label.text = f"✅ {self._get_status_text()}"
            self._check_label.opacity = 1.0
        else:
            self._check_label.text = ""
            self._check_label.opacity = 0

        self._redraw()

    def _get_status_text(self) -> str:
        status_map: dict[str, str] = {
            "normal": "正常",
            "late": "迟到",
            "early_leave": "早退",
            "absent": "旷工",
            "leave": "请假",
            "shooting": "撮影中",
            "pending": "签到",
        }
        return status_map.get(self._status, "签到")

    def _on_action(self) -> None:
        """签到/签退按钮回调。"""
        if self._has_checked_in and not self._has_checked_out:
            if self._on_checkout_cb:
                self._on_checkout_cb(self._period_name)
        else:
            if self._on_checkin_cb:
                self._on_checkin_cb(self._period_name)

    def _on_leave_touch(self, instance: Any, touch: Any) -> bool:
        """请假标签点击。"""
        if not self._leave_enabled:
            return False
        if self._leave_label.collide_point(*touch.pos):
            if self._on_leave_cb:
                self._on_leave_cb(self._period_name)
            return True
        return False

    def set_status_from_period(self, period_status: Any) -> None:
        """从 PeriodStatus 对象更新状态。"""
        if period_status is None:
            return
        self._status = period_status.status
        self._checkin_time = period_status.checkin_time
        self._checkout_time = period_status.checkout_time
        self._has_checked_in = period_status.checkin_time is not None
        self._has_checked_out = period_status.checkout_time is not None

        if period_status.status in ("normal", "late", "early_leave", "leave", "shooting"):
            self._card_state = "completed"
            self._target_height = self._COLLAPSED_HEIGHT
        elif period_status.status == "pending":
            self._card_state = "collapsed"
            self._target_height = self._COLLAPSED_HEIGHT

        self._update_display()

    def _redraw(self, *args: Any) -> None:
        """重绘卡片像素边框。"""
        self.canvas.before.clear()
        x, y = self.pos
        w, h = self.size
        bw = BORDER_WIDTH

        # 选择边框颜色
        if self._card_state == "expanded":
            border_light = "#FFFFFF"
            border_dark = COLORS["CARD_SHADOW"]
        elif self._card_state == "completed":
            border_light = DOPAMINE_COLORS["mint"]["light"]
            border_dark = DOPAMINE_COLORS["mint"]["dark"]
        else:
            border_light = "#FFFFFF"
            border_dark = COLORS["CARD_SHADOW"]

        with self.canvas.before:
            # 阴影
            Color(*self._to_rgba(SHADOW_BLACK))
            Rectangle(pos=(x + 2, y - 2), size=(w, h))
            # 卡片背景
            bg_color = CARD_WHITE
            Color(*self._to_rgba(bg_color))
            Rectangle(pos=(x, y), size=(w, h))
            # 凸起边框: 亮面 top+left
            Color(*self._to_rgba(border_light))
            Rectangle(pos=(x, y + h - bw), size=(w, bw))
            Rectangle(pos=(x, y), size=(bw, h))
            # 暗面 bottom+right
            Color(*self._to_rgba(border_dark))
            Rectangle(pos=(x, y), size=(w, bw))
            Rectangle(pos=(x + w - bw, y), size=(bw, h))

        # 更新子 widget 位置
        self._header.pos = (x, y)
        self._header.size = (w, self._COLLAPSED_HEIGHT)
        self._content_area.pos = (x, y + self._COLLAPSED_HEIGHT)
        self._content_area.size = (w, self._EXPANDED_HEIGHT - self._COLLAPSED_HEIGHT)
