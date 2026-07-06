"""全局字体加载器 — 注册秋叶圆体 为全局默认字体，默认粗体。"""

from __future__ import annotations

from pathlib import Path

from kivy.core.text import LabelBase
from kivy.uix.label import Label as KivyLabel

_FONT_DIR = (Path(__file__).parent / "assets" / "fonts").resolve()
_FONT_PATH = _FONT_DIR / "QiuYeYuanTi-16.ttf"

# emoji 不再走字体渲染 —— 改用项目自有像素图标 (app/ui/components/icon_label.py
# 的 IconLabel + assets/icons/*.png)。历史上两条字体路线都已废弃:
#   1. Windows Segoe UI Emoji: 仅桌面有此字体, 真机 6 个打包字体零覆盖, 仍是方块;
#   2. /system/fonts/NotoColorEmoji.ttf: 真机启动即崩溃循环 (logcat: Fatal
#      signal 11 SIGSEGV, tid=Jit thread pool) —— Kivy 的 SDL2_ttf/FreeType 对
#      NotoColorEmoji 的 CBDT/CBLC 彩色位图字形表兼容性差, 是已知崩溃诱因。
# 不要重新注册任何 emoji 字体, 也不要在 markup 里写 [font=emoji], 除非先验证
# 目标设备的 Kivy 版本明确支持彩色位图字体。

_Label___init__ = KivyLabel.__init__


def _label_init_bold(self: KivyLabel, **kwargs: object) -> None:
    kwargs.setdefault("bold", True)
    _Label___init__(self, **kwargs)


def apply_global_font() -> None:
    """注册秋叶圆体 为 Kivy 全局默认字体 + 默认粗体。

    Kivy 所有 Label 默认 font_name='Roboto'，先清除内置注册，
    再用秋叶圆体 覆盖 Roboto 名字。必须在创建任何 Widget 之前调用。
    """
    if not _FONT_PATH.exists():
        return

    font_path_str = str(_FONT_PATH)

    if "Roboto" in LabelBase._fonts:
        del LabelBase._fonts["Roboto"]

    LabelBase.register(name="Roboto", fn_regular=font_path_str)

    # 全局默认粗体 (合成粗体, 无需 Bold 字重文件)
    KivyLabel.__init__ = _label_init_bold  # type: ignore[method-assign]
