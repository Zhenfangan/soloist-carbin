"""打卡成功反馈面板 — 全屏浮层。

每次签到 / 签退成功后弹出，4.5 秒后自动关闭。
布局：
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
from kivy.graphics import Color, Rectangle
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView

from app.services.report_service import ENCOURAGEMENTS
from app.ui.assets.loader import SequenceLoader
from app.ui.tokens import FONT_SIZE_BODY, FONT_SIZE_TITLE

DISPLAY_DURATION = 4.5
IP_FRAME_INTERVAL = 0.25
BOUNCE_HEIGHT = 12
BOUNCE_HALF_DURATION = 0.2


class CheckinSuccessPanel(ModalView):  # type: ignore[misc]
    """打卡 / 签退成功后的全屏反馈面板"""

    def __init__(
        self,
        is_checkin: bool = True,
        is_night: bool = False,
        settings_service: Any = None,
        on_dismiss_callback: Callable[[], Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            size_hint=(1, 1),
            background="",
            background_color=(0, 0, 0, 0),
            auto_dismiss=False,
            **kwargs,
        )
        self._is_checkin = is_checkin
        self._is_night = is_night
        self._settings_service = settings_service
        self._on_dismiss_callback = on_dismiss_callback
        self._frame_event: Any = None
        self._bounce_anim: Animation | None = None

        # 半透明黑色遮罩
        with self.canvas.before:
            Color(0, 0, 0, 0.7)
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._redraw_bg, size=self._redraw_bg)

        root = FloatLayout()

        # 左 30%：IP 动画
        anim_id = "bear" if is_night else "rabbit"
        try:
            self._frames = SequenceLoader.load_sequence(anim_id)
        except Exception:
            self._frames = []
        self._frame_idx = 0
        self._ip_image = Image(
            size_hint=(0.3, 0.6),
            pos_hint={"x": 0.0, "center_y": 0.5},
            allow_stretch=True,
            keep_ratio=True,
        )
        if self._frames:
            self._ip_image.texture = self._frames[0].texture
        root.add_widget(self._ip_image)

        # 右 70% 上半：大字标题
        title_text = "签到成功！⭐" if is_checkin else "签退成功！⭐"
        self._title_lbl = Label(
            text=title_text,
            font_size=int(FONT_SIZE_TITLE * 1.6),
            color=(1, 1, 1, 1),
            bold=True,
            size_hint=(0.65, 0.25),
            pos_hint={"x": 0.32, "center_y": 0.6},
            halign="center",
            valign="middle",
        )
        self._title_lbl.bind(size=lambda i, _: setattr(i, "text_size", i.size))
        root.add_widget(self._title_lbl)

        # 右 70% 下半：激励语
        message = self._pick_encouragement()
        msg_lbl = Label(
            text=message,
            font_size=FONT_SIZE_BODY,
            color=(1, 1, 1, 0.9),
            size_hint=(0.65, 0.22),
            pos_hint={"x": 0.32, "center_y": 0.38},
            halign="center",
            valign="middle",
        )
        msg_lbl.bind(size=lambda i, _: setattr(i, "text_size", i.size))
        root.add_widget(msg_lbl)

        self.add_widget(root)

    def _redraw_bg(self, *_args: Any) -> None:
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size

    def _pick_encouragement(self) -> str:
        user_items: list[str] = []
        if self._settings_service:
            try:
                user_items = self._settings_service.get_user_encouragements()
            except Exception:
                user_items = []
        pool = user_items if user_items else ENCOURAGEMENTS
        return random.choice(pool)

    def on_open(self) -> None:  # type: ignore[override]
        # 延迟一帧启动跳动，确保 FloatLayout 已为 title 计算 y
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
        if self._frame_event:
            self._frame_event.cancel()
            self._frame_event = None
        if self._bounce_anim:
            self._bounce_anim.cancel(self._title_lbl)
            self._bounce_anim = None
        self.dismiss()
        if self._on_dismiss_callback:
            try:
                self._on_dismiss_callback()
            except Exception:
                pass
