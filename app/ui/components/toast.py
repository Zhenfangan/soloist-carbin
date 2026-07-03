"""公共 Toast — 临时浮层提示。

从 settings_screen.show_toast 抽取为公共组件，供全项目复用。
黑色胶囊背景直接绑定文字标签自身的 pos/size(而非旧版 scale_wrap+canvas.before
的双坐标系，会导致黑条与文字分离偏移)，标签用 pos_hint 在全屏 FloatLayout 内居中，
字号按屏幕比例放大以适配真机大屏。
"""

from __future__ import annotations

from typing import Any

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView

from app.ui.tokens import COLORS, FONT_SIZE_BODY, LOGICAL_HEIGHT, LOGICAL_WIDTH


def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, alpha)


def _screen_scale() -> float:
    """与主界面/弹窗一致的屏幕等比系数，最小 1(不缩小)。"""
    if not Window.width or not Window.height:
        return 1.0
    return max(1.0, min(Window.width / LOGICAL_WIDTH, Window.height / LOGICAL_HEIGHT))


def show_toast(message: str, duration: float = 2.0) -> ModalView:
    """显示临时 Toast 通知，duration 秒后自动消失。返回 ModalView 实例。"""
    scale = _screen_scale()
    pad_x, pad_y = 24.0 * scale, 14.0 * scale

    toast = ModalView(
        size_hint=(1, 1),
        background="",
        background_color=(0, 0, 0, 0),
        auto_dismiss=True,
    )
    root = FloatLayout()

    label = Label(
        text=message,
        font_size=FONT_SIZE_BODY * scale,
        color=_to_rgba(COLORS["BG_CREAM"]),
        halign="center",
        valign="middle",
        size_hint=(None, None),
        pos_hint={"center_x": 0.5, "center_y": 0.5},
    )

    with label.canvas.before:
        Color(0, 0, 0, 0.85)
        bg_rect = Rectangle(pos=label.pos, size=label.size)

    def _sync_bg(*_a: Any) -> None:
        bg_rect.pos = label.pos
        bg_rect.size = label.size

    def _fit_to_text(*_a: Any) -> None:
        label.width = label.texture_size[0] + pad_x * 2
        label.height = label.texture_size[1] + pad_y * 2

    label.bind(pos=_sync_bg, size=_sync_bg, texture_size=_fit_to_text)
    label.texture_update()
    _fit_to_text()
    _sync_bg()

    root.add_widget(label)
    toast.add_widget(root)
    toast.open()
    Clock.schedule_once(lambda _dt: toast.dismiss(), duration)

    # 暴露给测试/调用方校验对齐
    toast._label = label
    toast._bg_rect = bg_rect
    return toast


def show_reward_celebration(
    message: str,
    duration: float = 2.5,
    anim_id: str = "dog",
) -> ModalView:
    """奖励庆祝浮层 — 小狗摘星星动画 + 文案(拍摄复盘提交后用)。

    动画在上、文案在下，整体居中于深色圆角卡片上，duration 秒后消失。
    """
    from app.ui.components.sequence_sprite import SequenceSprite

    scale = _screen_scale()
    anim_size = int(112 * scale)   # 比 toast 大，动画更醒目
    pad_x, pad_y = 24.0 * scale, 20.0 * scale
    label_h = 40.0 * scale
    spacing = 6.0 * scale

    modal = ModalView(
        size_hint=(1, 1),
        background="",
        background_color=(0, 0, 0, 0),
        auto_dismiss=True,
    )
    root = FloatLayout()

    card = BoxLayout(
        orientation="vertical",
        size_hint=(None, None),
        width=max(anim_size + pad_x * 2, 260 * scale),
        height=anim_size + label_h + spacing + pad_y * 2,
        padding=[pad_x, pad_y],
        spacing=spacing,
        pos_hint={"center_x": 0.5, "center_y": 0.5},
    )
    with card.canvas.before:
        Color(0, 0, 0, 0.82)
        card_bg = RoundedRectangle(pos=card.pos, size=card.size, radius=[16 * scale])
    card.bind(
        pos=lambda *_a: setattr(card_bg, "pos", card.pos),
        size=lambda *_a: setattr(card_bg, "size", card.size),
    )

    anim_wrap = AnchorLayout(size_hint=(1, None), height=anim_size, anchor_x="center", anchor_y="center")
    sprite = SequenceSprite(
        anim_id,
        size_hint=(None, None),
        size=(anim_size, anim_size),
    )
    anim_wrap.add_widget(sprite)
    card.add_widget(anim_wrap)

    label = Label(
        text=message,
        font_size=FONT_SIZE_BODY * scale,
        color=_to_rgba(COLORS["BG_CREAM"]),
        halign="center",
        valign="middle",
        size_hint=(1, None),
        height=label_h,
    )
    label.bind(size=lambda *_a: setattr(label, "text_size", label.size))
    card.add_widget(label)

    root.add_widget(card)
    modal.add_widget(root)
    modal.bind(on_dismiss=lambda *_a: sprite.stop())
    modal.open()
    Clock.schedule_once(lambda _dt: modal.dismiss(), duration)

    modal._sprite = sprite
    modal._label = label
    return modal
