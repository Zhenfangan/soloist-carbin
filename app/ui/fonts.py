"""像素字体加载器 — 注册所有像素字体到 Kivy 字体系统。"""

from __future__ import annotations

from pathlib import Path
from typing import cast

from kivy.core.text import LabelBase

from app.ui.tokens import FONTS


def load_pixel_fonts() -> dict[str, str]:
    """注册所有像素字体到 Kivy，返回已加载字体名映射。

    如果字体文件不存在，静默跳过（后续页面使用默认字体）。
    """
    loaded: dict[str, str] = {}
    font_files = cast(dict[str, str], FONTS.get("FILES", {}))

    for font_name, relative_path in font_files.items():
        font_path = Path(relative_path)
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
        if rel_path and Path(rel_path).exists():
            return name
    return "Roboto"
