"""Minecraft 玻璃质感卡片背景 — 蓝白半透明 + 四角小簇方块 + 浅青边缘。

参照 Minecraft 玻璃方块设计：
1. 极淡蓝白主体（几乎纯白，半透明能透出背景）
2. 浅青色 1px 玻璃内框（模拟玻璃 pane 棱边）
3. **四个角各 2-3 个方块**（中间通透干净，斑块只点缀角落）
4. 左上 / 右上白色 2px 角落高光（玻璃反光）
"""

from __future__ import annotations

from kivy.graphics import Color, Rectangle


def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0, alpha)


# ── 玻璃色调 ──
_GLASS_BODY = "#E8F4F8"   # 极淡蓝白玻璃主体
_GLASS_EDGE = "#B8DCE4"   # 浅青色棱边高光
_GLASS_MARK = "#7AB0C0"   # 角落方块颜色（中青）

_MARK_PIXEL = 5   # 单元像素大小（6 × 0.8 ≈ 5）
_CORNER_MARGIN = 7  # 方块簇离玻璃内框距离


def draw_glass_card_bg(
    widget: object,
    border_light: str = "#FFFFFF",
    border_dark: str = "#C8D8E0",
    fill_alpha: float = 0.42,
    inset: int = 0,
) -> None:
    """绘制 Minecraft 玻璃风格卡片背景。

    inset=0 → PeriodCard / StatusBox / TaskInlineList / BetTaskItem
    inset=2 → DayCard / MonthCard
    """
    widget.canvas.before.clear()
    x, y = widget.pos
    w, h = widget.size
    bw = 2
    ix = inset

    with widget.canvas.before:
        # ── 1) 半透明阴影 ──
        Color(*_to_rgba("#000000", 0.18))
        Rectangle(pos=(x + ix + 2, y - 2), size=(w - 2 * ix, h))

        # ── 2) 极淡蓝白半透明玻璃主体 ──
        Color(*_to_rgba(_GLASS_BODY, fill_alpha))
        Rectangle(pos=(x + ix, y + ix), size=(w - 2 * ix, h - 2 * ix))

        # ── 3) 浅青色玻璃棱边（1px 内框 + 白色角落高光）──
        _draw_glass_edge(x + ix, y + ix, w - 2 * ix, h - 2 * ix)

        # ── 4) 四角小簇方块 ──
        _draw_corner_marks(x + ix, y + ix, w - 2 * ix, h - 2 * ix)

        # ── 5) 像素边框（亮面:上+左）──
        Color(*_to_rgba(border_light))
        Rectangle(pos=(x, y + h - bw), size=(w, bw))
        Rectangle(pos=(x, y), size=(bw, h))

        # ── 6) 像素边框（暗面:下+右）──
        Color(*_to_rgba(border_dark))
        Rectangle(pos=(x, y), size=(w, bw))
        Rectangle(pos=(x + w - bw, y), size=(bw, h))


def _draw_glass_edge(x: float, y: float, w: float, h: float) -> None:
    """绘制玻璃 pane 棱边 — 浅青色 1px 内框 + 左上/右上白色高光。"""
    if w < 10 or h < 10:
        return

    # 浅青色 1px 内框（距外边 3px）
    Color(*_to_rgba(_GLASS_EDGE, 0.55))
    fi = 3
    fw = 1
    Rectangle(pos=(x + fi, y + h - fi - fw), size=(w - 2 * fi, fw))           # top
    Rectangle(pos=(x + fi, y + fi), size=(w - 2 * fi, fw))                     # bottom
    Rectangle(pos=(x + fi, y + fi), size=(fw, h - 2 * fi))                     # left
    Rectangle(pos=(x + w - fi - fw, y + fi), size=(fw, h - 2 * fi))            # right

    # 左上 / 右上角白色 2px 高光（玻璃反光）
    Color(*_to_rgba("#FFFFFF", 0.80))
    hs = 2
    Rectangle(pos=(x + fi + 2, y + h - fi - 4), size=(hs, hs))
    Rectangle(pos=(x + w - fi - 5, y + h - fi - 4), size=(hs, hs))


def _draw_corner_marks(x: float, y: float, w: float, h: float) -> None:
    """在四个角各绘制 1-3 个像素方块，全部沿右上→左下对角线排列。

    布局：
    - 左上 / 右下角：3 个方块对角
    - 左下角：2 个方块对角
    - 右上角：1 个方块
    """
    if w < 36 or h < 36:
        return

    ps = _MARK_PIXEL
    m = _CORNER_MARGIN

    Color(*_to_rgba(_GLASS_MARK, 0.70))

    # ── 左上角（3 方块，右上→左下对角）──
    bx, by = x + m + ps * 2, y + h - m - ps
    for i in range(3):
        Rectangle(pos=(bx - i * ps, by - i * ps), size=(ps, ps))

    # ── 右上角（1 方块）──
    Rectangle(pos=(x + w - m - ps, y + h - m - ps), size=(ps, ps))

    # ── 左下角（2 方块，右上→左下对角）──
    bx, by = x + m + ps, y + m + ps
    for i in range(2):
        Rectangle(pos=(bx - i * ps, by - i * ps), size=(ps, ps))

    # ── 右下角（3 方块，右上→左下对角）──
    bx, by = x + w - m - ps, y + m + ps * 2
    for i in range(3):
        Rectangle(pos=(bx - i * ps, by - i * ps), size=(ps, ps))
