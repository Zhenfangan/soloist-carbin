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

from app.ui.components.glass_bg import draw_glass_card_bg
from app.ui.components.pixel_button import PixelButton
from app.ui.fonts import emj
from app.ui.tokens import (
    BORDER_WIDTH,
    CARD_PADDING,
    CARD_WHITE,
    COLORS,
    DOPAMINE_COLORS,
    FONT_SIZE_BODY,
    FONT_SIZE_SMALL,
    GRID_UNIT,
    SEMANTIC_COLORS,
    SHADOW_BLACK,
    TEXT_BROWN,
    TEXT_GRAY,
)

PERIOD_LABELS: dict[str, str] = {
    "morning": "上午", "afternoon": "下午", "evening": "晚上", "night": "晚上",
}
PERIOD_ICONS: dict[str, str] = {
    "morning": "[AM]", "afternoon": "[PM]", "evening": "[PM]", "night": "[PM]",
}
PERIOD_TIME_RANGES: dict[str, tuple[str, str]] = {
    "morning": ("09:00", "12:00"), "afternoon": ("14:00", "18:00"),
    "evening": ("", ""), "night": ("", ""),
}


class PeriodCard(BoxLayout):  # type: ignore[misc]
    """时段卡片 — 垂直 BoxLayout: 头部行 + 可展开内容区。

    彻底消除 FloatLayout 手动定位与 do_layout 的竞态。
    """

    _ANIMATION_DURATION = 0.3
    _EXPANDED_HEIGHT = 180
    _COLLAPSED_HEIGHT = 48
    _MASCOT_SIZE = 96        # 1.5× SPRITE_SIZE(64) — 所有动画统一尺寸
    _EXPANDED_HEIGHT_ANIM = 288  # 带吉祥物时的卡片高度 (8 的倍数)

    def __init__(
        self,
        period_name: str = "morning",
        on_checkin: Callable[[str], Any] | None = None,
        on_checkout: Callable[[str], Any] | None = None,
        on_leave: Callable[[str], Any] | None = None,
        is_current: bool = False,
        **kwargs: Any,
    ) -> None:
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("size_hint", (1, None))
        kwargs.setdefault("height", 48)
        super().__init__(**kwargs)

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

        self._period_label = PERIOD_LABELS.get(period_name, period_name)
        self._period_icon = PERIOD_ICONS.get(period_name, "")
        start, end = PERIOD_TIME_RANGES.get(period_name, ("", ""))
        self._start_time = start
        self._end_time = end
        self._mascot_active = False

        # ═══ 头部行 (始终 48px) ═══
        self._header = BoxLayout(
            orientation="horizontal",
            size_hint=(1, None),
            height=self._COLLAPSED_HEIGHT,
            padding=[CARD_PADDING, 0],
            spacing=GRID_UNIT,
        )

        self._icon_label = Label(
            text=self._period_icon,
            font_size=FONT_SIZE_BODY,
            size_hint=(None, 1), width=30,
            halign="center", valign="middle",
        )
        self._name_label = Label(
            text=self._period_label,
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(None, 1), width=50,
            halign="left", valign="middle",
        )
        self._summary_label = Label(
            text=self._get_time_range_text(),
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(1, 1),
            halign="left", valign="middle",
            markup=True,
        )
        # 完成徽章 — 放在 header 内，默认不可见
        self._check_label = Label(
            text="", font_size=FONT_SIZE_BODY,
            color=self._to_rgba(DOPAMINE_COLORS["mint"]["dark"]),
            size_hint=(None, 1), width=120,
            halign="left", valign="middle", opacity=0,
            markup=True,
        )

        self._header.add_widget(self._icon_label)
        self._header.add_widget(self._name_label)
        self._header.add_widget(self._summary_label)
        self._header.add_widget(self._check_label)
        self.add_widget(self._header)

        # ═══ 内容区 (展开时可见) ═══
        self._content_area = BoxLayout(
            orientation="vertical",
            size_hint=(1, None), height=0, opacity=0,
            padding=[CARD_PADDING, GRID_UNIT, CARD_PADDING, GRID_UNIT],
            spacing=GRID_UNIT,
        )

        self._action_btn = PixelButton(
            text=f"{emj('✍️')} 签到", color=COLORS["PRIMARY_YELLOW"],
            size_mode="large", size_hint=(1, None),
            markup=True,
        )
        self._action_btn.bind(on_press=lambda _: self._on_action())
        self._content_area.add_widget(self._action_btn)

        # 请假按钮 — 紧挨签到按钮下方，仅 morning/afternoon 时段显示
        self._can_leave = period_name in ("morning", "afternoon")
        self._leave_btn = PixelButton(
            text=f"{emj('🛌')} 请假",
            color=COLORS["CARD_SHADOW"],
            size_mode="small",
            size_hint=(1, None),
            disabled=True,
            markup=True,
        )
        self._leave_btn.bind(on_press=lambda _b: self._on_leave_press())
        self._content_area.add_widget(self._leave_btn)

        # 吉祥物动画插槽 — FloatLayout 确保吉祥物居中锚定不动
        # 平时 height=0 不占空间，动画时展开并绘制像素边框
        self._mascot_row = FloatLayout(
            size_hint=(1, None),
            height=0,
        )
        self._content_area.add_widget(self._mascot_row)

        self.add_widget(self._content_area)

        # 像素边框绘制
        self.bind(pos=self._redraw, size=self._redraw)

    @staticmethod
    def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
        h = hex_color.lstrip("#")
        return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, alpha)

    def _get_time_range_text(self) -> str:
        if self._start_time and self._end_time:
            return f"{self._start_time}-{self._end_time}"
        return "弹性"

    # ── 属性 ──

    @property
    def card_state(self) -> str: return self._card_state

    @card_state.setter
    def card_state(self, state: str) -> None:
        if state == self._card_state:
            return
        self._card_state = state
        self._update_display()

    @property
    def status(self) -> str: return self._status

    @status.setter
    def status(self, value: str) -> None:
        self._status = value
        self._update_display()

    @property
    def has_checked_in(self) -> bool: return self._has_checked_in
    @has_checked_in.setter
    def has_checked_in(self, value: bool) -> None:
        self._has_checked_in = value
        self._update_display()

    @property
    def has_checked_out(self) -> bool: return self._has_checked_out
    @has_checked_out.setter
    def has_checked_out(self, value: bool) -> None:
        self._has_checked_out = value
        self._update_display()

    @property
    def checkin_time(self) -> str | None: return self._checkin_time
    @checkin_time.setter
    def checkin_time(self, value: str | None) -> None:
        self._checkin_time = value
        self._update_display()

    @property
    def checkout_time(self) -> str | None: return self._checkout_time
    @checkout_time.setter
    def checkout_time(self, value: str | None) -> None:
        self._checkout_time = value
        self._update_display()

    @property
    def leave_enabled(self) -> bool: return self._leave_enabled
    @leave_enabled.setter
    def leave_enabled(self, value: bool) -> None:
        self._leave_enabled = value
        self._update_display()

    @property
    def is_current(self) -> bool: return self._is_current
    @is_current.setter
    def is_current(self, value: bool) -> None:
        self._is_current = value
        self._update_display()

    def set_time_range(self, start: str, end: str) -> None:
        """动态更新时段起止时间（响应用户设置变更）。"""
        self._start_time = start
        self._end_time = end
        self._summary_label.text = self._get_time_range_text()
        self._update_display()

    # ── 展开 / 折叠 / 完成 ──

    def expand(self, animate: bool = True) -> None:
        if self._card_state == "expanded":
            return
        self._card_state = "expanded"
        self._target_height = self._EXPANDED_HEIGHT
        self._animation_start(animate)

    def collapse(self, animate: bool = True) -> None:
        if self._card_state == "collapsed":
            return
        self._card_state = "collapsed"
        self._target_height = self._COLLAPSED_HEIGHT
        self._animation_start(animate)

    def complete(self, animate: bool = True) -> None:
        self._card_state = "completed"
        self._target_height = self._COLLAPSED_HEIGHT
        self._animation_start(animate)

    # ── 动画 ──

    def _cancel_animation(self) -> None:
        for ev in getattr(self, "_anim_events", []):
            Clock.unschedule(ev)
        self._anim_events = []

    def _animation_start(self, animate: bool) -> None:
        self._cancel_animation()
        if not animate:
            self.height = self._target_height
            self._update_display()
            return
        start_h = self.height
        target_h = self._target_height
        diff = target_h - start_h
        steps = max(1, int(abs(diff)) // GRID_UNIT)
        for i in range(steps):
            ev = Clock.schedule_once(
                lambda dt, s=i, total=steps: self._animation_step(s, total, start_h, diff),
                i * self._ANIMATION_DURATION / steps,
            )
            self._anim_events.append(ev)
        ev = Clock.schedule_once(
            lambda dt: self._animation_finalize(target_h),
            self._ANIMATION_DURATION + 0.01,
        )
        self._anim_events.append(ev)

    def _animation_step(self, step: int, total: int, start_h: int, diff: int) -> None:
        progress = (step + 1) / total
        self.height = start_h + int(diff * progress)

    def _animation_finalize(self, target_h: int) -> None:
        self.height = target_h

    # ── 显示更新 ──

    def _is_early_checkout(self) -> bool:
        """签退时间早于时段结束时间。"""
        if not self._checkout_time or not self._end_time:
            return False
        return self._checkout_time[:5] < self._end_time[:5]

    def _is_violation(self) -> bool:
        """有任何违规（迟到 / 早退）。"""
        return self._status in ("late", "early_leave") or self._is_early_checkout()

    def _update_display(self) -> None:
        # 摘要文字
        if self._card_state == "absent":
            self._summary_label.text = f"{emj('🚨')} 旷工"
            self._summary_label.color = self._to_rgba(SEMANTIC_COLORS["absent"]["icon"])
        elif self._card_state == "completed":
            parts = []
            if self._checkin_time:
                parts.append(f"{self._get_status_text()} {self._checkin_time}")
            if self._checkout_time:
                checkout_label = f"{emj('🏃')} 早退" if self._is_early_checkout() else f"{emj('🌙')} 签退"
                parts.append(f"{checkout_label} {self._checkout_time}")
            self._summary_label.text = "  ".join(parts) if parts else f"{emj('✅')} 已完成"
            color = COLORS["PRIMARY_DARK"] if self._is_violation() else DOPAMINE_COLORS["mint"]["dark"]
            self._summary_label.color = self._to_rgba(color)
        elif self._card_state == "expanded":
            self._summary_label.text = self._get_time_range_text()
            self._summary_label.color = self._to_rgba(TEXT_BROWN)
        else:
            self._summary_label.text = self._get_time_range_text()
            self._summary_label.color = self._to_rgba(TEXT_BROWN)

        # 内容区可见性 — 吉祥物动画期间不重置高度
        is_expanded = self._card_state == "expanded"
        if not self._mascot_active:
            self._content_area.height = self._EXPANDED_HEIGHT - self._COLLAPSED_HEIGHT if is_expanded else 0
            self._content_area.opacity = 1.0 if is_expanded else 0

        # 按钮状态 — 旷工时完全隐藏
        if self._card_state == "absent":
            self._action_btn.text = ""
            self._action_btn.disabled = True
            self._action_btn.opacity = 0
            self._action_btn.size_hint_y = None
            self._action_btn.height = 0
        elif self._has_checked_in and not self._has_checked_out:
            self._action_btn.text = f"{emj('✍️')} 签退"
            self._action_btn.set_color(DOPAMINE_COLORS["mint"]["light"])
            self._action_btn.disabled = False
            self._action_btn.opacity = 1
            self._action_btn.size_hint_y = None
            self._action_btn.height = 64
        elif self._has_checked_out:
            self._action_btn.text = ""
            self._action_btn.disabled = True
            self._action_btn.opacity = 0
            self._action_btn.size_hint_y = None
            self._action_btn.height = 0
        else:
            self._action_btn.text = f"{emj('✍️')} 签到"
            self._action_btn.set_color(COLORS["PRIMARY_YELLOW"])
            self._action_btn.disabled = not self._is_current
            self._action_btn.opacity = 1
            self._action_btn.size_hint_y = None
            self._action_btn.height = 64

        # 完成徽章 — 全正常才显示 [OK]，违规只显示状态文字
        if self._card_state == "completed":
            if self._is_violation():
                self._check_label.text = self._get_status_text()
                self._check_label.color = self._to_rgba(COLORS["PRIMARY_DARK"])
            else:
                self._check_label.text = f"{emj('✅')} 完成"
                self._check_label.color = self._to_rgba(DOPAMINE_COLORS["mint"]["dark"])
            self._check_label.opacity = 1.0
        else:
            self._check_label.opacity = 0

        # 请假按钮 — 仅 expanded + morning/afternoon 时段显示
        if self._card_state == "expanded" and self._can_leave:
            self._leave_btn.opacity = 1.0
            if self._leave_enabled:
                self._leave_btn.disabled = False
                self._leave_btn.set_color(DOPAMINE_COLORS["sky"]["light"])
            else:
                self._leave_btn.disabled = True
                self._leave_btn.set_color(COLORS["CARD_SHADOW"])
        else:
            self._leave_btn.opacity = 0
            self._leave_btn.disabled = True

    def _get_status_text(self) -> str:
        status_map = {
            "normal": f"{emj('✅')} 正常",
            "late": f"{emj('⏰')} 迟到",
            "early_leave": f"{emj('🏃')} 早退",
            "absent": f"{emj('🚨')} 旷工",
            "leave": f"{emj('🛌')} 请假",
            "shooting": f"{emj('📸')} 拍摄中",
            "pending": f"{emj('✍️')} 签到",
        }
        return status_map.get(self._status, f"{emj('✍️')} 签到")

    # ── 交互 ──

    def _on_action(self) -> None:
        if self._has_checked_in and not self._has_checked_out:
            if self._on_checkout_cb:
                self._on_checkout_cb(self._period_name)
        else:
            if self._on_checkin_cb:
                self._on_checkin_cb(self._period_name)

    def _on_leave_press(self) -> None:
        if not self._leave_enabled:
            return
        if self._on_leave_cb:
            self._on_leave_cb(self._period_name)

    def set_status_from_period(self, period_status: Any) -> None:
        if period_status is None:
            return
        self._status = period_status.status
        self._checkin_time = period_status.checkin_time
        self._checkout_time = period_status.checkout_time
        self._has_checked_in = period_status.checkin_time is not None
        self._has_checked_out = period_status.checkout_time is not None

        # 优先级 1: 已签到未签退 → 保持 expanded 显示签退按钮
        # (无论 service 判定为 normal/late, 只要还没签退就必须展开)
        if (
            self._has_checked_in
            and not self._has_checked_out
            and period_status.status not in ("leave", "shooting", "absent", "absent_morning", "absent_afternoon")
        ):
            self._card_state = "expanded"
            self._target_height = self._EXPANDED_HEIGHT
            self.height = self._EXPANDED_HEIGHT
        # 优先级 2: 旷工 → 红框折叠
        elif period_status.status in ("absent", "absent_morning", "absent_afternoon"):
            self._card_state = "absent"
            self._target_height = self._COLLAPSED_HEIGHT
            self.height = self._COLLAPSED_HEIGHT
        # 优先级 3: 已完成 (含签退/请假/拍摄) → 折叠绿框
        elif period_status.status in ("normal", "late", "early_leave", "leave", "shooting"):
            self._card_state = "completed"
            self._target_height = self._COLLAPSED_HEIGHT
            self.height = self._COLLAPSED_HEIGHT
        # 优先级 4: 未签到 → 折叠
        elif period_status.status == "pending":
            self._card_state = "collapsed"
            self._target_height = self._COLLAPSED_HEIGHT
            self.height = self._COLLAPSED_HEIGHT
        self._update_display()

    # ── 吉祥物动画 ──

    def show_mascot_widget(self, widget: Any) -> None:
        """在卡片内展示吉祥物动画 widget，同时扩展卡片高度并绘制边框。"""
        self._mascot_active = True
        self._mascot_row.clear_widgets()
        self._mascot_row.add_widget(widget)
        self._mascot_row.height = self._MASCOT_SIZE
        self._content_area.height = self._EXPANDED_HEIGHT_ANIM - self._COLLAPSED_HEIGHT
        self._content_area.opacity = 1.0
        self.height = self._EXPANDED_HEIGHT_ANIM
        # 绑定重绘以更新像素边框
        self._mascot_row.bind(pos=self._draw_mascot_border, size=self._draw_mascot_border)
        self._draw_mascot_border()

    def hide_mascot_widget(self) -> None:
        """移除吉祥物 widget，卡片恢复正常展开高度，清除边框。"""
        self._mascot_row.clear_widgets()
        self._mascot_row.height = 0
        self._mascot_active = False
        self._mascot_row.unbind(pos=self._draw_mascot_border, size=self._draw_mascot_border)
        self._mascot_row.canvas.before.clear()
        self._mascot_row.canvas.after.clear()
        self._content_area.height = self._EXPANDED_HEIGHT - self._COLLAPSED_HEIGHT
        self.height = self._EXPANDED_HEIGHT

    def _draw_mascot_border(self, *args: Any) -> None:
        """在吉祥物行周围绘制像素边框，稳定动画视觉。"""
        self._mascot_row.canvas.before.clear()
        self._mascot_row.canvas.after.clear()
        if not self._mascot_active or self._mascot_row.height <= 0:
            return
        x, y = self._mascot_row.pos
        w, h = self._mascot_row.size
        bw = BORDER_WIDTH
        with self._mascot_row.canvas.before:
            # 内部背景 — 与卡片同色的白底，让动画不穿帮
            Color(*self._to_rgba(CARD_WHITE))
            Rectangle(pos=(x, y), size=(w, h))
            # 像素边框 — 茶色 2px
            Color(*self._to_rgba(TEXT_BROWN, 0.4))
            Rectangle(pos=(x, y), size=(w, bw))
            Rectangle(pos=(x, y + h - bw), size=(w, bw))
            Rectangle(pos=(x, y), size=(bw, h))
            Rectangle(pos=(x + w - bw, y), size=(bw, h))

    # ── 像素边框 ──

    def _redraw(self, *args: Any) -> None:
        x, y = self.pos
        w, h = self.size
        bw = BORDER_WIDTH

        if self._card_state == "expanded":
            border_light, border_dark = "#FFFFFF", COLORS["CARD_SHADOW"]
        elif self._card_state == "completed":
            if self._is_violation():
                border_light, border_dark = COLORS["PRIMARY_YELLOW"], COLORS["PRIMARY_DARK"]
            else:
                border_light, border_dark = DOPAMINE_COLORS["mint"]["light"], DOPAMINE_COLORS["mint"]["dark"]
        elif self._card_state == "absent":
            border_light, border_dark = "#FF8090", "#CC2040"
        else:
            border_light, border_dark = "#FFFFFF", COLORS["CARD_SHADOW"]

        draw_glass_card_bg(self, border_light=border_light, border_dark=border_dark)
