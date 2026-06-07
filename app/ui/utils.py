"""像素边框与网格工具函数。

提供凸起/内凹/阴影样式生成，供所有像素组件复用。
"""

from __future__ import annotations

from typing import Any

from kivy.graphics import Color, Rectangle
from kivy.graphics.instructions import InstructionGroup

from app.ui.tokens import BORDER_WIDTH, GRID_UNIT, SHADOW_COLOR


def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
    """将 hex 色值 (如 #FFE030) 转为 Kivy RGBA (0-1) 元组。"""
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, alpha)


def snap_to_grid(value: int) -> int:
    """将数值对齐到 8px 网格 (GRID_UNIT)。

    >>> snap_to_grid(13)
    16
    >>> snap_to_grid(8)
    8
    """
    return ((value + GRID_UNIT - 1) // GRID_UNIT) * GRID_UNIT


def _build_raised_border(
    x: float, y: float, w: float, h: float,
    light_color: str, dark_color: str,
) -> InstructionGroup:
    """构建凸起像素边框 (亮面 top+left，暗面 bottom+right)。"""
    ig = InstructionGroup()
    bw = BORDER_WIDTH
    lr, lg, lb, la = _to_rgba(light_color)
    dr, dg, db, da = _to_rgba(dark_color)

    # 亮面: top edge
    ig.add(Color(lr, lg, lb, la))
    ig.add(Rectangle(pos=(x, y + h - bw), size=(w, bw)))
    # 亮面: left edge
    ig.add(Rectangle(pos=(x, y), size=(bw, h)))

    # 暗面: bottom edge
    ig.add(Color(dr, dg, db, da))
    ig.add(Rectangle(pos=(x, y), size=(w, bw)))
    # 暗面: right edge
    ig.add(Rectangle(pos=(x + w - bw, y), size=(bw, h)))

    return ig


def _build_inset_border(
    x: float, y: float, w: float, h: float,
    light_color: str, dark_color: str,
) -> InstructionGroup:
    """构建内凹像素边框 (暗面 top+left，亮面 bottom+right)。"""
    ig = InstructionGroup()
    bw = BORDER_WIDTH
    lr, lg, lb, la = _to_rgba(light_color)
    dr, dg, db, da = _to_rgba(dark_color)

    # 暗面: top edge
    ig.add(Color(dr, dg, db, da))
    ig.add(Rectangle(pos=(x, y + h - bw), size=(w, bw)))
    # 暗面: left edge
    ig.add(Rectangle(pos=(x, y), size=(bw, h)))

    # 亮面: bottom edge
    ig.add(Color(lr, lg, lb, la))
    ig.add(Rectangle(pos=(x, y), size=(w, bw)))
    # 亮面: right edge
    ig.add(Rectangle(pos=(x + w - bw, y), size=(bw, h)))

    return ig


def _build_shadow(
    x: float, y: float, w: float, h: float,
    offset: int = 2,
) -> InstructionGroup:
    """构建像素阴影 (纯黑，向右下偏移)。"""
    ig = InstructionGroup()
    r, g, b, a = _to_rgba(SHADOW_COLOR)
    ig.add(Color(r, g, b, a))
    ig.add(Rectangle(pos=(x + offset, y - offset), size=(w, h)))
    return ig


def pixel_border_raised_dict(
    light_color: str = "#FFF8E8",
    dark_color: str = "#F0E8D0",
) -> dict[str, Any]:
    """返回凸起像素边框所需的颜色配置字典。

    组件可使用此字典获取亮面/暗面色值，自行绘制。
    """
    return {"light": light_color, "dark": dark_color, "type": "raised"}


def pixel_border_inset_dict(
    light_color: str = "#FFF8E8",
    dark_color: str = "#F0E8D0",
) -> dict[str, Any]:
    """返回内凹像素边框所需的颜色配置字典。"""
    return {"light": light_color, "dark": dark_color, "type": "inset"}


def pixel_shadow_dict(offset: int = 2) -> dict[str, Any]:
    """返回像素阴影配置字典。"""
    return {"offset": offset, "color": SHADOW_COLOR}


def draw_pixel_border_raised(
    x: float, y: float, w: float, h: float,
    light_color: str = "#FFF8E8",
    dark_color: str = "#F0E8D0",
) -> InstructionGroup:
    """绘制凸起像素边框 (亮面 top+left，暗面 bottom+right)。"""
    return _build_raised_border(x, y, w, h, light_color, dark_color)


def draw_pixel_border_inset(
    x: float, y: float, w: float, h: float,
    light_color: str = "#FFF8E8",
    dark_color: str = "#F0E8D0",
) -> InstructionGroup:
    """绘制内凹像素边框 (暗面 top+left，亮面 bottom+right)。"""
    return _build_inset_border(x, y, w, h, light_color, dark_color)


def draw_pixel_shadow(
    x: float, y: float, w: float, h: float,
    offset: int = 2,
) -> InstructionGroup:
    """绘制像素阴影 (纯黑，向右下偏移)。"""
    return _build_shadow(x, y, w, h, offset)
