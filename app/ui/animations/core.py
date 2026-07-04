"""像素动画引擎 — FrameAnimator / SpritePlayer / 过渡动画。

逐帧切换为主，辅以简单位移/缩放。帧率固定 4 FPS (250ms/帧)。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.uix.image import Image as KivyImage
from kivy.uix.widget import Widget

from app.ui.assets.loader import SpriteLoader, apply_sprite_texture
from app.ui.tokens import GRID_UNIT


class FrameAnimator:
    """逐帧动画播放器。

    接收 sprite sheet 切片列表，按固定帧率循环或单次播放。
    """

    def __init__(
        self,
        frames: list[Any],
        fps: int = 4,
        loop: bool = True,
        reverse: bool = False,
        on_complete: Callable[[], None] | None = None,
    ) -> None:
        self._frames = frames
        self._fps = fps
        self._interval = 1.0 / fps
        self._loop = loop
        self._reverse = reverse
        self._on_complete = on_complete
        self._current_index = 0
        self._playing = False
        self._event: Any = None
        self._direction = -1 if reverse else 1

        if reverse and len(frames) > 1:
            self._current_index = len(frames) - 1

    @property
    def current_frame_index(self) -> int:
        return self._current_index

    @property
    def current_frame(self) -> Any:
        return self._frames[self._current_index]

    @property
    def frame_count(self) -> int:
        return len(self._frames)

    @property
    def is_playing(self) -> bool:
        return self._playing

    def play(self) -> None:
        """开始播放。"""
        if self._playing or not self._frames:
            return
        self._playing = True
        self._event = Clock.schedule_interval(self._tick, self._interval)

    def stop(self) -> None:
        """停止播放。"""
        self._playing = False
        if self._event:
            Clock.unschedule(self._event)
            self._event = None

    def reset(self) -> None:
        """重置到起始帧。"""
        self.stop()
        self._current_index = len(self._frames) - 1 if self._reverse else 0

    def _tick(self, dt: float) -> None:
        """每帧回调。"""
        next_idx = self._current_index + self._direction
        if 0 <= next_idx < len(self._frames):
            self._current_index = next_idx
        elif self._loop:
            self._current_index = 0 if self._direction > 0 else len(self._frames) - 1
        else:
            self.stop()
            if self._on_complete:
                self._on_complete()
                return


class SpritePlayer(Widget):  # type: ignore[misc]
    """将 FrameAnimator 绑定到 Kivy Image widget，封装为可复用的 Widget。

    自动更新 Image 的 texture。
    """

    def __init__(
        self,
        mascot_id: str = "dudu",
        fps: int = 4,
        loop: bool = True,
        reverse: bool = False,
        size: tuple[int, int] = (64, 64),
        on_complete: Callable[[], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = size

        frames = SpriteLoader.load_sprite(mascot_id)
        self._animator = FrameAnimator(frames, fps=fps, loop=loop, reverse=reverse, on_complete=on_complete)

        self._image = KivyImage(size=size, size_hint=(None, None))
        self._image.allow_stretch = True
        self._image.keep_ratio = False
        self.add_widget(self._image)

        # 绑定每帧更新
        Clock.schedule_interval(self._update_texture, self._animator._interval)

    @property
    def animator(self) -> FrameAnimator:
        return self._animator

    def play(self) -> None:
        self._animator.play()

    def stop(self) -> None:
        self._animator.stop()

    def _update_texture(self, dt: float) -> None:
        if not self._animator.is_playing:
            return
        frame = self._animator.current_frame
        apply_sprite_texture(self._image, frame)  # 挂帧纹理 + nearest 过滤(防放大糊)


def pixel_expand(widget: Widget, height_delta: int, duration: float = 0.2) -> None:
    """像素阶梯式高度变化动画，每 GRID_UNIT px 一步。

    Args:
        widget: 目标 widget
        height_delta: 高度变化量 (正=展开, 负=收起)
        duration: 总时长 (秒)
    """
    start_h = widget.height
    steps = max(1, abs(height_delta) // GRID_UNIT)
    step_duration = duration / steps
    step_px = height_delta / steps

    def _step(i: int, dt: float) -> None:
        widget.height = start_h + step_px * (i + 1)

    for i in range(steps):
        Clock.schedule_once(lambda dt, s=i: _step(s, dt), i * step_duration)


def pixel_fade_in(widget: Widget, duration: float = 0.2) -> None:
    """像素风格淡化出现。"""
    anim = Animation(opacity=1.0, duration=duration, t="in_out_cubic")
    widget.opacity = 0.0
    anim.start(widget)


def pixel_fade_out(widget: Widget, duration: float = 0.2) -> None:
    """像素风格淡化消失。"""
    anim = Animation(opacity=0.0, duration=duration, t="in_out_cubic")
    anim.start(widget)


def pixel_slide_in(widget: Widget, direction: str = "left", duration: float = 0.25) -> None:
    """像素风格滑入动画。

    Args:
        widget: 目标 widget
        direction: 'left' | 'right' | 'up' | 'down'
        duration: 总时长
    """
    orig_pos = list(widget.pos)
    w, h = widget.size

    offsets = {"left": (w, 0), "right": (-w, 0), "up": (0, -h), "down": (0, h)}
    dx, dy = offsets.get(direction, (w, 0))

    # 设置起始偏移位置
    widget.pos = (orig_pos[0] + dx, orig_pos[1] + dy)

    anim = Animation(x=orig_pos[0], y=orig_pos[1], duration=duration, t="out_quad")
    anim.start(widget)
