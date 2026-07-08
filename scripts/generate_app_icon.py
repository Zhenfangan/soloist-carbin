"""生成 App 启动图标 + 启动页(presplash) —— 像素风北欧小屋主题。

画布 32×32 手绘像素画(与 doc/superpowers 设计方案 A2「小屋打卡」/
B2「小屋草地」一致), nearest-neighbor 放大到各尺寸。产出:

- data/icon.png            — 传统方形图标(旧启动器/Play 商店), 不透明奶油底
- data/icon_fg.png         — 自适应图标前景层(透明底, 供 Android 8+ 遮罩)
- data/icon_bg.png         — 自适应图标背景层(纯色奶油, 铺满画布)
- data/presplash.png       — 竖屏启动页(小屋坐在像素草地上 + 木牌读条)

自适应前景层按 Android 安全区(内切圆直径为画布 61%)留白: 核心的小屋
主体 + 对勾徽标落在安全区内, 松树/太阳/烟等边缘点缀允许在圆形遮罩下
轻微裁切(方形/圆角启动器上完整可见)。

用法: python scripts/generate_app_icon.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.ui.tokens import COLORS, DOPAMINE_COLORS  # noqa: E402

DATA_DIR = Path(__file__).parent.parent / "data"
FONT_PATH = Path(__file__).parent.parent / "app" / "ui" / "assets" / "fonts" / "QiuYeYuanTi-16.ttf"

N = 32  # 原生像素网格边长
RGBA = tuple[int, int, int, int]

# ── 调色板: App token 为主, 场景专用色补充(松树/屋顶/门/烟囱等无对应 token) ──
CREAM = COLORS["BG_CREAM"]
INK = COLORS["TEXT_BROWN"]
GLOW = COLORS["PRIMARY_YELLOW"]
GLOW_DK = COLORS["PRIMARY_DARK"]
MINT = DOPAMINE_COLORS["mint"]["light"]
MINT_DK = DOPAMINE_COLORS["mint"]["dark"]
CORAL = DOPAMINE_COLORS["coral"]["light"]
SKY_BLUE = "#60C8FF"

ROOF = "#FF9040"
ROOF_DK = "#E07020"
WALL = "#FCEFCF"
WALL_SH = "#EAD9AC"
DOOR = "#6E4A2A"
DOOR_HI = "#8A6238"
CHIMNEY = "#D9663E"
SMOKE = "#EFE6D2"
TRUNK = "#6E4A2A"
GRASS = MINT
GRASS_DK = MINT_DK
WHITE = "#FFFFFF"


def _hex(c: str, a: int = 255) -> RGBA:
    h = c.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


# ── 像素网格工具(风格照 scripts/generate_icons.py: Bresenham 直线, 透明底) ──

Grid = list[list[RGBA | None]]


def _mk_grid(n: int = N) -> Grid:
    return [[None for _ in range(n)] for _ in range(n)]


def _px(g: Grid, x: int, y: int, c: RGBA | None) -> None:
    if c is not None and 0 <= x < len(g) and 0 <= y < len(g):
        g[y][x] = c


def _rect(g: Grid, x: int, y: int, w: int, h: int, c: RGBA | None) -> None:
    for dy in range(h):
        for dx in range(w):
            _px(g, x + dx, y + dy, c)


def _line(g: Grid, x0: int, y0: int, x1: int, y1: int, c: RGBA, thickness: int = 1) -> None:
    """Bresenham 直线, thickness 向下加厚 —— 用于保证对勾等折线两段严格相连,
    不会像手工枚举断点那样漏像素(真实教训: 见 checkmark 断线 bug)。"""
    dx, sx = abs(x1 - x0), (1 if x0 < x1 else -1)
    dy, sy = -abs(y1 - y0), (1 if y0 < y1 else -1)
    err, x, y = dx + dy, x0, y0
    while True:
        for t in range(thickness):
            _px(g, x, y + t, c)
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy


def _disc(g: Grid, cx: int, cy: int, r: int, c: RGBA) -> None:
    for yy in range(-r, r + 1):
        for xx in range(-r, r + 1):
            if xx * xx + yy * yy <= r * r + 1:
                _px(g, cx + xx, cy + yy, c)


def _roof_tri(g: Grid, cx: int, base_y: int, base_half: int, c: RGBA, edge: RGBA) -> None:
    """对称三角屋顶: base 行最宽, 向上每行两侧各收 1。"""
    for i in range(base_half + 1):
        y = base_y - i
        half = base_half - i
        _rect(g, cx - half, y, half * 2, 1, c)
        _px(g, cx - half, y, edge)
        _px(g, cx + half - 1, y, edge)


# ── 场景绘制(与已获批的 JS 方案 A2 逐像素对应) ──

def draw_cabin(g: Grid, transparent_bg: bool = False) -> None:
    """白天小屋(A2 基底场景)。transparent_bg=True 时天空区域透明,
    供自适应图标前景层 / 启动页合成到自定义背景上使用。"""
    if not transparent_bg:
        _rect(g, 0, 0, 32, 32, _hex(CREAM))
    _disc(g, 26, 6, 3, _hex(GLOW))  # 太阳

    # 地面(草地)
    _rect(g, 0, 28, 32, 4, _hex(GRASS))
    for i in range(0, 32, 3):
        _px(g, i + 1, 28, _hex(GRASS_DK))

    # 松树(左)
    _rect(g, 4, 25, 1, 3, _hex(TRUNK))
    for r in range(6):
        _rect(g, 4 - r, 25 - r, 1 + r * 2, 1, _hex(MINT_DK if r % 2 else MINT))
    _px(g, 4, 18, _hex(MINT))

    # 屋顶
    _roof_tri(g, 17, 15, 10, _hex(ROOF), _hex(ROOF_DK))
    _rect(g, 7, 15, 20, 1, _hex(ROOF_DK))

    # 墙体
    _rect(g, 10, 16, 16, 12, _hex(WALL))
    _rect(g, 10, 16, 1, 12, _hex(WALL_SH))
    _rect(g, 25, 16, 1, 12, _hex(WALL_SH))
    _rect(g, 9, 16, 1, 12, _hex(INK))
    _rect(g, 26, 16, 1, 12, _hex(INK))
    _rect(g, 9, 27, 18, 1, _hex(INK))

    # 窗
    _rect(g, 17, 18, 6, 5, _hex(SKY_BLUE))
    _rect(g, 16, 17, 8, 1, _hex(INK))
    _rect(g, 16, 23, 8, 1, _hex(INK))
    _rect(g, 16, 17, 1, 7, _hex(INK))
    _rect(g, 23, 17, 1, 7, _hex(INK))
    _rect(g, 19, 18, 1, 5, _hex(INK))
    _rect(g, 17, 20, 6, 1, _hex(INK))

    # 门
    _rect(g, 12, 22, 3, 6, _hex(DOOR))
    _rect(g, 12, 22, 1, 6, _hex(DOOR_HI))
    _rect(g, 11, 21, 5, 1, _hex(INK))
    _rect(g, 11, 22, 1, 6, _hex(INK))
    _rect(g, 15, 22, 1, 6, _hex(INK))
    _px(g, 14, 25, _hex(GLOW))

    # 烟囱 + 烟
    _rect(g, 21, 9, 2, 6, _hex(CHIMNEY))
    _rect(g, 21, 9, 2, 1, _hex(ROOF_DK))
    _px(g, 22, 7, _hex(SMOKE))
    _px(g, 23, 5, _hex(SMOKE))


def stamp_check(g: Grid) -> None:
    """珊瑚色对勾徽标(右下角) —— thickLine 连续画线, 已验证两段严格相连、
    不戳出徽标圆边界(见设计复核: 21 像素单一连通块)。"""
    cx, cy, r = 24, 24, 6
    _disc(g, cx, cy, r + 1, _hex(INK))
    _disc(g, cx, cy, r, _hex(CORAL))
    _disc(g, cx, cy, r - 1, _hex(CORAL))
    _line(g, 19, 24, 22, 27, _hex(WHITE), thickness=2)
    _line(g, 22, 27, 28, 20, _hex(WHITE), thickness=2)


def grid_to_image(g: Grid, n: int = N) -> Image.Image:
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    px = img.load()
    for y in range(n):
        for x in range(n):
            if g[y][x] is not None:
                px[x, y] = g[y][x]
    return img


def _paste_centered_scaled(canvas: Image.Image, art: Image.Image, fill_frac: float) -> None:
    """把 art(32×32) 用 NEAREST 放大到 canvas 边长 × fill_frac, 居中贴上。"""
    side = int(canvas.width * fill_frac)
    scaled = art.resize((side, side), Image.NEAREST)
    x = (canvas.width - side) // 2
    y = (canvas.height - side) // 2
    canvas.alpha_composite(scaled, (x, y))


# ── 图标三件套 ──

def make_legacy_icon(size: int = 512) -> Image.Image:
    """传统方形图标 —— 不透明奶油底 + 完整场景, 边距 ~7.5%(旧启动器圆角裁切安全)。"""
    g = _mk_grid()
    draw_cabin(g, transparent_bg=False)
    stamp_check(g)
    art = grid_to_image(g)

    canvas = Image.new("RGBA", (size, size), _hex(CREAM))
    _paste_centered_scaled(canvas, art, fill_frac=0.86)
    return canvas.convert("RGB")


def make_adaptive_foreground(size: int = 512) -> Image.Image:
    """自适应图标前景层 —— 透明底, 核心内容收在安全区(圆遮罩下不裁核心)。"""
    g = _mk_grid()
    draw_cabin(g, transparent_bg=True)
    stamp_check(g)
    art = grid_to_image(g)

    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    _paste_centered_scaled(canvas, art, fill_frac=0.72)
    return canvas


def make_adaptive_background(size: int = 512) -> Image.Image:
    """自适应图标背景层 —— 纯奶油底铺满(遮罩形状由前景决定, 背景恒不透明)。"""
    return Image.new("RGB", (size, size), _hex(CREAM))


# ── 启动页(B2 小屋草地) ──

# 画布宽高比须与下方参考构图(240×496, 1:2.067)一致 —— 否则按参考坐标 s()
# 换算出的纵向元素(木牌/读条)会画到实际画布高度之外而被裁掉(曾复现: 用
# 1080×1920 时读条底部溢出画布 24px, 只剩一条边可见)。
PW = 1080
PH = round(PW * 496 / 240)


def _lerp_color(c1: RGBA, c2: RGBA, t: float) -> RGBA:
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(4))  # type: ignore[return-value]


def make_presplash() -> Image.Image:
    canvas = Image.new("RGBA", (PW, PH), (0, 0, 0, 255))
    px = canvas.load()

    # 天空竖向渐变: 暖橙调 → 奶油 → 淡薄荷(呼应 App 内 landscape 层次)
    top, mid, bot = _hex("#FFF3D6"), _hex(CREAM), _hex("#EAFBF2")
    mid_y = int(PH * 0.55)
    for y in range(PH):
        if y <= mid_y:
            t = y / mid_y
            c = _lerp_color(top, mid, t)
        else:
            t = (y - mid_y) / (PH - mid_y)
            c = _lerp_color(mid, bot, t)
        for x in range(PW):
            px[x, y] = c

    draw = ImageDraw.Draw(canvas)

    # 像素云朵
    scale = PW / 240  # 以 240 宽的原始构图为基准换算
    def s(v: float) -> int:
        return int(v * scale)
    cloud_c = _hex(WHITE)
    for cx, cy in [(40, 70), (150, 110), (80, 150)]:
        draw.rectangle([s(cx), s(cy), s(cx + 34), s(cy + 8)], fill=cloud_c)
        draw.rectangle([s(cx + 8), s(cy - 6), s(cx + 28), s(cy + 2)], fill=cloud_c)

    # 草地
    grass_top = s(372)
    draw.rectangle([0, grass_top, PW, PH], fill=_hex(GRASS))
    draw.rectangle([0, grass_top, PW, grass_top + s(4)], fill=_hex(GRASS_DK))
    xx = 0
    while xx < PW:
        draw.rectangle([xx + s(3), grass_top - s(4), xx + s(6), grass_top], fill=_hex(GRASS_DK))
        xx += s(10)

    # 小屋(透明底场景, 直接叠到草地上方) + 对勾徽标
    g = _mk_grid()
    draw_cabin(g, transparent_bg=True)
    stamp_check(g)
    art = grid_to_image(g)
    art_side = s(136)
    art_scaled = art.resize((art_side, art_side), Image.NEAREST)
    art_x = (PW - art_side) // 2
    art_y = s(208)
    canvas.alpha_composite(art_scaled, (art_x, art_y))
    draw = ImageDraw.Draw(canvas)  # alpha_composite 后需重新取 draw 句柄

    # 木牌 + 分段像素读条(静态 62%, 呼应设计稿)
    plaque_x0, plaque_y0 = s(40), s(410)
    plaque_x1, plaque_y1 = s(200), s(432)
    draw.rectangle([plaque_x0, plaque_y0, plaque_x1, plaque_y1], fill=_hex(DOOR))
    draw.rectangle([plaque_x0, plaque_y0, plaque_x1, plaque_y0 + s(3)], fill=_hex(DOOR_HI))

    segs, prog = 10, 0.62
    lit = round(segs * prog)
    bar_x0, bar_y0 = s(48), s(415)
    bar_x1, bar_y1 = s(184), s(427)
    bar_w = bar_x1 - bar_x0
    gap = s(2)
    seg_w = (bar_w - gap * (segs - 1)) / segs
    for i in range(segs):
        sx = bar_x0 + i * (seg_w + gap)
        draw.rectangle([sx - 1, bar_y0 - 1, sx + seg_w + 1, bar_y1 + 1], fill=_hex(INK))
        fill_c = _hex(GLOW) if i < lit else _hex("#6E4A2A")
        draw.rectangle([sx, bar_y0, sx + seg_w, bar_y1], fill=fill_c)

    # 文字: 中文书名号风格标题 + 英文小标
    title_font = ImageFont.truetype(str(FONT_PATH), s(30))
    sub_font = ImageFont.truetype(str(FONT_PATH), s(13))

    title = "独奏者小屋"
    tb = draw.textbbox((0, 0), title, font=title_font)
    tw = tb[2] - tb[0]
    draw.text(((PW - tw) / 2, s(78)), title, font=title_font, fill=_hex(INK))

    sub = "SOLOIST CABIN"
    sb = draw.textbbox((0, 0), sub, font=sub_font)
    sw = sb[2] - sb[0]
    draw.text(((PW - sw) / 2, s(118)), sub, font=sub_font, fill=_hex(COLORS["TEXT_GRAY"]))

    hint = "整理小屋中 · 62%"
    hb = draw.textbbox((0, 0), hint, font=sub_font)
    hw = hb[2] - hb[0]
    draw.text(((PW - hw) / 2, s(452)), hint, font=sub_font, fill=_hex(COLORS["TEXT_GRAY"]))

    return canvas.convert("RGB")


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    outputs = {
        "icon.png": make_legacy_icon(),
        "icon_fg.png": make_adaptive_foreground(),
        "icon_bg.png": make_adaptive_background(),
        "presplash.png": make_presplash(),
    }
    for name, img in outputs.items():
        path = DATA_DIR / name
        img.save(str(path))
        print(f"  Generated {name} ({img.width}×{img.height}, mode={img.mode})")

    print(f"\nAll {len(outputs)} assets written to {DATA_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
