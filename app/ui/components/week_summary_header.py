"""WeekSummaryHeader — 本周总结浮层（薄荷绿双框像素风格）。

布局: 左侧三行文字（已完成超额 / 大百分比 / 预计奖励）| 右侧小狗摘星星（跳动动画）
高度 144px，卡片内绘制阴影（不超出 widget bounds）。
"""

from __future__ import annotations

from typing import Any

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label

from app.ui.tokens import (
    DOPAMINE_COLORS,
    FONT_SIZE_BODY,
    FONT_SIZE_TITLE,
    GRID_UNIT,
    PRIMARY_YELLOW,
    SHADOW_BLACK,
)

# IP 动画帧统一存于 app/ui/assets/animations/dog/frame_NN.png (ASCII 路径)。
# 原 doc/ui-design/.../小狗摘星星/ 中文路径在安卓真机上无法解析 (桌面端因
# CWD=项目根凑巧能找到, 真机贴图为空 → 渲染成白方块), 故改用规范化副本。
_DOG_FRAMES = [
    f"app/ui/assets/animations/dog/frame_{i:02d}.png"
    for i in range(1, 8)
]
_DOG_FPS = 4
_DOG_LOOP_PAUSE = 3.0

# 薄荷绿双框配色（参考战报 afternoon slot）
_C_OUTER  = "#50E8B0"   # 外框
_C_INNER  = "#A8F4D8"   # 内框
_C_BG     = "#C8F5EC"   # 内容底色
_C_SHADOW = "#28C888"   # 内阴影（右下偏移 3px，不超出 bounds）
_C_TEXT   = "#1A1A1A"   # 正文黑
_C_RATE   = "#0D4A2F"   # 百分比深绿（在薄荷底上更清晰）

# 滞纳期警告配色
_L_OUTER  = "#FF6B8A"   # 珊瑚红外框
_L_INNER  = "#FFB3C6"   # 浅珊瑚内框
_L_BG     = "#FFD4DE"   # 粉底
_L_SHADOW = "#E05070"   # 深珊瑚阴影
_L_RATE   = "#8B1030"   # 深红百分比


