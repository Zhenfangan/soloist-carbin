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
