"""生成 5 个像素角色 sprite sheet PNG 文件。

每角色 4 帧横向排列，使用 PIL/Pillow 逐像素绘制。
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

SPRITES_DIR = Path(__file__).parent.parent / "app" / "ui" / "assets" / "sprites"

# ── 角色色板 ──────────────────────────────────────────
# 索引: 0=透明, 1=主色, 2=亮面, 3=暗面, 4=特征色

DUDU_PALETTE = [(0, 0, 0, 0), (212, 160, 64), (240, 192, 96), (168, 128, 48), (107, 68, 32)]
WENG_PALETTE = [(0, 0, 0, 0), (255, 224, 48), (255, 240, 160), (208, 176, 32), (32, 32, 32)]
TUAN_PALETTE = [(0, 0, 0, 0), (240, 240, 240), (255, 255, 255), (208, 208, 208), (32, 32, 32)]
WANG_PALETTE = [(0, 0, 0, 0), (255, 107, 138), (255, 160, 184), (217, 74, 106), (255, 255, 255)]
MIGU_PALETTE = [(0, 0, 0, 0), (176, 144, 240), (208, 192, 255), (144, 112, 208), (255, 224, 48)]


def _draw_eyes(pixels: list[list[int]], cx: int, ey: int, eye_w: int = 2, eye_h: int = 2) -> None:
    """画豆豆眼 (2×2 黑块)。"""
    for dx in range(eye_w):
        for dy in range(eye_h):
            if 0 <= ey + dy < len(pixels) and 0 <= cx - 2 + dx < len(pixels[0]):
                pixels[ey + dy][cx - 2 + dx] = 4
            if 0 <= ey + dy < len(pixels) and 0 <= cx + 2 + dx < len(pixels[0]):
                pixels[ey + dy][cx + 2 + dx] = 4


def _draw_blush(pixels: list[list[int]], cx: int, by: int) -> None:
    """画腮红 (2×2 浅粉方块，位于眼下外侧)。"""
    blush_color = 2  # 亮面色代替腮红
    for dx in range(2):
        for dy in range(2):
            if 0 <= by + dy < len(pixels):
                if 0 <= cx - 4 + dx < len(pixels[0]):
                    pixels[by + dy][cx - 4 + dx] = blush_color
                if 0 <= cx + 2 + dx < len(pixels[0]):
                    pixels[by + dy][cx + 2 + dx] = blush_color


def _fill_rect(pixels: list[list[int]], x: int, y: int, w: int, h: int, color: int) -> None:
    """填充矩形区域。"""
    H = len(pixels)
    W = len(pixels[0])
    for dy in range(h):
        for dx in range(w):
            py, px = y + dy, x + dx
            if 0 <= py < H and 0 <= px < W:
                pixels[py][px] = color


def _make_frame(size: int) -> list[list[int]]:
    """创建全透明画布。"""
    return [[0 for _ in range(size)] for _ in range(size)]


# ══════════════════════════════════════════════════════
# 兜兜(熊) 32×32 — 胖圆身体 + 短耳 + 肚皮 + 豆豆眼
# ══════════════════════════════════════════════════════

def _draw_dudu_body(pixels: list[list[int]], offset_y: int = 0) -> None:
    """兜兜身体主体。"""
    S = len(pixels)
    # 耳朵
    _fill_rect(pixels, 7, 0 + offset_y, 6, 5, 1)
    _fill_rect(pixels, 19, 0 + offset_y, 6, 5, 1)
    _fill_rect(pixels, 8, 1 + offset_y, 4, 4, 2)
    _fill_rect(pixels, 20, 1 + offset_y, 4, 4, 2)
    # 头部
    _fill_rect(pixels, 6, 5 + offset_y, 20, 14, 1)
    _fill_rect(pixels, 8, 7 + offset_y, 16, 10, 2)
    # 身体
    _fill_rect(pixels, 8, 19 + offset_y, 16, 10, 1)
    # 肚皮
    _fill_rect(pixels, 10, 21 + offset_y, 12, 7, 2)
    # 脚
    _fill_rect(pixels, 9, 29 + offset_y, 6, 3, 3)
    _fill_rect(pixels, 17, 29 + offset_y, 6, 3, 3)
    # 豆豆眼
    _draw_eyes(pixels, 16, 10 + offset_y)
    # 鼻子
    _fill_rect(pixels, 15, 13 + offset_y, 2, 2, 3)
    # 嘴
    pixels[16 + offset_y][15] = 4
    pixels[16 + offset_y][16] = 4


def generate_dudu() -> Image.Image:
    """兜兜 sprite sheet: 4帧 (待机/跳1/跳2/✌️) × 32×32 = 128×32"""
    frames = []
    for fi in range(4):
        p = _make_frame(32)
        if fi == 0:  # 待机
            _draw_dudu_body(p)
        elif fi == 1:  # 跳1 — 整体上移
            _draw_dudu_body(p, offset_y=-3)
        elif fi == 2:  # 跳2 — 再上移+手臂张开
            _draw_dudu_body(p, offset_y=-5)
            _fill_rect(p, 3, 15, 5, 3, 1)  # 左手
            _fill_rect(p, 24, 15, 5, 3, 1)  # 右手
        elif fi == 3:  # ✌️ — 举手
            _draw_dudu_body(p)
            _fill_rect(p, 5, 5, 3, 10, 1)  # 左手举起
            _fill_rect(p, 24, 5, 3, 10, 1)  # 右手举起
            # 手指 (V sign)
            p[2][6] = 1
            p[2][10] = 1
            p[2][25] = 1
            p[2][27] = 1
        frames.append(p)
    return _stitch_frames(frames, 32, DUDU_PALETTE)


# ══════════════════════════════════════════════════════
# 嗡嗡(蜜蜂) 16×16 — 椭圆条纹身体 + 翅膀 + 触角
# ══════════════════════════════════════════════════════

def _draw_weng_body(pixels: list[list[int]]) -> None:
    S = 16
    # 触角
    pixels[2][7] = 4
    pixels[1][6] = 4
    pixels[2][8] = 4
    pixels[1][9] = 4
    # 头部
    _fill_rect(pixels, 6, 3, 4, 3, 1)
    _fill_rect(pixels, 7, 3, 2, 2, 2)
    # 身体 (条纹)
    _fill_rect(pixels, 5, 6, 6, 7, 1)
    _fill_rect(pixels, 5, 8, 6, 2, 4)  # 黑条纹1
    _fill_rect(pixels, 5, 11, 6, 2, 4)  # 黑条纹2
    # 翅膀
    _fill_rect(pixels, 2, 6, 3, 4, 2)
    _fill_rect(pixels, 11, 6, 3, 4, 2)
    # 眼睛
    _draw_eyes(pixels, 8, 4, eye_w=1, eye_h=1)
    # 微笑
    pixels[6][8] = 4


def generate_wengweng() -> Image.Image:
    """嗡嗡 sprite sheet: 4帧 (待机/飞1/飞2/打气) × 16×16 = 64×16"""
    frames = []
    for fi in range(4):
        p = _make_frame(16)
        _draw_weng_body(p)
        if fi == 1:  # 飞1 — 翅膀抬起
            _fill_rect(p, 2, 4, 3, 2, 2)
            _fill_rect(p, 11, 4, 3, 2, 2)
        elif fi == 2:  # 飞2 — 翅膀更高
            _fill_rect(p, 2, 3, 3, 2, 2)
            _fill_rect(p, 11, 3, 3, 2, 2)
        elif fi == 3:  # 打气 — 翅膀张开+腮红
            _fill_rect(p, 1, 5, 4, 4, 2)
            _fill_rect(p, 11, 5, 4, 4, 2)
            _draw_blush(p, 8, 5)
        frames.append(p)
    return _stitch_frames(frames, 16, WENG_PALETTE)


# ══════════════════════════════════════════════════════
# 团团(熊猫) 32×32 — 胖大白身体 + 黑眼圈 + 黑四肢
# ══════════════════════════════════════════════════════

def _draw_tuan_body(pixels: list[list[int]], offset_y: int = 0) -> None:
    S = 32
    # 耳朵
    _fill_rect(pixels, 6, 0 + offset_y, 6, 5, 4)
    _fill_rect(pixels, 20, 0 + offset_y, 6, 5, 4)
    # 头部
    _fill_rect(pixels, 7, 5 + offset_y, 18, 15, 1)
    _fill_rect(pixels, 9, 7 + offset_y, 14, 11, 2)
    # 黑眼圈
    _fill_rect(pixels, 10, 8 + offset_y, 5, 4, 4)
    _fill_rect(pixels, 17, 8 + offset_y, 5, 4, 4)
    # 眼睛白点
    _fill_rect(pixels, 12, 9 + offset_y, 2, 2, 2)
    _fill_rect(pixels, 19, 9 + offset_y, 2, 2, 2)
    # 鼻子
    _fill_rect(pixels, 15, 13 + offset_y, 2, 2, 4)
    # 身体
    _fill_rect(pixels, 7, 20 + offset_y, 18, 10, 1)
    _fill_rect(pixels, 9, 21 + offset_y, 14, 7, 2)
    # 手臂
    _fill_rect(pixels, 5, 21 + offset_y, 4, 6, 4)
    _fill_rect(pixels, 23, 21 + offset_y, 4, 6, 4)
    # 脚
    _fill_rect(pixels, 8, 29 + offset_y, 6, 3, 4)
    _fill_rect(pixels, 18, 29 + offset_y, 6, 3, 4)


def generate_tuantuan() -> Image.Image:
    """团团 sprite sheet: 4帧 (待机/冒出/抱星/转圈) × 32×32 = 128×32"""
    frames = []
    star_colors = [0, (255, 224, 48), (255, 240, 160)]  # 星星用黄色系

    for fi in range(4):
        p = _make_frame(32)
        if fi == 0:  # 待机
            _draw_tuan_body(p)
        elif fi == 1:  # 冒出 — 从底部冒出
            _draw_tuan_body(p, offset_y=-8)
        elif fi == 2:  # 抱星 — 手中间有星星
            _draw_tuan_body(p)
            # 星星在身体中间 (简化: 小方块)
            for sx in range(6):
                for sy in range(6):
                    if (sx + sy) % 2 == 0:  # 棋盘格模拟星星
                        px = 13 + sx
                        py = 18 + sy
                        if 0 <= py < 32 and 0 <= px < 32:
                            p[py][px] = 5  # 特殊色
        elif fi == 3:  # 转圈 — 身体微转 (偏移)
            _draw_tuan_body(p, offset_y=0)
            # 手臂位置变化表示转动
            _fill_rect(p, 3, 23, 4, 4, 4)
            _fill_rect(p, 25, 20, 4, 4, 4)

        frames.append(p)
    return _stitch_frames(frames, 32, TUAN_PALETTE)


# ══════════════════════════════════════════════════════
# 旺仔(小狗) 32×32 — 垂耳 + 长嘴 + 尾巴 + 白肚皮
# ══════════════════════════════════════════════════════

def _draw_wang_body(pixels: list[list[int]]) -> None:
    S = 32
    # 耳朵 (垂耳)
    _fill_rect(pixels, 5, 2, 5, 8, 1)
    _fill_rect(pixels, 22, 2, 5, 8, 1)
    _fill_rect(pixels, 5, 1, 4, 1, 2)
    _fill_rect(pixels, 23, 1, 4, 1, 2)
    # 头部
    _fill_rect(pixels, 8, 5, 16, 12, 1)
    _fill_rect(pixels, 10, 7, 12, 8, 2)
    # 眼睛 (豆豆眼)
    _draw_eyes(pixels, 16, 8)
    # 鼻子
    _fill_rect(pixels, 15, 11, 2, 2, 4)
    # 嘴
    _fill_rect(pixels, 14, 14, 4, 1, 3)
    # 身体
    _fill_rect(pixels, 8, 17, 16, 10, 1)
    # 白肚皮
    _fill_rect(pixels, 10, 19, 12, 7, 4)
    # 腿
    _fill_rect(pixels, 9, 27, 5, 5, 1)
    _fill_rect(pixels, 18, 27, 5, 5, 1)
    # 尾巴
    _fill_rect(pixels, 24, 18, 3, 3, 1)
    _fill_rect(pixels, 25, 15, 2, 3, 2)


def generate_wangzai() -> Image.Image:
    """旺仔 sprite sheet: 4帧 (待机/摇尾1/摇尾2/撒花) × 32×32 = 128×32"""
    frames = []
    for fi in range(4):
        p = _make_frame(32)
        _draw_wang_body(p)
        if fi == 1:  # 摇尾1 — 尾巴偏移
            _fill_rect(p, 24, 18, 3, 3, 2)
            _fill_rect(p, 26, 16, 2, 3, 1)
        elif fi == 2:  # 摇尾2 — 尾巴更偏
            _fill_rect(p, 24, 20, 3, 3, 2)
            _fill_rect(p, 27, 18, 2, 3, 1)
        elif fi == 3:  # 撒花 — 周围有彩色小方块
            for (px, py) in [(2, 10), (28, 8), (4, 22), (27, 24), (15, 0)]:
                if 0 <= py < 32 and 0 <= px < 32:
                    p[py][px] = 2
        frames.append(p)
    return _stitch_frames(frames, 32, WANG_PALETTE)


# ══════════════════════════════════════════════════════
# 咪咕(小猫) 16×16 — 尖耳 + 长尾 + 黄眼睛
# ══════════════════════════════════════════════════════

def _draw_migu_body(pixels: list[list[int]]) -> None:
    S = 16
    # 耳朵 (三角形)
    _fill_rect(pixels, 5, 0, 3, 2, 1)
    _fill_rect(pixels, 8, 0, 3, 2, 1)
    _fill_rect(pixels, 5, 0, 1, 2, 2)
    _fill_rect(pixels, 10, 0, 1, 2, 2)
    # 头部
    _fill_rect(pixels, 4, 2, 8, 7, 1)
    _fill_rect(pixels, 5, 3, 6, 5, 2)
    # 黄眼睛
    _fill_rect(pixels, 5, 4, 2, 2, 4)
    _fill_rect(pixels, 9, 4, 2, 2, 4)
    # 瞳孔
    pixels[5][5] = 3
    pixels[9][5] = 3
    # 鼻子
    _fill_rect(pixels, 7, 7, 2, 1, 3)
    # 身体
    _fill_rect(pixels, 4, 9, 8, 5, 1)
    _fill_rect(pixels, 5, 10, 6, 3, 2)
    # 尾巴
    _fill_rect(pixels, 12, 9, 2, 3, 1)
    _fill_rect(pixels, 13, 11, 2, 2, 2)
    # 脚
    _fill_rect(pixels, 5, 14, 2, 2, 3)
    _fill_rect(pixels, 9, 14, 2, 2, 3)


def generate_migu() -> Image.Image:
    """咪咕 sprite sheet: 4帧 (待机/歪头/眨眼/灵感) × 16×16 = 64×16"""
    frames = []
    for fi in range(4):
        p = _make_frame(16)
        if fi == 0:  # 待机
            _draw_migu_body(p)
        elif fi == 1:  # 歪头 — 身体偏移
            _draw_migu_body(p)
            # 头歪一点 (移动头部像素)
            for y in range(0, 9):
                for x in range(3, 13):
                    if p[y][x] == 1:
                        p[y][x - 1] = 1
                        p[y][x] = 0
        elif fi == 2:  # 眨眼 — 眼睛变细线
            _draw_migu_body(p)
            p[5][5] = 0
            p[5][6] = 0
            p[5][9] = 0
            p[5][10] = 0
            p[4][5] = 4  # 细线眼
            p[4][6] = 4
            p[4][9] = 4
            p[4][10] = 4
        elif fi == 3:  # 灵感 — 头顶灯泡
            _draw_migu_body(p)
            _fill_rect(p, 7, 0, 2, 1, 4)  # 黄灯泡
            p[0][8] = 2
        frames.append(p)
    return _stitch_frames(frames, 16, MIGU_PALETTE)


# ══════════════════════════════════════════════════════
# 工具函数
# ══════════════════════════════════════════════════════

def _stitch_frames(frames: list[list[list[int]]], size: int, palette: list[tuple[int, ...]]) -> Image.Image:
    """将帧列表拼接为横向 sprite sheet。"""
    num_frames = len(frames)
    sheet = Image.new("RGBA", (size * num_frames, size), (0, 0, 0, 0))
    pixels = sheet.load()

    for fi, frame in enumerate(frames):
        for y in range(size):
            for x in range(size):
                color_idx = frame[y][x]
                if color_idx < len(palette):
                    pixels[x + fi * size, y] = palette[color_idx]

    return sheet


def main() -> int:
    SPRITES_DIR.mkdir(parents=True, exist_ok=True)

    generators = {
        "dudu_32x32.png": generate_dudu,
        "wengweng_16x16.png": generate_wengweng,
        "tuantuan_32x32.png": generate_tuantuan,
        "wangzai_32x32.png": generate_wangzai,
        "migu_16x16.png": generate_migu,
    }

    for filename, gen_func in generators.items():
        path = SPRITES_DIR / filename
        img = gen_func()
        img.save(str(path))
        print(f"  Generated {filename} ({img.width}×{img.height})")

    print(f"\nAll {len(generators)} sprite sheets generated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