class WeekSummaryHeader(FloatLayout):  # type: ignore[misc]
    """本周总结浮层。"""

    PAGE_PADDING: int = GRID_UNIT * 2

    def __init__(self, summary: dict[str, object] | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = 144
        self._summary: dict[str, object] = summary or {}
        self._dog_frame_idx = 0
        self._dog_anim_event: object = None
        self._dog_base_y: float = 0.0

        # ── 三行文字 (均占左侧全宽，白色描边防马赛克底色干扰) ─────────
        # 第1行: 已完成/超额（顶部）
        self._completed_label = Label(
            text="",
            font_size=FONT_SIZE_BODY + 4,
            color=self._to_rgba(_C_TEXT),
            size_hint=(None, None),
            halign="left",
            valign="middle",
            outline_color=(1, 1, 1, 1),
            outline_width=2,
        )
        # 第2行: 完成率大字（中部）
        self._rate_label = Label(
            text="0%",
            font_size=FONT_SIZE_TITLE * 4,   # 72 px
            color=self._to_rgba(_C_RATE),
            size_hint=(None, None),
            halign="left",
            valign="middle",
            bold=True,
            outline_color=(1, 1, 1, 1),
            outline_width=2,
        )
        # 第3行: 预计奖励（底部）
        self._reward_label = Label(
            text="",
            font_size=FONT_SIZE_BODY + 4,
            color=self._to_rgba(_C_TEXT),
            size_hint=(None, None),
            halign="left",
            valign="middle",
            outline_color=(1, 1, 1, 1),
            outline_width=2,
        )

        # ── 右侧小狗动画 ──────────────────────────────────────────────
        self._dog_img = Image(
            source=_DOG_FRAMES[0],
            size_hint=(None, None),
            fit_mode="contain",
        )

        self.add_widget(self._completed_label)
        self.add_widget(self._rate_label)
        self.add_widget(self._reward_label)
        self.add_widget(self._dog_img)

        self.bind(pos=self._redraw, size=self._redraw)

        if summary:
            self.update_summary(summary, animate=False)

        Clock.schedule_once(lambda dt: self._start_dog_animation(), 0.3)

    @staticmethod
    def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
        h = hex_color.lstrip("#")
        return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0,
                int(h[4:6], 16) / 255.0, alpha)

    # ── 小狗逐帧动画 ─────────────────────────────────────────────────

    def _start_dog_animation(self) -> None:
        self._dog_frame_idx = 0
        self._play_dog_frame()

    def _play_dog_frame(self) -> None:
        if self._dog_frame_idx < len(_DOG_FRAMES):
            self._dog_img.source = _DOG_FRAMES[self._dog_frame_idx]
            self._dog_frame_idx += 1
            self._dog_anim_event = Clock.schedule_once(
                lambda dt: self._play_dog_frame(), 1.0 / _DOG_FPS
            )
        else:
            self._dog_anim_event = Clock.schedule_once(
                lambda dt: self._start_dog_animation(), _DOG_LOOP_PAUSE
            )

    # ── 跳动动画 ─────────────────────────────────────────────────────

    def _start_bounce(self) -> None:
        Animation.cancel_all(self._dog_img, "y")
        bounce = (
            Animation(y=self._dog_base_y + 8, duration=0.32, t="out_sine")
            + Animation(y=self._dog_base_y, duration=0.32, t="in_sine")
        )
        bounce.repeat = True
        bounce.start(self._dog_img)

    # ── 数据更新 ─────────────────────────────────────────────────────

    def update_summary(self, summary: dict[str, object], animate: bool = True) -> None:
        self._summary = summary
        completed = int(summary.get("completed", 0))
        extra_count = int(summary.get("extra_count", 0))
        total_reward = float(summary.get("total_reward", 0.0))
        completion_rate = float(summary.get("completion_rate", 0.0))
        status = str(summary.get("status", "active"))
        accrued_late_fees = float(summary.get("accrued_late_fees", 0) or 0)
        self._is_late = status == "late"

        if not animate:
            self._completed_label.text = f"已完成 {completed}  超额 {extra_count}"
            if self._is_late:
                self._reward_label.text = f"滞纳中 · 已累积 -{int(accrued_late_fees)}"
            else:
                self._reward_label.text = f"预计奖励: {int(total_reward):+d}"
            self._rate_label.text = f"{int(completion_rate)}%"
            self._redraw()
            return

        self._animate_count(completed, extra_count)
        self._animate_reward(total_reward)
        self._animate_rate(completion_rate)

    def _animate_count(self, new_c: int, new_e: int) -> None:
        steps, interval = 10, 0.03
        for i in range(steps + 1):
            p = i / steps
            c, e = int(new_c * p), int(new_e * p)
            Clock.schedule_once(
                lambda dt, cc=c, ee=e: setattr(
                    self._completed_label, "text", f"已完成 {cc}  超额 {ee}"
                ),
                i * interval,
            )

    def _animate_reward(self, new_val: float) -> None:
        steps, interval = 10, 0.03
        for i in range(steps + 1):
            v = new_val * (i / steps)
            if self._is_late:
                accrued = float(self._summary.get("accrued_late_fees", 0) or 0)
                Clock.schedule_once(
                    lambda dt, vv=int(accrued * (i / steps)): setattr(
                        self._reward_label, "text", f"滞纳中 · 已累积 -{vv}"
                    ),
                    i * interval,
                )
            else:
                sign = "+" if v >= 0 else ""
                Clock.schedule_once(
                    lambda dt, s=sign, vv=int(v): setattr(
                        self._reward_label, "text", f"预计奖励: {s}{vv}"
                    ),
                    i * interval,
                )

    def _animate_rate(self, new_val: float) -> None:
        steps, interval = 10, 0.03
        for i in range(steps + 1):
            v = new_val * (i / steps)
            Clock.schedule_once(
                lambda dt, vv=int(v): setattr(self._rate_label, "text", f"{vv}%"),
                i * interval,
            )

    # ── 绘制 + 布局 ─────────────────────────────────────────────────

    def _redraw(self, *args: Any) -> None:
        """薄荷绿双层像素边框卡片（内阴影，不超出 bounds）。
        滞纳期使用珊瑚红警告配色。
        """
        self.canvas.before.clear()
        x, y = self.pos
        w, h = self.size

        is_late = getattr(self, "_is_late", False)
        outer = _L_OUTER if is_late else _C_OUTER
        inner = _L_INNER if is_late else _C_INNER
        bg = _L_BG if is_late else _C_BG
        shadow = _L_SHADOW if is_late else _C_SHADOW
        rate_color = _L_RATE if is_late else _C_RATE

        with self.canvas.before:
            # 内阴影：偏移 3px（右下，保持在 bounds 内）
            Color(*self._to_rgba(shadow, 0.45))
            Rectangle(pos=(x + 3, y), size=(w - 3, h - 3))

            # 外框
            Color(*self._to_rgba(outer))
            Rectangle(pos=(x, y + 3), size=(w - 3, h - 3))

            # 内框
            Color(*self._to_rgba(inner))
            Rectangle(pos=(x + 3, y + 6), size=(w - 9, h - 9))

            # 内容底色
            Color(*self._to_rgba(bg))
            Rectangle(pos=(x + 6, y + 9), size=(w - 15, h - 15))

        self._rate_label.color = self._to_rgba(rate_color)
        self._reposition_labels()

    def _reposition_labels(self, *args: Any) -> None:
        """布局: 右侧小狗 | 左侧三行文字（共用左侧宽度）。"""
        w = self.width
        h = self.height
        pad = 14

        # ── 右侧小狗 ──────────────────────────────────────────────
        dog_size = int(h * 0.90)
        dog_x = self.x + w - dog_size - pad
        new_base_y = self.y + (h - dog_size) / 2

        self._dog_img.size = (dog_size, dog_size)
        if abs(new_base_y - self._dog_base_y) > 0.5:
            self._dog_base_y = new_base_y
            self._dog_img.pos = (dog_x, new_base_y)
            Clock.schedule_once(lambda dt: self._start_bounce(), 0)
        else:
            self._dog_img.x = dog_x

        # ── 左侧文字列（从 pad 到 dog_x - pad，共用同一宽度）──────
        text_w = dog_x - self.x - pad * 2
        lbl_x = self.x + pad

        # 第2行: 大百分比（垂直居中，h*0.55 高）
        rate_h = int(h * 0.55)
        rate_y = self.y + (h - rate_h) / 2
        self._rate_label.pos = (lbl_x, rate_y)
        self._rate_label.size = (text_w, rate_h)
        self._rate_label.text_size = (text_w, rate_h)

        # 第1行: 已完成/超额（大百分比上方，距顶 10px）
        small_h = FONT_SIZE_BODY + 8  # 22px 行高
        self._completed_label.pos = (lbl_x, self.y + h - small_h - 10)
        self._completed_label.size = (text_w, small_h)
        self._completed_label.text_size = (text_w, small_h)

        # 第3行: 预计奖励（大百分比下方，距底 10px）
        self._reward_label.pos = (lbl_x, self.y + 10)
        self._reward_label.size = (text_w, small_h)
        self._reward_label.text_size = (text_w, small_h)
