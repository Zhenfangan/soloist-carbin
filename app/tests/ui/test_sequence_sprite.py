"""SequenceSprite — 帧序列循环动画组件(cat 庆祝 / dog 摘星星复用)。"""

from __future__ import annotations

from app.ui.components.sequence_sprite import SequenceSprite


def test_loads_cat_sequence_frames() -> None:
    sprite = SequenceSprite("cat", autoplay=False)
    assert sprite.frame_count == 7
    assert sprite.texture is not None  # 首帧已上屏


def test_advance_cycles_frames_and_updates_texture() -> None:
    sprite = SequenceSprite("cat", autoplay=False)
    assert sprite.current_index == 0
    first_tex = sprite.texture
    sprite._advance()
    assert sprite.current_index == 1
    assert sprite.texture is not first_tex  # 换帧了
    # 循环回绕
    for _ in range(6):
        sprite._advance()
    assert sprite.current_index == 0


def test_dog_sequence_also_loads() -> None:
    sprite = SequenceSprite("dog", autoplay=False)
    assert sprite.frame_count == 7


def test_unknown_anim_id_degrades_without_crash() -> None:
    sprite = SequenceSprite("nonexistent", autoplay=False)
    assert sprite.frame_count == 0
    sprite._advance()  # 空序列不崩
    sprite.play()
    sprite.stop()


def test_play_stop_toggles_running() -> None:
    sprite = SequenceSprite("cat", autoplay=False)
    assert sprite.is_playing is False
    sprite.play()
    assert sprite.is_playing is True
    sprite.stop()
    assert sprite.is_playing is False


def test_default_rhythm_is_uniform_interval() -> None:
    """不传 bubble_indices/loop_pause 时行为不变(其他动画的向后兼容)。"""
    sprite = SequenceSprite("dog", autoplay=False, fps=4.0)
    for idx in range(sprite.frame_count):
        sprite._index = idx
        assert sprite._next_delay() == 0.25


def test_bubble_indices_hold_twice_as_long() -> None:
    """真机反馈: 小猫动画比战报里的感觉快 —— 战报用 _start_frame_anim 让
    气泡帧(bubble_indices)停留 2 倍时长, SequenceSprite 之前完全没有这个
    节奏, 只会匀速循环, 即使 fps 数字相同, 观感也更"赶"。"""
    sprite = SequenceSprite("cat", autoplay=False, fps=4.0, bubble_indices={1, 3, 4})
    sprite._index = 1
    assert sprite._next_delay() == 0.5
    sprite._index = 2
    assert sprite._next_delay() == 0.25


def test_loop_pause_applies_after_last_frame() -> None:
    """播完最后一帧后暂停 loop_pause 秒才重新开始, 与战报节奏一致。"""
    sprite = SequenceSprite("cat", autoplay=False, fps=4.0, loop_pause=2.0)
    sprite._index = sprite.frame_count - 1
    assert sprite._next_delay() == 2.0
