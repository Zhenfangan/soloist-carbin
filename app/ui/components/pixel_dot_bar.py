"""像素点 bar 几何计算 —— CycleBar 与 StatusStatCard 共用。

按可用宽度和点数自适应: 优先保持理想点宽/间距, 空间不够时先缩间隙,
仍不够再缩点宽(设 6px 下限保证可见), 避免点数一多就溢出卡片。
"""

from __future__ import annotations

DOT_W = 10   # 理想点宽度
DOT_H = 14   # 理想点高度
DOT_GAP = 3  # 理想点间距


def calc_dot_geom(
    bar_w: float,
    total: int,
    ideal_w: float = DOT_W,
    ideal_h: float = DOT_H,
    ideal_gap: float = DOT_GAP,
) -> tuple[float, float, float]:
    """返回 (点宽, 点高, 间距)。"""
    if total <= 0:
        return ideal_w, ideal_h, ideal_gap

    needed = total * ideal_w + (total - 1) * ideal_gap
    if needed <= bar_w:
        return ideal_w, ideal_h, ideal_gap

    # 空间不够：优先缩间隙，再缩方块
    if total > 1:
        gap = max(2, (bar_w - total * ideal_w) / (total - 1))
        if gap >= 3:
            return ideal_w, ideal_h, gap
    else:
        gap = 2

    # 间隙缩到最小仍不够 → 缩方块宽度
    gap = max(2, (bar_w - total * 6) / (total - 1)) if total > 1 else 2
    dot_w = max(6, (bar_w - (total - 1) * gap) / total)
    return dot_w, ideal_h, gap
