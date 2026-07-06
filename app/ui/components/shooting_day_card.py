"""ShootingDayCard — 拍摄日卡片。

在签到页替代三个时段卡的位置，随拍摄日状态在 3 态间切换：
- idle:   非拍摄日 —— 提示 + "设为拍摄日" 按钮(仅上午上班前可点)
- active: 拍摄进行中 —— 小猫庆祝动画 + "完成拍摄" + "拍张现场" + (窗口内)"取消"
- done:   复盘已完成 —— "已完成 ✓" + 一句鼓励语(不再放"查看战报"按钮,
          避免与页面底部"结束今日并查看战报"大按钮重复; 战报统一走底部大按钮)

主按钮回调按当前状态派发，避免频繁重绑。active 态卡片加高以容纳小猫动画。
鼓励语优先取用户在设置里自定义的激励句(get_user_encouragements), 否则用内置。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

from app.ui.components.glass_bg import draw_glass_card_bg
from app.ui.components.pixel_button import PixelButton
from app.ui.components.sequence_sprite import SequenceSprite
from app.ui.tokens import (
    CARD_PADDING,
    CARD_SHADOW,
    COLORS,
    FONT_SIZE_BODY,
    GRID_UNIT,
    SEMANTIC_COLORS,
    TEXT_BROWN,
)

_SHOOTING_COLOR = SEMANTIC_COLORS["shooting"]["border"]   # 暖橙
_DONE_COLOR = SEMANTIC_COLORS["completed"]["border"]      # 薄荷绿

_BASE_H = 110
_ANIM_H = 88
_ACTIVE_H = _BASE_H + _ANIM_H   # 动画区从 0 展开为 _ANIM_H，spacing 数量不变

_STATE_TEXT = {
    "idle": ("今天是拍摄日吗？", "设为拍摄日", _SHOOTING_COLOR),
    "active": ("● 今天是拍摄日", "完成拍摄", COLORS["PRIMARY_YELLOW"]),
    # done 态不再有主按钮(查看战报走底部大按钮), 第二项留空占位
    "done": ("拍摄复盘已完成 ✓", "", _DONE_COLOR),
}


class ShootingDayCard(BoxLayout):  # type: ignore[misc]
    """拍摄日卡片 — 垂直 BoxLayout: 提示行 + 动画区 + 按钮行。"""

    def __init__(
        self,
        on_set: Callable[[], Any] | None = None,
        on_complete: Callable[[], Any] | None = None,
        on_cancel: Callable[[], Any] | None = None,
        on_capture: Callable[[], Any] | None = None,
        settings_service: Any = None,
        **kwargs: Any,
    ) -> None:
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("size_hint", (1, None))
        kwargs.setdefault("height", _BASE_H)
        kwargs.setdefault("padding", [CARD_PADDING, GRID_UNIT])
        kwargs.setdefault("spacing", GRID_UNIT)
        super().__init__(**kwargs)

        self._on_set = on_set
        self._on_complete = on_complete
        self._on_cancel = on_cancel
        self._on_capture = on_capture
        self._settings_service = settings_service
        self._state = "idle"
        self._can_cancel = False
        self._encouragement_text = ""  # done 态显示, 进入 done 时抽一次并缓存

        self._hint_label = Label(
            text=_STATE_TEXT["idle"][0],
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(1, None),
            height=30,
            halign="center",
            valign="middle",
        )
        self.add_widget(self._hint_label)

        # done 态鼓励语(替代原"查看战报"按钮), 其余状态高度归零不占位
        self._encourage_label = Label(
            text="",
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(_DONE_COLOR),
            size_hint=(1, None),
            height=0,
            opacity=0,
            halign="center",
            valign="middle",
        )
        self._encourage_label.bind(
            size=lambda i, _v: setattr(i, "text_size", (i.width, None))
        )
        self.add_widget(self._encourage_label)

        # 小猫庆祝动画区(仅 active 展开)
        self._anim_wrap = AnchorLayout(
            size_hint=(1, None),
            height=0,
            anchor_x="center",
            anchor_y="center",
        )
        self._anim = SequenceSprite(
            "cat",
            fps=4.0,  # 与战报 report_preview._start_frame_anim 的节奏保持一致
            bubble_indices={1, 3, 4},
            loop_pause=2.0,
            autoplay=False,
            size_hint=(None, None),
            size=(_ANIM_H, _ANIM_H),
        )
        self._anim_wrap.add_widget(self._anim)
        self._anim_wrap.opacity = 0.0
        self.add_widget(self._anim_wrap)

        btn_row = BoxLayout(
            orientation="horizontal",
            size_hint=(1, None),
            height=48,
            spacing=GRID_UNIT,
        )
        self._primary_btn = PixelButton(
            text=_STATE_TEXT["idle"][1],
            color=_SHOOTING_COLOR,
            size_mode="small",
            font_size=FONT_SIZE_BODY,
            size_hint=(1, None),
        )
        self._primary_btn.bind(on_press=lambda _w: self._on_primary())
        self._capture_btn = PixelButton(
            text="拍张现场",
            color=_SHOOTING_COLOR,
            size_mode="small",
            font_size=FONT_SIZE_BODY,
            size_hint=(1, None),
        )
        self._capture_btn.bind(on_press=lambda _w: self._on_capture_pressed())
        self._cancel_btn = PixelButton(
            text="取消",
            color=CARD_SHADOW,
            size_mode="small",
            font_size=FONT_SIZE_BODY,
            size_hint=(1, None),
        )
        self._cancel_btn.bind(on_press=lambda _w: self._on_cancel_pressed())
        self._btn_row = btn_row
        btn_row.add_widget(self._primary_btn)
        btn_row.add_widget(self._capture_btn)
        btn_row.add_widget(self._cancel_btn)
        self.add_widget(btn_row)

        self.bind(pos=self._redraw_bg, size=self._redraw_bg)
        self.set_state("idle")

    # ── 状态机 ────────────────────────────────────────────

    def set_state(self, state: str, can_cancel: bool = False) -> None:
        """切换卡片状态。can_cancel 仅在 active 且仍在取消窗口内为 True。"""
        prev = self._state
        self._state = state if state in _STATE_TEXT else "idle"
        self._can_cancel = can_cancel and self._state == "active"
        # 首次进入 done 才抽一句鼓励语并缓存, 避免每次刷新(切 tab)都换一句抖动
        if self._state == "done" and (prev != "done" or not self._encouragement_text):
            self._encouragement_text = self._pick_encouragement()
        self._update_display()

    def _pick_encouragement(self) -> str:
        """抽一句鼓励语: 用户在设置里自定义的优先, 否则用战报内置池。"""
        import random

        from app.services.report_service import ENCOURAGEMENTS
        pool: list[str] = []
        if self._settings_service:
            try:
                pool = self._settings_service.get_user_encouragements()
            except Exception:
                pool = []
        return random.choice(pool or ENCOURAGEMENTS)

    @property
    def natural_height(self) -> int:
        """当前状态下卡片应有的高度(供外部显隐时设置，避免硬编码覆盖)。"""
        return _ACTIVE_H if self._state == "active" else _BASE_H

    def _update_display(self) -> None:
        hint, primary_text, primary_color = _STATE_TEXT[self._state]
        self._hint_label.text = hint
        self._primary_btn.text = primary_text
        self._primary_btn.set_color(primary_color)

        is_active = self._state == "active"
        is_done = self._state == "done"
        # 小猫动画：仅 active 展开并播放
        self._anim_wrap.opacity = 1.0 if is_active else 0.0
        self._anim_wrap.height = _ANIM_H if is_active else 0
        if is_active:
            self._anim.play()
        else:
            self._anim.stop()

        # done 态: 隐藏整排按钮, 改显鼓励语; 其余状态: 隐藏鼓励语显示按钮
        if is_done:
            self._encourage_label.text = self._encouragement_text
            self._encourage_label.height = 40
            self._encourage_label.opacity = 1.0
        else:
            self._encourage_label.text = ""
            self._encourage_label.height = 0
            self._encourage_label.opacity = 0.0

        # 拍张现场：仅 active
        self._set_btn_visible(self._capture_btn, is_active)
        # 取消：active 且仍在窗口内
        self._set_btn_visible(self._cancel_btn, self._can_cancel)

        # 隐藏的按钮必须从 btn_row 移除, 而不是只置 width=0 —— 否则 BoxLayout
        # 的 spacing 仍会在"隐藏位"上计入间距, 挤占 primary_btn 的宽度,
        # 导致按钮右边缘对不齐同一屏幕上的其他卡片(如签到按钮)。
        # done 态整排按钮都不加(战报走底部大按钮)。
        self._btn_row.clear_widgets()
        self._btn_row.height = 0 if is_done else 48
        if not is_done:
            self._btn_row.add_widget(self._primary_btn)
            if is_active:
                self._btn_row.add_widget(self._capture_btn)
            if self._can_cancel:
                self._btn_row.add_widget(self._cancel_btn)

        self.height = self.natural_height

    @staticmethod
    def _set_btn_visible(btn: PixelButton, show: bool) -> None:
        btn.opacity = 1.0 if show else 0.0
        btn.disabled = not show
        btn.size_hint_x = 1 if show else None
        if not show:
            btn.width = 0

    # ── 回调派发 ──────────────────────────────────────────

    def _on_primary(self) -> None:
        # done 态无主按钮(已从 btn_row 移除), 只 idle/active 派发
        cb = {
            "idle": self._on_set,
            "active": self._on_complete,
        }.get(self._state)
        if cb:
            cb()

    def _on_capture_pressed(self) -> None:
        if self._on_capture:
            self._on_capture()

    def _on_cancel_pressed(self) -> None:
        if self._on_cancel:
            self._on_cancel()

    # ── 绘制 ──────────────────────────────────────────────

    def _redraw_bg(self, *_args: Any) -> None:
        draw_glass_card_bg(self, border_light="#FFFFFF", border_dark="#C8D8E0")

    @staticmethod
    def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
        h = hex_color.lstrip("#")
        return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, alpha)
