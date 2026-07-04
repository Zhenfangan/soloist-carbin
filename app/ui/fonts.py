"""全局字体加载器 — 注册秋叶圆体 为全局默认字体，默认粗体，并注册彩色 emoji。"""

from __future__ import annotations

from pathlib import Path

from kivy.core.text import LabelBase
from kivy.uix.label import Label as KivyLabel

_FONT_DIR = (Path(__file__).parent / "assets" / "fonts").resolve()
_FONT_PATH = _FONT_DIR / "QiuYeYuanTi-16.ttf"

# Windows 自带 Segoe UI Emoji（彩色 emoji 字体）
#
# 曾尝试加入 /system/fonts/NotoColorEmoji.ttf 修复安卓真机 emoji 显示成方块的
# 问题, 但真机测试出现启动即崩溃循环 (logcat: Fatal signal 11 SIGSEGV,
# tid=Jit thread pool) —— Kivy 的 SDL2_ttf/FreeType 文字渲染管线对
# NotoColorEmoji 使用的 CBDT/CBLC 彩色位图字形表兼容性差, 是已知的崩溃诱因。
# 显示成方块是外观问题, 崩溃是致命问题, 两害相权已回退, 不要重新加入
# 这个字体路径, 除非先验证目标设备的 Kivy 版本明确支持彩色位图字体。
_EMOJI_FONT_CANDIDATES = [
    Path("C:/Windows/Fonts/seguiemj.ttf"),
    Path("C:/Windows/Fonts/segoeuiemoji.ttf"),
]

_Label___init__ = KivyLabel.__init__


def _label_init_bold(self: KivyLabel, **kwargs: object) -> None:
    kwargs.setdefault("bold", True)
    _Label___init__(self, **kwargs)


def apply_global_font() -> None:
    """注册秋叶圆体 为 Kivy 全局默认字体 + 默认粗体 + 彩色 emoji 字体。

    Kivy 所有 Label 默认 font_name='Roboto'，先清除内置注册，
    再用秋叶圆体 覆盖 Roboto 名字。必须在创建任何 Widget 之前调用。

    额外注册 'emoji' 字体名指向 Segoe UI Emoji；标签里通过
    markup `[font=emoji]🎯[/font]` 即可显示彩色 emoji。
    """
    if not _FONT_PATH.exists():
        return

    font_path_str = str(_FONT_PATH)

    if "Roboto" in LabelBase._fonts:
        del LabelBase._fonts["Roboto"]

    LabelBase.register(name="Roboto", fn_regular=font_path_str)

    # 全局默认粗体 (合成粗体, 无需 Bold 字重文件)
    KivyLabel.__init__ = _label_init_bold  # type: ignore[method-assign]

    # 注册 emoji 字体（Windows Segoe UI Emoji）
    for emoji_path in _EMOJI_FONT_CANDIDATES:
        if emoji_path.exists():
            LabelBase.register(name="emoji", fn_regular=str(emoji_path))
            break


def emj(char: str) -> str:
    """包装 emoji 字符为 markup —— 标签需 markup=True 才生效。

    若 emoji 字体未注册（如测试环境跳过了 apply_global_font），
    返回纯字符避免 Label 渲染时找不到 emoji.ttf 报错。
    """
    if "emoji" not in LabelBase._fonts:
        return char
    return f"[font=emoji]{char}[/font]"
