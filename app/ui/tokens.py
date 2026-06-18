"""设计令牌常量 — 全局配色/网格/字体/阴影定义。

所有 UI 组件必须引用此模块的常量，禁止硬编码色值。
"""

from __future__ import annotations

from typing import Final

# ============================================================
# 1.1 主色板
# ============================================================

COLORS: Final[dict[str, str]] = {
    "PRIMARY_YELLOW": "#FFE030",
    "PRIMARY_DARK": "#E0A800",
    "BG_CREAM": "#FFF8E8",
    "CARD_WHITE": "#FFFFFF",
    "CARD_SHADOW": "#F0E8D0",
    "TEXT_BROWN": "#3A3028",
    "TEXT_GRAY": "#8A8078",
    "SHADOW_BLACK": "#000000",
}

# 便捷别名
PRIMARY_YELLOW: str = COLORS["PRIMARY_YELLOW"]
PRIMARY_DARK: str = COLORS["PRIMARY_DARK"]
BG_CREAM: str = COLORS["BG_CREAM"]
CARD_WHITE: str = COLORS["CARD_WHITE"]
CARD_SHADOW: str = COLORS["CARD_SHADOW"]
TEXT_BROWN: str = COLORS["TEXT_BROWN"]
TEXT_GRAY: str = COLORS["TEXT_GRAY"]
SHADOW_BLACK: str = COLORS["SHADOW_BLACK"]

# ============================================================
# 1.2 多巴胺辅色 (每色系配亮面/暗面)
# ============================================================

DOPAMINE_COLORS: Final[dict[str, dict[str, str]]] = {
    "coral": {"light": "#FF6B8A", "dark": "#D94A6A"},
    "mint": {"light": "#50E8B0", "dark": "#30C090"},
    "lavender": {"light": "#B090F0", "dark": "#9070D0"},
    "sky": {"light": "#60C8FF", "dark": "#40A0E0"},
    "warm_orange": {"light": "#FF9040", "dark": "#E07020"},
    "watermelon": {"light": "#FF5070", "dark": "#E03050"},
}

# ============================================================
# 1.3 功能语义色
# ============================================================

SEMANTIC_COLORS: Final[dict[str, dict[str, str]]] = {
    "normal": {"block": "#E0F4FF", "border": "#60C8FF", "icon": "#60C8FF"},
    "late": {"block": "#FFE8EC", "border": "#FF6B8A", "icon": "#FF6B8A"},
    "early_leave": {"block": "#FFF0E8", "border": "#FF9040", "icon": "#FF9040"},
    "absent": {"block": "#FFE0E8", "border": "#FF5070", "icon": "#FF5070"},
    "leave": {"block": "#F0ECFF", "border": "#B090F0", "icon": "#B090F0"},
    "shooting": {"block": "#FFF8E0", "border": "#FF9040", "icon": "#FF9040"},
    "completed": {"block": "#E0FFF0", "border": "#50E8B0", "icon": "#50E8B0"},
}

# ============================================================
# 1.4 网格常量
# ============================================================

GRID: Final[dict[str, int]] = {
    "UNIT": 8,
    "BORDER_WIDTH": 2,
    "BTN_HEIGHT": 48,
    "BTN_HEIGHT_LARGE": 64,
    "BTN_HEIGHT_SMALL": 36,
    "CARD_PADDING": 16,
    "NAV_HEIGHT": 72,
    "ICON_SIZE": 40,
    "SPRITE_SIZE": 64,
}

GRID_UNIT: int = GRID["UNIT"]
BORDER_WIDTH: int = GRID["BORDER_WIDTH"]
BTN_HEIGHT: int = GRID["BTN_HEIGHT"]
CARD_PADDING: int = GRID["CARD_PADDING"]
NAV_HEIGHT: int = GRID["NAV_HEIGHT"]
ICON_SIZE: int = GRID["ICON_SIZE"]
SPRITE_SIZE: int = GRID["SPRITE_SIZE"]

# grass-front.png 顶端有色像素在 750px 窗口中距底部的距离（px）
# = 181 * 750 / 1080，草地前景层覆盖范围的上界
GRASS_INSET: int = 126

# ============================================================
# 1.5 像素字体常量
# ============================================================

FONTS: Final[dict[str, object]] = {
    "DEFAULT": "QiuYeYuanTi",
    "PIXEL": "QiuYeYuanTi",
    "HANZI_PIXEL": "QiuYeYuanTi",
    "SIZE_TITLE": 18,
    "SIZE_BODY": 14,
    "SIZE_SMALL": 10,
    "FILES": {
        "QiuYeYuanTi": "app/ui/assets/fonts/QiuYeYuanTi-16.ttf",
    },
}

FONT_PIXEL: str = FONTS["PIXEL"]  # type: ignore[assignment]
FONT_HANZI_PIXEL: str = FONTS["HANZI_PIXEL"]  # type: ignore[assignment]
FONT_SIZE_TITLE: int = FONTS["SIZE_TITLE"]  # type: ignore[assignment]
FONT_SIZE_BODY: int = FONTS["SIZE_BODY"]  # type: ignore[assignment]
FONT_SIZE_SMALL: int = FONTS["SIZE_SMALL"]  # type: ignore[assignment]

# ============================================================
# 1.6 像素阴影常量
# ============================================================

SHADOWS: Final[dict[str, object]] = {
    "OFFSET": 2,
    "COLOR": "#000000",
    "LIGHT_OFFSET": (2, 2),  # (x, y) for light face
    "DARK_OFFSET": (-2, -2),  # (x, y) for dark face
}

SHADOW_OFFSET: int = SHADOWS["OFFSET"]  # type: ignore[assignment]
SHADOW_COLOR: str = SHADOWS["COLOR"]  # type: ignore[assignment]
