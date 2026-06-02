"""像素字体加载器 — 注册所有像素字体到 Kivy 字体系统。"""

from __future__ import annotations

from pathlib import Path
from typing import cast

from kivy.core.text import LabelBase

from app.ui.tokens import FONTS

_FONT_DIR = (Path(__file__).parent / "assets" / "fonts").resolve()


def load_pixel_fonts() -> dict[str, str]:
    """注册所有像素字体到 Kivy，返回已加载字体名映射。"""
    loaded: dict[str, str] = {}
    font_files = cast(dict[str, str], FONTS.get("FILES", {}))

    for font_name, relative_path in font_files.items():
        # 相对路径 → 基于 FONT_DIR 解析
        font_path = Path(relative_path)
        if not font_path.is_absolute():
            # 尝试相对工区根目录
            font_path = Path.cwd() / relative_path
            if not font_path.exists():
                # fallback: 基于此模块位置
                font_path = (_FONT_DIR / font_name.replace("-", "")).with_suffix(".ttf")
        if font_path.exists() and font_path.is_file():
            try:
                LabelBase.register(name=font_name, fn_regular=str(font_path))
                loaded[font_name] = str(font_path)
            except Exception:
                pass

    return loaded


def get_available_font_name() -> str:
    """返回第一个可用的像素字体名，如果都没有则返回默认字体。"""
    font_files = cast(dict[str, str], FONTS.get("FILES", {}))
    for name in ["press-start-2p", "silkscreen"]:
        rel_path = font_files.get(name, "")
        font_path = Path(rel_path)
        if not font_path.is_absolute():
            font_path = Path.cwd() / rel_path
            if not font_path.exists():
                prefix = name.replace("-", "").replace("2p", "2P")
                font_path = _FONT_DIR / f"{prefix}-Regular.ttf"
        if font_path.exists():
            return name
    return "Roboto"


def apply_global_font() -> None:
    """注册像素字体到 Kivy 系统（不覆盖全局默认字体以保留中文渲染）。

    像素字体通过 font_name 属性在需要的组件上显式使用。
    必须在创建任何 Widget 之前调用。
    """
    load_pixel_fonts()
