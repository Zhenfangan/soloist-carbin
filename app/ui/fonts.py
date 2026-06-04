"""全局字体加载器 — 注册 SmileySans-Oblique 为全局默认字体。"""

from __future__ import annotations

from pathlib import Path

from kivy.core.text import LabelBase

_FONT_DIR = (Path(__file__).parent / "assets" / "fonts").resolve()
_FONT_PATH = _FONT_DIR / "SmileySans-Oblique.ttf"


def apply_global_font() -> None:
    """注册 SmileySans-Oblique 为 Kivy 全局默认字体。

    Kivy 所有 Label 默认 font_name='Roboto'，先清除内置注册，
    再用 SmileySans 覆盖 Roboto 名字。必须在创建任何 Widget 之前调用。
    """
    if not _FONT_PATH.exists():
        return

    font_path_str = str(_FONT_PATH)

    if "Roboto" in LabelBase._fonts:
        del LabelBase._fonts["Roboto"]

    LabelBase.register(name="Roboto", fn_regular=font_path_str)
