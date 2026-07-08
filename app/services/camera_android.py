"""Android 相机服务 — 调 plyer.camera Intent 拍照"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from kivy.clock import Clock
from kivy.logger import Logger

from app.utils.storage import scan_media

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


def _make_result_handler(
    on_done: Callable[[Path | None], None],
) -> Callable[[str | None], None]:
    """构造 plyer take_picture 的 on_complete 回调。

    on_complete 在非主线程被调用(见 _dispatch_to_main_thread)。文件存在性检查、
    媒体库扫描(仅发 Android 广播, 不碰 graphics)留在回调线程即可; 唯独最终的
    on_done(会触发大量 graphics 操作)必须切回主线程。
    """

    def _on_complete(filename: str | None) -> None:
        Logger.info(f"AndroidCamera: 拍照回调 filename={filename}")
        if filename and Path(filename).exists():
            path = Path(filename)
            scan_media(path)
            _dispatch_to_main_thread(lambda: on_done(path))
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
