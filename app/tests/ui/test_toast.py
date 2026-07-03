"""公共 toast 组件冒烟测试。"""

from __future__ import annotations

from kivy.uix.label import Label
from kivy.uix.modalview import ModalView

from app.ui.components.toast import show_reward_celebration, show_toast


def _all_label_texts(widget: object) -> list[str]:
    texts: list[str] = []
    if isinstance(widget, Label):
        texts.append(widget.text)
    for child in getattr(widget, "children", []):
        texts.extend(_all_label_texts(child))
    return texts


def _find_widgets(widget: object, cls: type) -> list:
    out = []
    if isinstance(widget, cls):
        out.append(widget)
    for child in getattr(widget, "children", []):
        out.extend(_find_widgets(child, cls))
    return out


def test_show_toast_returns_modalview_with_message() -> None:
    toast = show_toast("测试提示", duration=0.1)
    try:
        assert isinstance(toast, ModalView)
        assert "测试提示" in " ".join(_all_label_texts(toast))
    finally:
        toast.dismiss()


def test_background_rect_tracks_label_no_offset() -> None:
    """黑条必须紧贴文字标签(修复旧 scale_wrap 坐标错配导致的偏移)。"""
    from kivy.clock import Clock

    toast = show_toast("拍摄复盘已记录，奖励已入账", duration=0.1)
    try:
        for _ in range(3):
            Clock.tick()
        rect = toast._bg_rect
        lbl = toast._label
        assert abs(rect.pos[0] - lbl.pos[0]) < 1.0
        assert abs(rect.pos[1] - lbl.pos[1]) < 1.0
        assert abs(rect.size[0] - lbl.size[0]) < 1.0
        assert abs(rect.size[1] - lbl.size[1]) < 1.0
        assert lbl.size[0] > 0 and lbl.size[1] > 0  # 背景不是 0 宽
    finally:
        toast.dismiss()


def test_reward_celebration_shows_dog_animation_and_message() -> None:
    """done 态庆祝浮层:小狗摘星星动画 + 奖励文案(文案保留)。"""
    from kivy.clock import Clock

    from app.ui.components.sequence_sprite import SequenceSprite

    modal = show_reward_celebration("拍摄复盘已记录，奖励已入账", duration=0.1)
    try:
        for _ in range(3):
            Clock.tick()
        assert isinstance(modal, ModalView)
        assert "奖励已入账" in "".join(_all_label_texts(modal))
        sprites = _find_widgets(modal, SequenceSprite)
        assert len(sprites) == 1
        assert sprites[0].frame_count == 7  # dog 序列
        assert sprites[0].is_playing is True  # 自动播放
    finally:
        modal.dismiss()
