"""打卡成功反馈面板 — 卡片头部下方的内嵌反馈。

每次签到 / 签退成功后，覆盖在触发的 PeriodCard 头部以下的内容区，
~4.5 秒后自动消失。卡片头部（period 名 + 时间范围）始终保留可见，
卡片本身的高度、位置不变。

面板自己不画背景 —— 卡片本身的玻璃背景就是它的底；同时把卡片原本
的签到 / 请假按钮隐藏；滚动时自动跟随卡片位置。

布局：
- 左 30%：IP 序列动画（rabbit 日常 / bear 夜间）
- 右 70%：
  - 上半：大字 "签到成功！★" / "签退成功！★"（上下弹跳）
  - 下半：激励语句（用户自定义优先，否则内置 5 句）
"""

from __future__ import annotations

import random
from collections.abc import Callable
from typing import Any

from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label

from app.services.report_service import ENCOURAGEMENTS
from app.ui.assets.loader import SequenceLoader
from app.ui.tokens import (
    FONT_SIZE_BODY,
    FONT_SIZE_TITLE,
    PRIMARY_YELLOW,
    TEXT_BROWN,
)

ANIM_SPEED = 1.5  # 帧序列播放倍速 (1.0=原速, >1=加速)
DISPLAY_DURATION = 4.5  # 总时长匹配帧序列加速后: (0.3+0.7×3+1.3×3)/1.5 ≈ 4.2s + 末帧驻留
BOUNCE_HEIGHT = 8
BOUNCE_HALF_DURATION = 0.2
HEADER_HEIGHT = 48  # 与 PeriodCard._COLLAPSED_HEIGHT 一致


def _hex_to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, alpha)


