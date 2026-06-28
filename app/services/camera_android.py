"""Android 相机服务 — 调 plyer.camera Intent 拍照"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .camera_service import CameraService


class AndroidCameraService(CameraService):
    """Android 实现：调 plyer.camera.take_picture，保存到 user_data/photos。"""

    _BASE_DIR = Path("user_data/photos")

    def take_photo(
        self,
        period: str,
        action: str,
        on_done: Callable[[Path | None], None],
    ) -> None:
        from app.utils.clock import get_clock
        date_str = get_clock().today_str()
        dest = self._BASE_DIR / date_str / f"{period}_{action}.jpg"
        dest.parent.mkdir(parents=True, exist_ok=True)

        try:
            from plyer import camera as plyer_camera  # type: ignore[import]

            def _on_complete(filename: str | None) -> None:
                if filename and Path(filename).exists():
                    on_done(Path(filename))
                else:
                    on_done(None)

            plyer_camera.take_picture(filename=str(dest), on_complete=_on_complete)
        except Exception:
            on_done(None)
