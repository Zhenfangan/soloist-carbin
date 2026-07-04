"""StatusStatCard — 月历"各状态统计"卡: 玻璃框 + 图例(色块+文字合一) +
像素点 bar(按天数) + 计数, 一个状态一张卡。"""
from __future__ import annotations

from app.ui.components.calendar_cell import CALENDAR_COLORS, CALENDAR_STATUS_LABELS
from app.ui.components.status_stat_card import StatusStatCard


def test_shows_status_label() -> None:
    card = StatusStatCard(status="late", count=3)
    assert card._label.text == CALENDAR_STATUS_LABELS["late"]


def test_shows_count_text() -> None:
    card = StatusStatCard(status="normal", count=20)
    assert "20" in card._count_label.text


def test_dot_color_matches_status() -> None:
    card = StatusStatCard(status="absent", count=2)
    assert card._dot_color() == CALENDAR_COLORS["absent"]


def test_dot_count_matches_count() -> None:
    card = StatusStatCard(status="shooting", count=5)
    assert card._count == 5
