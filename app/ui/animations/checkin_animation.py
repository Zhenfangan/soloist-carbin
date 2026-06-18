"""打卡成功动画序列。

4 阶段动画:
① 按钮隐藏 (150ms)
② 吉祥物在卡片内展开 (300ms)
③ 吉祥物左右摇摆 2 次 (1600ms)
④ 吉祥物缩回，卡片恢复 (400ms)

总时长 ~2.5 秒。吉祥物显示在触发签到/签退的 PeriodCard 内部，
卡片临时扩展高度容纳动画，完成后恢复正常。

日常打卡/签退使用小兔胜利动画，加班时段使用小熊熬夜动画。
统一尺寸 = PeriodCard._MASCOT_SIZE = 96px（小猪基准 ×1.5）。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from kivy.clock import Clock
from kivy.uix.image import Image
from kivy.uix.label import Label

from app.ui.assets.loader import SequenceLoader
from app.ui.tokens import SPRITE_SIZE

MASCOT_DISPLAY_SIZE = int(SPRITE_SIZE * 1.5)  # 96px — 小猪1.5×基准，全动画统一


def _do_nothing(*args: Any) -> None:
    pass


def checkin_success_sequence(
    container: Any,  # PeriodCard（需有 show_mascot_widget / hide_mascot_widget）
    animating_widget: Any,
    on_mascot_show: Callable[[], Any] | None = None,
    on_mascot_hide: Callable[[], Any] | None = None,
    on_complete: Callable[[], Any] | None = None,
    is_night: bool = False,
) -> None:
    """执行打卡成功动画序列（卡片内版）。

    Args:
        container: PeriodCard 实例，动画在其内部展示。
        animating_widget: 触发动画的按钮（短暂隐藏后恢复）。
        is_night: True 时使用小熊熬夜，否则用小兔胜利。
    """
    if on_mascot_show is None:
        on_mascot_show = _do_nothing
    if on_mascot_hide is None:
        on_mascot_hide = _do_nothing
    if on_complete is None:
        on_complete = _do_nothing

    # 吉祥物图片
    anim_id = "bear" if is_night else "rabbit"
    try:
        seq_frames = SequenceLoader.load_sequence(anim_id)
        mascot_img: Any = Image(
            size_hint=(None, None),
            size=(MASCOT_DISPLAY_SIZE, MASCOT_DISPLAY_SIZE),
            pos_hint={"center_x": 0.5},
            allow_stretch=True,
            keep_ratio=True,
        )
        if seq_frames:
            mascot_img.texture = seq_frames[0].texture
        else:
            raise ValueError("no frames")
        _frame_idx = [0]
        _frame_count = len(seq_frames)
    except Exception:
        seq_frames = []
        _frame_idx = [0]
        _frame_count = 0
        mascot_img = Label(
            text="(^‿^)",
            font_size=48,
            size_hint=(None, None),
            size=(MASCOT_DISPLAY_SIZE, MASCOT_DISPLAY_SIZE),
        )

    def _advance_frame() -> None:
        if seq_frames and _frame_count > 1:
            _frame_idx[0] = (_frame_idx[0] + 1) % _frame_count
            mascot_img.texture = seq_frames[_frame_idx[0]].texture

    # 阶段 1: 短暂隐藏按钮
    def phase1(dt: float) -> None:
        if hasattr(animating_widget, "opacity"):
            animating_widget.opacity = 0
        Clock.schedule_once(phase2, 0.3)

    # 阶段 2: 吉祥物在卡片内展开
    def phase2(dt: float) -> None:
        if hasattr(container, "show_mascot_widget"):
            container.show_mascot_widget(mascot_img)
        on_mascot_show()
        Clock.schedule_once(phase3_swing_1, 0.3)

    def phase3_swing_1(dt: float) -> None:
        _advance_frame()
        Clock.schedule_once(phase3_swing_2, 0.4)

    def phase3_swing_2(dt: float) -> None:
        _advance_frame()
        Clock.schedule_once(phase3_swing_3, 0.4)

    def phase3_swing_3(dt: float) -> None:
        _advance_frame()
        Clock.schedule_once(phase3_swing_4, 0.4)

    def phase3_swing_4(dt: float) -> None:
        _advance_frame()
        Clock.schedule_once(phase4, 0.6)

    # 阶段 4: 吉祥物消失，还原按钮
    def phase4(dt: float) -> None:
        on_mascot_hide()
        Clock.schedule_once(phase_cleanup, 0.4)

    def phase_cleanup(dt: float) -> None:
        if hasattr(container, "hide_mascot_widget"):
            container.hide_mascot_widget()
        if hasattr(animating_widget, "opacity"):
            animating_widget.opacity = 1
        on_complete()

    Clock.schedule_once(phase1, 0.05)
