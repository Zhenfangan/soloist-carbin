"""生成 16 个像素功能图标 PNG 文件。

画布 16×16，单色为主最多 2 色，1px 线条，nearest-neighbor 放大。
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

ICONS_DIR = Path(__file__).parent.parent / "app" / "ui" / "assets" / "icons"

# 图标调色板: 索引用于按需染色，生成时用占位色
FG_COLOR = (60, 56, 40)  # 前景色 (深棕近似)
FG2_COLOR = (255, 224, 48)  # 第二色 (明黄)


def _mk_grid() -> list[list[int]]:
    """创建 16×16 透明画布。"""
    return [[0 for _ in range(16)] for _ in range(16)]


def _draw_pixel(grid: list[list[int]], x: int, y: int, color: int = 1) -> None:
    if 0 <= x < 16 and 0 <= y < 16:
        grid[y][x] = color


def _draw_rect(grid: list[list[int]], x: int, y: int, w: int, h: int, color: int = 1) -> None:
    for dy in range(h):
        for dx in range(w):
            _draw_pixel(grid, x + dx, y + dy, color)


def _draw_line(grid: list[list[int]], x1: int, y1: int, x2: int, y2: int, color: int = 1) -> None:
    """Bresenham 直线。"""
    dx = abs(x2 - x1)
    dy = -abs(y2 - y1)
    sx = 1 if x1 < x2 else -1
    sy = 1 if y1 < y2 else -1
    err = dx + dy
    while True:
        _draw_pixel(grid, x1, y1, color)
        if x1 == x2 and y1 == y2:
            break
        e2 = 2 * err
        if e2 >= dy:
            if x1 == x2:
                break
            err += dy
            x1 += sx
        if e2 <= dx:
            if y1 == y2:
                break
            err += dx
            y1 += sy


def _to_img(grid: list[list[int]], fg: tuple[int, ...], fg2: tuple[int, ...] | None = None) -> Image.Image:
    """将网格转为 16×16 RGBA PNG 图像。"""
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    px = img.load()
    for y in range(16):
        for x in range(16):
            if grid[y][x] == 1:
                px[x, y] = (*fg, 255)
            elif grid[y][x] == 2 and fg2:
                px[x, y] = (*fg2, 255)
    # nearest-neighbor 放大至 32×32
    return img.resize((32, 32), Image.NEAREST)


# ── 图标定义 ──

def make_checkin_tab() -> Image.Image:
    """打卡 Tab — 方形印章 + 内勾号。"""
    g = _mk_grid()
    _draw_rect(g, 2, 3, 12, 11, 1)  # 外框
    _draw_rect(g, 3, 4, 10, 9, 0)  # 清空内部
    # 勾号 ✓
    _draw_line(g, 5, 9, 7, 11, 1)
    _draw_line(g, 7, 11, 12, 5, 1)
    return _to_img(g, FG_COLOR)


def make_history_tab() -> Image.Image:
    """历史 Tab — 日历格 (左上折角)。"""
    g = _mk_grid()
    _draw_rect(g, 2, 3, 12, 11, 1)  # 外框
    _draw_rect(g, 3, 4, 10, 9, 0)
    # 折角
    _draw_rect(g, 2, 3, 4, 3, 2)  # 右上折角 明黄色
    _draw_line(g, 6, 3, 6, 5, 1)
    # 日期线
    _draw_line(g, 3, 7, 13, 7, 1)
    # 几个小方块代表日期
    for dx in range(4):
        _draw_pixel(g, 5 + dx * 2, 10, 1)
    return _to_img(g, FG_COLOR, FG2_COLOR)


def make_bet_tab() -> Image.Image:
    """对赌 Tab — 十字准星靶心。"""
    g = _mk_grid()
    # 外圆 (用方形近似)
    _draw_rect(g, 3, 3, 10, 10, 1)
    _draw_rect(g, 4, 4, 8, 8, 0)
    _draw_rect(g, 5, 5, 6, 6, 1)
    _draw_rect(g, 6, 6, 4, 4, 0)
    _draw_pixel(g, 8, 8, 2)
    # 十字线
    _draw_line(g, 8, 1, 8, 3, 1)
    _draw_line(g, 8, 13, 8, 15, 1)
    _draw_line(g, 1, 8, 3, 8, 1)
    _draw_line(g, 13, 8, 15, 8, 1)
    return _to_img(g, FG_COLOR, FG2_COLOR)


def make_settings_tab() -> Image.Image:
    """设置 Tab — 齿轮 (8 齿)。"""
    g = _mk_grid()
    # 中心
    _draw_rect(g, 6, 6, 4, 4, 1)
    _draw_rect(g, 7, 7, 2, 2, 0)
    # 8 个齿 (上下左右 + 对角线)
    _draw_rect(g, 7, 1, 2, 2, 1)
    _draw_rect(g, 7, 13, 2, 2, 1)
    _draw_rect(g, 1, 7, 2, 2, 1)
    _draw_rect(g, 13, 7, 2, 2, 1)
    _draw_pixel(g, 2, 2, 1)
    _draw_pixel(g, 12, 2, 1)
    _draw_pixel(g, 2, 12, 1)
    _draw_pixel(g, 12, 12, 1)
    return _to_img(g, FG_COLOR)


def make_checkin_btn() -> Image.Image:
    """签到按钮 — 空心方格 → 填实 + 勾。"""
    g = _mk_grid()
    _draw_rect(g, 2, 3, 12, 11, 1)
    _draw_rect(g, 3, 4, 10, 9, 0)
    # 填充 + 勾
    _draw_rect(g, 4, 5, 8, 7, 2)
    _draw_line(g, 6, 9, 8, 11, 1)
    _draw_line(g, 8, 11, 12, 6, 1)
    return _to_img(g, FG_COLOR, FG2_COLOR)


def make_checkout_btn() -> Image.Image:
    """签退按钮 — 空心方格 + 箭头。"""
    g = _mk_grid()
    _draw_rect(g, 2, 3, 12, 11, 1)
    _draw_rect(g, 3, 4, 10, 9, 0)
    # 箭头 →
    _draw_line(g, 4, 8, 10, 8, 1)  # 横线
    _draw_line(g, 8, 6, 10, 8, 1)  # 上箭头
    _draw_line(g, 8, 10, 10, 8, 1)  # 下箭头
    return _to_img(g, FG_COLOR)


def make_leave_btn() -> Image.Image:
    """请假 — 方形信封。"""
    g = _mk_grid()
    _draw_rect(g, 2, 4, 12, 9, 1)  # 信封主体
    _draw_rect(g, 3, 5, 10, 7, 0)
    # 信封盖
    _draw_line(g, 2, 4, 8, 9, 1)
    _draw_line(g, 14, 4, 8, 9, 1)
    _draw_line(g, 2, 4, 14, 4, 1)
    return _to_img(g, FG_COLOR)


def make_add_btn() -> Image.Image:
    """添加任务 — 十字加号。"""
    g = _mk_grid()
    _draw_rect(g, 7, 2, 2, 12, 1)  # 竖线
    _draw_rect(g, 2, 7, 12, 2, 1)  # 横线
    return _to_img(g, FG_COLOR)


def make_report_btn() -> Image.Image:
    """战报入口 — 卷轴 (长方形 + 两端凸起)。"""
    g = _mk_grid()
    _draw_rect(g, 2, 5, 12, 7, 1)  # 纸面
    _draw_rect(g, 3, 6, 10, 5, 0)
    # 卷轴两端
    _draw_rect(g, 1, 4, 2, 9, 1)
    _draw_rect(g, 13, 4, 2, 9, 1)
    # 文字线
    for dy in range(3):
        _draw_line(g, 4, 7 + dy * 2, 11, 7 + dy * 2, 1)
    return _to_img(g, FG_COLOR)


def make_save_btn() -> Image.Image:
    """保存相册 — 向下箭头 + 横线。"""
    g = _mk_grid()
    _draw_line(g, 3, 7, 13, 7, 1)  # 横线
    _draw_line(g, 6, 10, 8, 7, 1)  # 左上斜线
    _draw_line(g, 10, 10, 8, 7, 1)  # 右上斜线
    _draw_line(g, 8, 2, 8, 7, 1)  # 竖线 (箭头杆)
    return _to_img(g, FG_COLOR)


def make_settle_btn() -> Image.Image:
    """结算 — 天平 (竖线 + 横杆 + 两端)。"""
    g = _mk_grid()
    _draw_line(g, 8, 3, 8, 12, 1)  # 竖杆
    _draw_line(g, 3, 3, 13, 3, 1)  # 横杆
    # 两端盘子
    _draw_rect(g, 1, 1, 4, 2, 1)
    _draw_rect(g, 11, 1, 4, 2, 1)
    # 底座
    _draw_rect(g, 5, 12, 6, 2, 1)
    return _to_img(g, FG_COLOR)


def make_arrow_left() -> Image.Image:
    """箭头 ← — 三角形箭头。"""
    g = _mk_grid()
    for i in range(5):
        _draw_line(g, 10 - i, 3 + i, 10 - i, 12 - i, 1)
    return _to_img(g, FG_COLOR)


def make_arrow_right() -> Image.Image:
    """箭头 → — 三角形箭头。"""
    g = _mk_grid()
    for i in range(5):
        _draw_line(g, 6 + i, 3 + i, 6 + i, 12 - i, 1)
    return _to_img(g, FG_COLOR)


def make_check_mark() -> Image.Image:
    """勾号 ✓。"""
    g = _mk_grid()
    _draw_line(g, 3, 8, 6, 11, 1)
    _draw_line(g, 6, 11, 13, 3, 1)
    return _to_img(g, FG_COLOR)


def make_cross() -> Image.Image:
    """叉号 ✗。"""
    g = _mk_grid()
    _draw_line(g, 3, 3, 12, 12, 1)
    _draw_line(g, 12, 3, 3, 12, 1)
    return _to_img(g, FG_COLOR)


def make_warning() -> Image.Image:
    """警告 ⚠。"""
    g = _mk_grid()
    # 三角
    _draw_line(g, 8, 1, 1, 12, 1)
    _draw_line(g, 1, 12, 15, 12, 1)
    _draw_line(g, 15, 12, 8, 1, 1)
    # 填充
    for y in range(3, 11):
        for x in range(8 - (y - 1) // 2, 8 + (y - 1) // 2 + 1):
            if x > 2 and x < 14:
                _draw_pixel(g, x, y, 2)
    # 感叹号
    _draw_rect(g, 7, 5, 2, 4, 1)
    _draw_pixel(g, 8, 10, 1)
    return _to_img(g, FG_COLOR, FG2_COLOR)


ICON_DEFS = {
    "tab_checkin.png": make_checkin_tab,
    "tab_history.png": make_history_tab,
    "tab_bet.png": make_bet_tab,
    "tab_settings.png": make_settings_tab,
    "btn_checkin.png": make_checkin_btn,
    "btn_checkout.png": make_checkout_btn,
    "btn_leave.png": make_leave_btn,
    "btn_add.png": make_add_btn,
    "btn_report.png": make_report_btn,
    "btn_save.png": make_save_btn,
    "btn_settle.png": make_settle_btn,
    "arrow_left.png": make_arrow_left,
    "arrow_right.png": make_arrow_right,
    "check_mark.png": make_check_mark,
    "cross.png": make_cross,
    "warning.png": make_warning,
}


def main() -> int:
    ICONS_DIR.mkdir(parents=True, exist_ok=True)

    for filename, gen_func in ICON_DEFS.items():
        path = ICONS_DIR / filename
        img = gen_func()
        img.save(str(path))
        print(f"  Generated {filename} ({img.width}×{img.height})")

    print(f"\nAll {len(ICON_DEFS)} icons generated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
