"""pixel_dot_bar.calc_dot_geom — 像素点 bar 几何计算(CycleBar/StatusStatCard 共用)。

从 CycleBar 抽取而来, 行为不变: 优先保持理想点宽/间距, 空间不够先缩间隙,
仍不够再缩点宽(设 6px 下限), 避免点数一多就溢出卡片。
"""
from __future__ import annotations

from app.ui.components.pixel_dot_bar import calc_dot_geom


def test_fits_without_shrinking_when_space_enough() -> None:
    w, h, gap = calc_dot_geom(bar_w=200, total=7)
    assert (w, gap) == (10, 3)


def test_shrinks_width_when_space_tight() -> None:
    """空间不够理想尺寸时, 点宽不超过理想值, 且不会缩到 0(仍可见)。"""
    w, h, gap = calc_dot_geom(bar_w=90, total=10)
    assert w <= 10
    assert w > 0
    assert gap >= 2


def test_width_has_floor_when_extremely_tight() -> None:
    w, h, gap = calc_dot_geom(bar_w=60, total=20)
    assert w < 10
    assert w >= 6  # 下限保护, 不会缩到不可见


def test_zero_total_does_not_crash() -> None:
    w, h, gap = calc_dot_geom(bar_w=100, total=0)
    assert w > 0 and h > 0
