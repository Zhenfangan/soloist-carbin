"""打卡成功动画序列。

4 阶段动画:
① 按钮缩小 + 变为勾号 (150ms)
② 兜兜从右下角弹入 (300ms spring)
③ 兜兜左右摇摆 2 次 (1000ms)
④ 兜兜缩回右下角 (200ms ease-out)

总时长 ~2 秒。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from kivy.clock import Clock
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label

from app.ui.assets.loader import SpriteLoader
from app.ui.tokens import GRID_UNIT, SPRITE_SIZE


def _do_nothing(*args: Any) -> None:
    pass


def checkin_success_sequence(
    container: FloatLayout,
    animating_widget: Any,  # 被动画的按钮/勾号 widget
    on_mascot_show: Callable[[], Any] | None = None,
    on_mascot_hide: Callable[[], Any] | None = None,
    on_complete: Callable[[], Any] | None = None,
) -> None:
    """执行打卡成功动画序列。

    Args:
        container: 动画容器 (FloatLayout)
        animating_widget: 要缩放的按钮
        on_mascot_show: 兜兜弹出时的回调（可用于下一步展开）
        on_mascot_hide: 兜兜缩回时的回调
        on_complete: 全部完成后的回调
    """
    if on_mascot_show is None:
        on_mascot_show = _do_nothing
    if on_mascot_hide is None:
        on_mascot_hide = _do_nothing
    if on_complete is None:
        on_complete = _do_nothing

    # 创建勾号标签
    check_label = Label(
        text="OK",
        font_size=24,
        size_hint=(None, None),
        size=(40, 40),
        opacity=0,
    )
    container.add_widget(check_label)

    # 创建兜兜 image
    try:
        dudu_frames = SpriteLoader.load_sprite("dudu")
        mascot_img = Image(
            size_hint=(None, None),
            size=(SPRITE_SIZE, SPRITE_SIZE),
            opacity=0,
        )
        if dudu_frames:
            # 使用第二帧（✌️ 帧）
            mascot_img.texture = dudu_frames[2].texture
            mascot_img.canvas.ask_update()
    except Exception:
        # 回退: 用文字
        mascot_img = Label(
            text="dudu",
            font_size=32,
            size_hint=(None, None),
            size=(SPRITE_SIZE, SPRITE_SIZE),
            opacity=0,
        )

    container.add_widget(mascot_img)

    # 阶段时间线
    # 阶段 1: 按钮缩小 + 勾号 (150ms)
    def phase1(dt: float) -> None:
        # 隐藏原按钮
        if hasattr(animating_widget, 'opacity'):
            animating_widget.opacity = 0
        # 显示勾号
        if hasattr(animating_widget, 'pos'):
            check_label.pos = (
                animating_widget.pos[0] + animating_widget.size[0] / 2 - 20,
                animating_widget.pos[1] + animating_widget.size[1] / 2 - 20,
            )
        check_label.opacity = 1

        # 阶段 2: 兜兜弹入 (300ms)
        Clock.schedule_once(phase2, 0.15)

    # 阶段 2: 兜兜从右下角弹入
    def phase2(dt: float) -> None:
        # 将兜兜放置在容器右下位置
        mascot_img.pos = (container.width - SPRITE_SIZE - GRID_UNIT, GRID_UNIT)
        mascot_img.opacity = 1
        on_mascot_show()

        # 阶段 3: 摇摆 2 次 (1000ms)
        Clock.schedule_once(phase3_swing_1, 0.15)

    def phase3_swing_1(dt: float) -> None:
        # 轻微移动实现摇摆
        current_x = mascot_img.pos[0]
        mascot_img.pos = (current_x - 4, mascot_img.pos[1])
        Clock.schedule_once(phase3_swing_2, 0.2)

    def phase3_swing_2(dt: float) -> None:
        current_x = mascot_img.pos[0]
        mascot_img.pos = (current_x + 8, mascot_img.pos[1])
        Clock.schedule_once(phase3_swing_3, 0.2)

    def phase3_swing_3(dt: float) -> None:
        current_x = mascot_img.pos[0]
        mascot_img.pos = (current_x - 8, mascot_img.pos[1])
        Clock.schedule_once(phase3_swing_4, 0.2)

    def phase3_swing_4(dt: float) -> None:
        current_x = mascot_img.pos[0]
        mascot_img.pos = (current_x + 4, mascot_img.pos[1])

        # 阶段 4: 兜兜缩回 (200ms)
        Clock.schedule_once(phase4, 0.3)

    # 阶段 4: 兜兜缩回
    def phase4(dt: float) -> None:
        mascot_img.opacity = 0
        check_label.opacity = 1
        on_mascot_hide()

        # 清理
        Clock.schedule_once(phase_cleanup, 0.2)

    def phase_cleanup(dt: float) -> None:
        try:
            if check_label in container.children:
                container.remove_widget(check_label)
            if mascot_img in container.children:
                container.remove_widget(mascot_img)
        except Exception:
            pass
        on_complete()

    # 启动动画
    Clock.schedule_once(phase1, 0.05)
