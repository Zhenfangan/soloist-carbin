"""Android 相机服务 — 调 plyer.camera Intent 拍照"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from kivy.clock import Clock
from kivy.logger import Logger

from app.utils.storage import get_private_photos_dir, scan_media

from .camera_service import CameraService


def _dispatch_to_main_thread(callback: Callable[[], None]) -> None:
    """把回调调度到 Kivy 主线程执行。

    真机根因(2026-07-08 logcat 坐实): 系统相机经 plyer 的 onActivityResult 在
    【非 Kivy 主线程】回调, 若在该线程里直接操作 graphics(创建/移除 widget、
    改 canvas、传纹理)会抛:
        TypeError: Cannot change graphics instruction outside the main Kivy thread
    进而打断整条签到收尾逻辑 —— 刷新卡片、庆祝动画、男友承诺框全部丢失, 且卡片
    图标纹理传不上 GL 显示成黑块, 必须切 Tab 才恢复(切 Tab 的 on_enter 由主循环
    在主线程触发)。

    Clock.schedule_once 的回调保证在主线程下一帧执行, 是 Kivy 官方推荐的跨线程
    UI 更新方式。
    """
    Clock.schedule_once(lambda _dt: callback(), 0)


def _rescue_to_private(src: Path, private_dir_provider: Callable[[], Path]) -> Path:
    """把系统相机刚写入公共相册的照片, 抢救性复制到 app 私有目录并返回私有路径。

    真机坐实(2026-07-08 OPPO): 公共相册的照片在 scoped storage 下不持久, 回调后
    几分钟就被系统当孤儿文件清理(DB 里 photo_path 有值但文件已消失)。但回调这一刻
    文件还在(Path.exists() 为真), 立即复制到 app 完全掌控的私有外部目录, 战报即可
    稳定读取。复制失败则退回原公共路径(至少当次能显示), 绝不丢回调。
    """
    try:
        import shutil

        from app.utils.clock import get_clock
        date = get_clock().today_str()
        dest_dir = private_dir_provider() / date
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / src.name
        shutil.copy2(src, dest)
        return dest
    except Exception as e:  # noqa: BLE001
        Logger.error(f"AndroidCamera: 抢救照片到私有目录失败 {e!r}")
        return src


def _make_result_handler(
    on_done: Callable[[Path | None], None],
    private_dir_provider: Callable[[], Path] | None = None,
) -> Callable[[str | None], None]:
    """构造 plyer take_picture 的 on_complete 回调。

    on_complete 在非主线程被调用(见 _dispatch_to_main_thread)。文件存在性检查、
    抢救复制(纯 IO, 不碰 graphics)留在回调线程即可; 唯独最终的 on_done(会触发大量
    graphics 操作)必须切回主线程。private_dir_provider 可注入以便单测。
    """
    provider = private_dir_provider or get_private_photos_dir

    def _on_complete(filename: str | None) -> None:
        Logger.info(f"AndroidCamera: 拍照回调 filename={filename}")
        if filename and Path(filename).exists():
            src = Path(filename)
            final = _rescue_to_private(src, provider)
            _dispatch_to_main_thread(lambda: on_done(final))
        else:
            _dispatch_to_main_thread(lambda: on_done(None))

    return _on_complete


class AndroidCameraService(CameraService):
    """Android 实现：调 plyer.camera.take_picture，保存到公共 Pictures/Soloist。"""

    def take_photo(
        self,
        period: str,
        action: str,
        on_done: Callable[[Path | None], None],
    ) -> None:
        from app.utils.clock import get_clock
        from app.utils.storage import get_pictures_dir
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
            plyer_camera.take_picture(
                filename=str(dest),
                on_complete=_make_result_handler(on_done),
            )
        except Exception as e:  # noqa: BLE001
            Logger.error(f"AndroidCamera: take_picture 失败 {e!r}")
            _dispatch_to_main_thread(lambda: on_done(None))
