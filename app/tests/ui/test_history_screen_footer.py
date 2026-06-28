"""历史页底部留白测试 — 确保滚到底内容不被 navtab 遮挡。"""

from __future__ import annotations

from unittest.mock import MagicMock

from app.models.history import DayCard as DayCardModel, WeekViewData
from app.ui.screens.history_screen import HistoryScreen
from app.ui.tokens import NAV_HEIGHT


def _make_service() -> MagicMock:
    svc = MagicMock()
    svc.get_cycle_history.return_value = []  # 空周期列表
    svc.get_week_view.return_value = WeekViewData(
        week_start="2026-06-01",
        week_end="2026-06-07",
        days=[],
        weekly_net=-200.0,
    )
    svc.get_month_view.return_value = MagicMock(cells=[], weekly_summaries=[])
    svc.get_year_view.return_value = MagicMock(months=[])
    return svc


def test_cycle_container_reserves_bottom_padding_for_navtab() -> None:
    """周期视图 ScrollView 的内容容器底部 padding 应 >= NAV_HEIGHT，
    保证滚到最底部时周期条不被 navtab 遮挡。"""
    screen = HistoryScreen(history_service=_make_service())  # type: ignore[arg-type]

    container = screen._cycle_container
    assert hasattr(container, "padding"), "期望 _cycle_container 有 padding 属性"

    padding = container.padding
    if isinstance(padding, (list, tuple)) and len(padding) == 4:
        bottom = padding[3]
    elif isinstance(padding, (list, tuple)) and len(padding) == 2:
        bottom = padding[1]
    elif isinstance(padding, (int, float)):
        bottom = padding
    else:
        bottom = 0

    assert bottom >= NAV_HEIGHT, (
        f"_cycle_container.padding bottom={bottom} < NAV_HEIGHT={NAV_HEIGHT}，"
        "周期条会被 navtab 遮挡。请给 container 添加足够的 bottom padding。"
    )


def test_cycle_empty_label_inside_scroll_container() -> None:
    """空状态 label 应位于 ScrollView 的可滚动容器内。"""
    screen = HistoryScreen(history_service=_make_service())  # type: ignore[arg-type]

    container_children = screen._cycle_container.children
    assert screen._cycle_empty_label in container_children, (
        "_cycle_empty_label 不在 _cycle_container 中——"
        "它被固定在 ScrollView 外部，navtab 会把它遮挡。"
    )
