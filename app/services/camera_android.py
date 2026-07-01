"""Android 相机服务 — 调 plyer.camera Intent 拍照"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .camera_service import CameraService


class AndroidCameraService(CameraService):
    """Android 实现：调 plyer.camera.take_picture，保存到公共 Pictures/Soloist。"""

    def take_photo(
        self,
        period: str,
        action: str,
        on_done: Callable[[Path | None], None],
    ) -> None:
        from kivy.logger import Logger

        from app.utils.clock import get_clock
        from app.utils.storage import get_pictures_dir, scan_media
        date_str = get_clock().today_str()
        dest = get_pictures_dir() / date_str / f"{period}_{action}.jpg"
        dest.parent.mkdir(parents=True, exist_ok=True)

        # Android 7+ (API 24+) 默认禁止 file:// URI 跨进程传递, 否则抛
        # FileUriExposedException。plyer.camera 正是用 file:// 把目标路径传给
        # 系统相机, 不关掉这个检查, 相机 Intent 会直接崩溃 → 签到毫无反应。
        try:
            from jnius import autoclass  # type: ignore[import]
            strict_mode = autoclass("android.os.StrictMode")
            strict_mode.disableDeathOnFileUriExposure()
        except Exception as e:  # noqa: BLE001
            Logger.warning(f"AndroidCamera: 关闭 FileUriExposure 检查失败 {e!r}")

        try:
            from plyer import camera as plyer_camera  # type: ignore[import]

            Logger.info(f"AndroidCamera: 启动系统相机 dest={dest}")

            def _on_complete(filename: str | None) -> None:
                Logger.info(f"AndroidCamera: 拍照回调 filename={filename}")
                if filename and Path(filename).exists():
                    scan_media(Path(filename))
                    on_done(Path(filename))
                else:
                    on_done(None)

            plyer_camera.take_picture(filename=str(dest), on_complete=_on_complete)
        except Exception as e:  # noqa: BLE001
            Logger.error(f"AndroidCamera: take_picture 失败 {e!r}")
            on_done(None)
