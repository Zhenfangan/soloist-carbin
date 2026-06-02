"""测试动画系统 — FrameAnimator / SpritePlayer / 过渡动画。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.ui.animations.core import (
    FrameAnimator,
    SpritePlayer,
    pixel_expand,
    pixel_fade_in,
    pixel_fade_out,
    pixel_slide_in,
)
from app.ui.assets.loader import SpriteLoader


class TestFrameAnimator:
    """7.1 FrameAnimator 测试"""

    def test_create_animator(self) -> None:
        frames = ["f0", "f1", "f2", "f3"]
        anim = FrameAnimator(frames)
        assert anim.frame_count == 4
        assert anim.current_frame_index == 0
        assert not anim.is_playing

    def test_forward_playback(self) -> None:
        frames = ["f0", "f1", "f2", "f3"]
        anim = FrameAnimator(frames)
        anim._tick(0)
        assert anim.current_frame_index == 1
        anim._tick(0)
        assert anim.current_frame_index == 2

    def test_loop_playback(self) -> None:
        frames = ["f0", "f1", "f2"]
        anim = FrameAnimator(frames, loop=True)
        anim._current_index = 2
        anim._tick(0)
        assert anim.current_frame_index == 0  # loop back

    def test_reverse_playback(self) -> None:
        frames = ["f0", "f1", "f2", "f3"]
        anim = FrameAnimator(frames, reverse=True)
        assert anim.current_frame_index == 3
        anim._tick(0)
        assert anim.current_frame_index == 2

    def test_on_complete_callback(self) -> None:
        completed: list[bool] = []

        def cb() -> None:
            completed.append(True)

        frames = ["f0", "f1"]
        anim = FrameAnimator(frames, loop=False, on_complete=cb)
        anim._tick(0)  # 0→1
        assert anim.current_frame_index == 1
        anim._tick(0)  # 1→end, fire callback
        assert not anim.is_playing
        assert completed == [True]

    def test_play_stop(self) -> None:
        frames = ["f0", "f1"]
        anim = FrameAnimator(frames)
        anim.play()
        assert anim.is_playing
        anim.stop()
        assert not anim.is_playing

    def test_reset(self) -> None:
        frames = ["f0", "f1", "f2", "f3"]
        anim = FrameAnimator(frames, reverse=True)
        anim._tick(0)
        anim.reset()
        assert anim.current_frame_index == 3


class TestPixelTransitions:
    """7.3~7.5 过渡动画测试"""

    def test_pixel_expand_changes_height(self) -> None:
        from kivy.clock import Clock
        from kivy.uix.widget import Widget

        w = Widget()
        w.height = 48
        pixel_expand(w, 16, duration=0.1)

        # 推进时钟让 schedule_once 回调执行
        for _ in range(10):
            Clock.tick()
        # 展开后高度应增加
        assert w.height > 48, f"expected height > 48, got {w.height}"

    def test_pixel_fade_in_sets_opacity(self) -> None:
        from kivy.clock import Clock
        from kivy.uix.widget import Widget

        w = Widget()
        w.opacity = 0.0
        pixel_fade_in(w, duration=0.05)

        # 推进时钟让动画完成 (duration=0.05s)
        for _ in range(10):
            Clock.tick()
        assert w.opacity > 0.0, f"expected opacity > 0, got {w.opacity}"

    def test_pixel_fade_out_sets_opacity(self) -> None:
        from kivy.clock import Clock
        from kivy.uix.widget import Widget

        w = Widget()
        w.opacity = 1.0
        pixel_fade_out(w, duration=0.05)

        for _ in range(10):
            Clock.tick()
        assert w.opacity < 1.0, f"expected opacity < 1, got {w.opacity}"

    def test_pixel_slide_in_sets_position(self) -> None:
        from kivy.clock import Clock
        from kivy.uix.widget import Widget

        w = Widget()
        w.size = (100, 50)
        w.pos = (200, 100)

        # pixel_slide_in 从右侧滑入: start_pos = (200 + 100, 100) = (300, 100)
        pixel_slide_in(w, direction="left", duration=0.05)
        # 立即验证起始位置被偏移
        assert w.x == 300, f"expected x=300 (shifted right), got {w.x}"

        for _ in range(10):
            Clock.tick()
        # 动画完成后应回到原位置
        assert w.x < 300, f"expected x < 300 after slide, got {w.x}"


class TestSpritePlayer:
    """7.2 SpritePlayer 测试"""

    def test_create_sprite_player(self) -> None:
        # 需要 mock SpriteLoader 因为 CoreImage 需要 OpenGL
        with patch.object(SpriteLoader, "load_sprite", return_value=[MagicMock(), MagicMock(), MagicMock(), MagicMock()]):
            player = SpritePlayer(mascot_id="dudu")
            assert player.animator.frame_count == 4
            assert not player.animator.is_playing
            player.play()
            assert player.animator.is_playing
            player.stop()  # type: ignore[unreachable]
            assert not player.animator.is_playing
