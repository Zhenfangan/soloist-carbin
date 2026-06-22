"""打卡成功反馈面板 — 卡片头部下方的内嵌反馈。

每次签到 / 签退成功后，覆盖在触发的 PeriodCard 头部以下的内容区，
4.5 秒后自动消失。卡片头部（period 名 + 时间范围）始终保留可见，
卡片本身的高度、位置不变。

布局（卡片白底）：
- 左 30%：IP 序列动画（rabbit 日常 / bear 夜间）
- 右 70%：
  - 上半：大字 "签到成功！⭐" / "签退成功！⭐"（上下弹跳）
  - 下半：激励语句（用户自定义优先，否则内置 5 句）
"""

from __future__ import annotations

import random
from collections.abc import Callable
from typing import Any

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label

from app.services.report_service import ENCOURAGEMENTS
from app.ui.assets.loader import SequenceLoader
from app.ui.tokens import (
    CARD_WHITE,
    FONT_SIZE_BODY,
    FONT_SIZE_TITLE,
    PRIMARY_YELLOW,
    TEXT_BROWN,
    TEXT_GRAY,
)

DISPLAY_DURATION = 4.5
IP_FRAME_INTERVAL = 0.25
BOUNCE_HEIGHT = 8
BOUNCE_HALF_DURATION = 0.2
HEADER_HEIGHT = 48  # 与 PeriodCard._COLLAPSED_HEIGHT 一致


def _hex_to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, alpha)


class CheckinSuccessPanel(FloatLayout):  # type: ignore[misc]
    """卡片内嵌的打卡 / 签退成功反馈浮层"""

    def __init__(
        self,
        target_card: Any,
        is_checkin: bool = True,
        is_night: bool = False,
        settings_service: Any = None,
        on_dismiss_callback: Callable[[], Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(size_hint=(None, None), **kwargs)
        self._target_card = target_card
        self._is_checkin = is_checkin
        self._is_night = is_night
        self._settings_service = settings_service
        self._on_dismiss_callback = on_dismiss_callback
        self._frame_event: Any = None
        self._bounce_anim: Animation | None = None
        self._dismissed = False

        # 初次同步位置/大小
        self._sync_to_card()

        # 卡片白底（覆盖原内容区的签到按钮 / 请假标签）
        with self.canvas.before:
            Color(*_hex_to_rgba(CARD_WHITE))
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._redraw_bg, size=self._redraw_bg)

        # 左 30%：IP 动画
        anim_id = "bear" if is_night else "rabbit"
        try:
            self._frames = SequenceLoader.load_sequence(anim_id)
        except Exception:
            self._frames = []
        self._frame_idx = 0
        self._ip_image = Image(
            size_hint=(0.28, 0.85),
            pos_hint={"x": 0.03, "center_y": 0.5},
            allow_stretch=True,
            keep_ratio=True,
        )
        if self._frames:
            self._ip_image.texture = self._frames[0].texture
        self.add_widget(self._ip_image)

        # 右 70% 上半：大字标题（卡片内容区高度约 132px）
        # 使用 unicode ★（U+2605），秋叶圆体原生支持；避免 markup font 标签引起字体文件加载失败
        title_text = "签到成功！★" if is_checkin else "签退成功！★"
        self._title_lbl = Label(
            text=title_text,
            font_size=int(FONT_SIZE_TITLE * 1.5),
            color=_hex_to_rgba(PRIMARY_YELLOW),
            outline_color=_hex_to_rgba(TEXT_BROWN),
            outline_width=2,
            bold=True,
            size_hint=(0.66, 0.45),
            pos_hint={"x": 0.32, "center_y": 0.68},
            halign="center",
            valign="middle",
        )
        self._title_lbl.bind(size=lambda i, _: setattr(i, "text_size", i.size))
        self.add_widget(self._title_lbl)

        # 右 70% 下半：激励语
        message = self._pick_encouragement()
        self._msg_lbl = Label(
            text=message,
            font_size=FONT_SIZE_BODY,
            color=_hex_to_rgba(TEXT_GRAY),
            size_hint=(0.66, 0.35),
            pos_hint={"x": 0.32, "center_y": 0.25},
            halign="center",
            valign="middle",
        )
        self._msg_lbl.bind(size=lambda i, _: setattr(i, "text_size", i.size))
        self.add_widget(self._msg_lbl)

        # 同步：卡片位置/大小变化时跟随
        target_card.bind(pos=self._on_card_changed, size=self._on_card_changed)

    # --------------------------------------------------------------
    # 位置/大小同步（仅覆盖 header 以下的内容区）
    # --------------------------------------------------------------

    def _sync_to_card(self) -> None:
        card = self._target_card
        # 卡片底部在 window 坐标系中的位置（脱离 ScrollView / Screen 嵌套）
        wx, wy = card.to_window(card.x, card.y)
        # 覆盖 card 全宽，高度 = card.height - 头部高度
        new_h = max(0, card.height - HEADER_HEIGHT)
        self.size = (card.width, new_h)
        # y = card.y（底部对齐卡片底部），顶部停在 header 下沿
        self.pos = (wx, wy)

    def _on_card_changed(self, *_args: Any) -> None:
        if self._dismissed:
            return
        self._sync_to_card()

    def _redraw_bg(self, *_args: Any) -> None:
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size

    # --------------------------------------------------------------
    # 内容
    # --------------------------------------------------------------

    def _pick_encouragement(self) -> str:
        user_items: list[str] = []
        if self._settings_service:
            try:
                user_items = self._settings_service.get_user_encouragements()
            except Exception:
                user_items = []
        pool = user_items if user_items else ENCOURAGEMENTS
        return random.choice(pool)

    # --------------------------------------------------------------
    # 生命周期
    # --------------------------------------------------------------

    def open(self) -> None:
        Window.add_widget(self)
        Clock.schedule_once(self._start_title_bounce, 0.05)
        Clock.schedule_once(self._auto_dismiss, DISPLAY_DURATION)
        if self._frames and len(self._frames) > 1:
            self._frame_event = Clock.schedule_interval(
                self._advance_frame, IP_FRAME_INTERVAL
            )

    def _advance_frame(self, dt: float) -> None:
        if not self._frames:
            return
        self._frame_idx = (self._frame_idx + 1) % len(self._frames)
        self._ip_image.texture = self._frames[self._frame_idx].texture

    def _start_title_bounce(self, dt: float) -> None:
        original_y = self._title_lbl.y
        anim = (
            Animation(y=original_y + BOUNCE_HEIGHT, duration=BOUNCE_HALF_DURATION, t="out_quad")
            + Animation(y=original_y, duration=BOUNCE_HALF_DURATION, t="in_quad")
        )
        anim.repeat = True
        anim.start(self._title_lbl)
        self._bounce_anim = anim

    def _auto_dismiss(self, dt: float) -> None:
        if self._dismissed:
            return
        self._dismissed = True
        if self._frame_event:
            self._frame_event.cancel()
            self._frame_event = None
        if self._bounce_anim:
            self._bounce_anim.cancel(self._title_lbl)
            self._bounce_anim = None
        try:
            self._target_card.unbind(pos=self._on_card_changed, size=self._on_card_changed)
        except Exception:
            pass
        if self.parent is Window:
            Window.remove_widget(self)
        if self._on_dismiss_callback:
            try:
                self._on_dismiss_callback()
            except Exception:
                pass
