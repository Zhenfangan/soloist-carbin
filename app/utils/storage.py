"""跨平台图片保存路径 — 桌面存 ~/Desktop, 安卓存公共 Pictures/Soloist。

战报导出与相机照片统一通过 get_pictures_dir() 取根目录;
安卓端落盘后调 scan_media() 通知系统媒体库, 让相册可见。
"""

from __future__ import annotations

from pathlib import Path


def _platform() -> str:
    try:
        from kivy.utils import platform  # type: ignore[import]
        return str(platform)
    except Exception:
        return "unknown"


def get_pictures_dir() -> Path:
    """返回图片保存根目录(自动创建)。安卓→公共 Pictures/Soloist, 桌面→Desktop。"""
    if _platform() == "android":
        path = _android_pictures_dir()
    else:
        path = Path.home() / "Desktop"
    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return path


def _android_pictures_dir() -> Path:
    """安卓公共相册目录 Pictures/Soloist。失败回退 /sdcard。"""
    try:
        from jnius import autoclass  # type: ignore[import]
        Environment = autoclass("android.os.Environment")
        pics = Environment.getExternalStoragePublicDirectory(
            Environment.DIRECTORY_PICTURES
        ).getAbsolutePath()
        return Path(pics) / "Soloist"
    except Exception:
        return Path("/sdcard/Pictures/Soloist")


def get_private_photos_dir() -> Path:
    """app 私有外部目录下的照片根目录(自动创建)。

    打卡照片存这里而非公共相册: 真机坐实(2026-07-08 OPPO), 系统相机写入公共
    Pictures 的照片在 scoped storage 下不持久 —— 尤其卸载重装后 app 换了 uid,
    旧相册目录不再归属它, 照片会被系统当孤儿文件清理(DB 里 photo_path 有值但
    文件已消失)。app 私有外部目录(getExternalFilesDir)由 app 完全掌控、读写零
    权限、不受 uid 变化影响, 是打卡凭证最稳的落脚点。桌面→Desktop/soloist_photos。
    """
    if _platform() == "android":
        try:
            from jnius import autoclass  # type: ignore[import]
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            ctx = PythonActivity.mActivity
            base = ctx.getExternalFilesDir("Pictures").getAbsolutePath()
            path = Path(base) / "Soloist"
        except Exception:
            path = Path(
                "/sdcard/Android/data/org.soloist.soloistcarbin/files/Pictures/Soloist"
            )
    else:
        path = Path.home() / "Desktop" / "soloist_photos"
    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return path


def scan_media(path: Path) -> None:
    """通知安卓媒体库扫描新文件, 让相册立即可见(桌面端空操作)。"""
    if _platform() != "android":
        return
    try:
        from jnius import autoclass  # type: ignore[import]
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        Intent = autoclass("android.content.Intent")
        Uri = autoclass("android.net.Uri")
        File = autoclass("java.io.File")
        activity = PythonActivity.mActivity
        intent = Intent(Intent.ACTION_MEDIA_SCANNER_SCAN_FILE)
        intent.setData(Uri.fromFile(File(str(path))))
        activity.sendBroadcast(intent)
    except Exception:
        pass