class CheckinSuccessPanel(FloatLayout):  # type: ignore[misc]
    """卡片内嵌的打卡 / 签退成功反馈浮层 —— 透明背景，使用卡片自身玻璃。"""

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
        self._frame_event: Any = None  # 兼容旧逻辑，改用 _next_frame_event 链式调度
        self._next_frame_event: Any = None
        self._bounce_anim: Animation | None = None
        self._dismissed = False
        self._hidden_widgets: list[tuple[Any, float]] = []
        self._bound_scrollview: Any = None

        # 初次同步位置/大小
        self._sync_to_card()

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

        # 右 70% 上半：大字标题
        title_text = "签到成功！★" if is_checkin else "签退成功！★"
        self._title_lbl = Label(
            text=title_text,
            font_size=int(FONT_SIZE_TITLE * 1.5),
            color=_hex_to_rgba(PRIMARY_YELLOW),
            outline_color=_hex_to_rgba(TEXT_BROWN),
            outline_width=2,
            bold=True,
            size_hint=(0.66, 0.38),
            pos_hint={"x": 0.32, "center_y": 0.74},
            halign="center",
            valign="middle",
        )
        self._title_lbl.bind(size=lambda i, _: setattr(i, "text_size", i.size))
        self.add_widget(self._title_lbl)

        # 右 70% 下半：激励语 (与标题间距充足，避免重叠)
        message = self._pick_encouragement()
        self._msg_lbl = Label(
            text=message,
            font_size=FONT_SIZE_BODY,
            color=_hex_to_rgba(TEXT_BROWN),
            size_hint=(0.66, 0.32),
            pos_hint={"x": 0.32, "center_y": 0.20},
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

    @staticmethod
    def _overlay_container() -> Any:
        """挂载目标: 优先挂到 main.py 暴露的 root_scatter(随整体缩放变换),
        取不到时(如独立单测)退回裸 Window。"""
        app = App.get_running_app()
        container = getattr(app, "_root_scatter", None)
        return container if container is not None else Window

    def _sync_to_card(self) -> None:
        card = self._target_card
        container = self._overlay_container()
        # to_window 顺着父级链(含 ScrollView 滚动偏移 + Scatter 缩放)算出窗口坐标;
        # 再用 container.to_widget 转回 container 的本地坐标系, 使 pos 在缩放后的
        # 设计画布坐标系下才是正确的(否则挂到裸 Window 上时 to_window 的位置虽准,
        # 但 size 仍是未缩放的逻辑尺寸, 真机上会显得极小)。
        wx, wy = card.to_window(card.x, card.y)
        if container is not Window:
            wx, wy = container.to_widget(wx, wy)
        new_h = max(0, card.height - HEADER_HEIGHT)
        self.size = (card.width, new_h)
        self.pos = (wx, wy)

    def _on_card_changed(self, *_args: Any) -> None:
        if self._dismissed:
            return
        self._sync_to_card()

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
        self._container = self._overlay_container()
        self._container.add_widget(self)
        self._sync_to_card()
        # 隐藏底下卡片的签到 / 请假按钮，避免半透明玻璃透出
        for attr in ("_action_btn", "_leave_btn"):
            w = getattr(self._target_card, attr, None)
            if w is not None:
                self._hidden_widgets.append((w, w.opacity))
                w.opacity = 0
        # 跟随滚动：找到上层 ScrollView 并绑定 scroll_y / scroll_x
        parent = self._target_card.parent
        while parent is not None:
            if hasattr(parent, "scroll_y"):
                self._bound_scrollview = parent
                parent.bind(scroll_y=self._on_scroll_changed, scroll_x=self._on_scroll_changed)
                break
            parent = parent.parent
        Clock.schedule_once(self._start_title_bounce, 0.05)
        Clock.schedule_once(self._auto_dismiss, DISPLAY_DURATION)
        if self._frames and len(self._frames) > 1:
            self._start_frame_sequence()

    def _on_scroll_changed(self, *_args: Any) -> None:
        if not self._dismissed:
            self._sync_to_card()

    # --------------------------------------------------------------
    # 帧序列播放（分阶段变速）
    # --------------------------------------------------------------
    # 帧时间表: frame_02~04 各 0.7s, frame_05(打哈欠) 1.3s,
    #            frame_06(倒数第二) 1.3s, frame_07(最后) 1.3s

    def _start_frame_sequence(self) -> None:
        """启动分阶段变速帧序列: frame_01 已是初始纹理, 从 frame_02 开始推进。"""
        if not self._frames or len(self._frames) <= 1:
            return
        # frame_01(索引0) → frame_02(索引1): 0.3/ANIM_SPEED 后
        self._next_frame_event = Clock.schedule_once(
            lambda dt: self._advance_to(1, 0.7 / ANIM_SPEED), 0.3 / ANIM_SPEED
        )

    def _advance_to(self, frame_idx: int, next_delay: float) -> None:
        """跳转到 frame_idx 帧并设置下一帧的延迟。

        Args:
            frame_idx: 要显示的帧索引
            next_delay: 当前帧展示完毕后到下一帧的延迟(秒)
        """
        if self._dismissed:
            return
        if frame_idx < len(self._frames):
            self._frame_idx = frame_idx
            self._ip_image.texture = self._frames[frame_idx].texture

        next_idx = frame_idx + 1
        if next_idx >= len(self._frames):
            self._next_frame_event = None
            return  # 最后一帧，不再推进

        # 根据下一帧索引决定展示时长 (已按 ANIM_SPEED 缩放)
        if next_idx >= 4:
            delay = 1.3 / ANIM_SPEED
        else:
            delay = 0.7 / ANIM_SPEED

        self._next_frame_event = Clock.schedule_once(
            lambda dt, n=next_idx, d=delay: self._advance_to(n, d), next_delay
        )

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
        if self._next_frame_event:
            self._next_frame_event.cancel()
            self._next_frame_event = None
        if self._bounce_anim:
            self._bounce_anim.cancel(self._title_lbl)
            self._bounce_anim = None
        # 恢复底下卡片按钮可见性
        for w, prev_opacity in self._hidden_widgets:
            try:
                w.opacity = prev_opacity
            except Exception:
                pass
        # 解绑滚动事件
        if self._bound_scrollview is not None:
            try:
                self._bound_scrollview.unbind(
                    scroll_y=self._on_scroll_changed,
                    scroll_x=self._on_scroll_changed,
                )
            except Exception:
                pass
        try:
            self._target_card.unbind(pos=self._on_card_changed, size=self._on_card_changed)
        except Exception:
            pass
        if self.parent is not None:
            self.parent.remove_widget(self)
        if self._on_dismiss_callback:
            try:
                self._on_dismiss_callback()
            except Exception:
                pass
