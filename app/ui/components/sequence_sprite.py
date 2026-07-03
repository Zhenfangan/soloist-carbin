"""SequenceSprite — 帧序列循环动画。

复用 assets/animations/<id>/ 的逐帧 PNG(cat 小猫庆祝 / dog 小狗摘星星),
以固定帧率循环播放。加载失败时优雅降级为空(不崩,texture 保持默认)。
"""

from __future__ import annotations

from typing import Any

from kivy.clock import Clock
from kivy.uix.image import Image

from app.ui.assets.loader import SequenceLoader


class SequenceSprite(Image):  # type: ignore[misc]
    """按固定帧率循环播放帧序列的 Image。"""

    def __init__(
        self,
        anim_id: str,
        fps: float = 6.0,
        autoplay: bool = True,
        **kwargs: Any,
    ) -> None:
        kwargs.setdefault("allow_stretch", True)
        kwargs.setdefault("keep_ratio", True)
        super().__init__(**kwargs)

        self._interval = 1.0 / fps if fps > 0 else 0.25
        self._index = 0
        self._event: Any = None
        try:
            self._frames = SequenceLoader.load_sequence(anim_id)
        except Exception:
            self._frames = []

        if self._frames:
            self.texture = self._frames[0].texture

        if autoplay:
            self.play()

    # ── 属性 ──────────────────────────────────────────────
    @property
    def frame_count(self) -> int:
        return len(self._frames)

    @property
    def current_index(self) -> int:
        return self._index

    @property
    def is_playing(self) -> bool:
        return self._event is not None

    # ── 控制 ──────────────────────────────────────────────
    def play(self) -> None:
        if self._event is not None or not self._frames:
            return
        self._event = Clock.schedule_interval(lambda _dt: self._advance(), self._interval)

    def stop(self) -> None:
        if self._event is not None:
            self._event.cancel()
            self._event = None

    def _advance(self) -> None:
        if not self._frames:
            return
        self._index = (self._index + 1) % len(self._frames)
        self.texture = self._frames[self._index].texture
