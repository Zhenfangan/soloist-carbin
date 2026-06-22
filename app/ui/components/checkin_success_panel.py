"""打卡成功反馈面板 — 覆盖在目标 PeriodCard 之上的浮层。

每次签到 / 签退成功后，在触发的 PeriodCard 当前可视区域内显示反馈，
4.5 秒后自动消失。PeriodCard 本身的大小、位置不会改变；面板只是
通过 Window.add_widget 加在 Window 顶层、pos/size 跟随 PeriodCard 同步。

布局（限制在卡片内部）：
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
from app.ui.tokens import FONT_SIZE_BODY, FONT_SIZE_SMALL, FONT_SIZE_TITLE

DISPLAY_DURATION = 4.5
IP_FRAME_INTERVAL = 0.25
BOUNCE_HEIGHT = 8
BOUNCE_HALF_DURATION = 0.2


class CheckinSuccessPanel(FloatLayout):  # type: ignore[misc]
    """打卡 / 签退成功后的卡片内反馈浮层"""

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

        # 同步初始位置/大小到目标卡片
        self._sync_to_card()

        # 半透明背景（绑定到 FloatLayout 自身）
        with self.canvas.before:
            Color(0, 0, 0, 0.65)
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
            size_hint=(0.3, 0.85),
            pos_hint={"x": 0.02, "center_y": 0.5},
            allow_stretch=True,
            keep_ratio=True,
        )
        if self._frames:
            self._ip_image.texture = self._frames[0].texture
        self.add_widget(self._ip_image)

        # 右 70% 上半：大字标题（适配卡片高度 ~180px，字号取 TITLE 即可）
        title_text = "签到成功！⭐" if is_checkin else "签退成功！⭐"
        self._title_lbl = Label(
            text=title_text,
            font_size=FONT_SIZE_TITLE,
            color=(1, 1, 1, 1),
            bold=True,
            size_hint=(0.66, 0.4),
            pos_hint={"x": 0.32, "center_y": 0.65},
            halign="center",
            valign="middle",
        )
        self._title_lbl.bind(size=lambda i, _: setattr(i, "text_size", i.size))
        self.add_widget(self._title_lbl)

        # 右 70% 下半：激励语
        message = self._pick_encouragement()
        self._msg_lbl = Label(
            text=message,
            font_size=FONT_SIZE_SMALL,
            color=(1, 1, 1, 0.92),
            size_hint=(0.66, 0.35),
            pos_hint={"x": 0.32, "center_y": 0.28},
            halign="center",
            valign="middle",
        )
        self._msg_lbl.bind(size=lambda i, _: setattr(i, "text_size", i.size))
        self.add_widget(self._msg_lbl)

        # 跟随目标卡片位置/大小变化（滚动、布局重排时同步）
        target_card.bind(pos=self._on_card_changed, size=self._on_card_changed)

    # --------------------------------------------------------------
    # 位置/大小同步
    # --------------------------------------------------------------

    def _sync_to_card(self) -> None:
        card = self._target_card
        # 卡片的 window 坐标（脱离 ScrollView / Screen 嵌套）
        wx, wy = card.to_window(card.x, card.y)
        self.size = (card.width, card.height)
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
        """挂到 Window 顶层 + 启动动画 + 定时关闭"""
        Window.add_widget(self)
        # 延一帧启动跳动，确保 FloatLayout 已为 title 计算 y
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
        # 解绑目标卡片，避免引用泄漏
        try:
            self._target_card.unbind(pos=self._on_card_changed, size=self._on_card_changed)
        except Exception:
            pass
        # 从 Window 移除
        if self.parent is Window:
            Window.remove_widget(self)
        if self._on_dismiss_callback:
            try:
                self._on_dismiss_callback()
            except Exception:
                pass
