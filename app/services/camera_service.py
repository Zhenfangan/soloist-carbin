"""相机服务抽象接口 — 打卡自拍"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path


class CameraService(ABC):
    """调起相机/选图，完成后通过回调返回图片路径。"""

    @abstractmethod
    def take_photo(
        self,
        period: str,
        action: str,
        on_done: Callable[[Path | None], None],
    ) -> None:
        """调起相机拍照，完成后调用 on_done(path)。

        Args:
            period: morning / afternoon
            action: in (签到) / out (签退)
            on_done: 回调，path=None 表示用户取消或失败
        """
        raise NotImplementedError
