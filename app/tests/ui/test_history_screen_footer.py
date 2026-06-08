"""历史页底部留白测试 — 确保滚到底"本周合计"不被 navtab 遮挡。"""

from __future__ import annotations

from unittest.mock import MagicMock

from app.models.history import DayCard as DayCardModel, WeekViewData
from app.ui.screens.history_screen import HistoryScreen
from app.ui.tokens import NAV_HEIGHT


def _make_service() -> MagicMock:
    svc = MagicMock()
    svc.get_week_view.return_value = WeekViewData(
        week_start="2026-06-01",
        week_end="2026-06-07",
        days=[],
        weekly_net=-200.0,
    )
    svc.get_month_view.return_value = MagicMock(cells=[], weekly_summaries=[])
    svc.get_year_view.return_value = MagicMock(months=[])
    return svc


def test_week_card_container_reserves_bottom_padding_for_navtab() -> None:
    """周视图 ScrollView 的内容容器底部 padding 应 >= NAV_HEIGHT，
    保证滚到最底部时"本周合计"不被 navtab 遮挡。"""
    screen = HistoryScreen(history_service=_make_service())  # type: ignore[arg-type]

    container = screen._week_card_container
    assert hasattr(container, "padding"), "期望 _week_card_container 有 padding 属性"

    padding = container.padding
    # Kivy BoxLayout.padding 可以是 [left,top,right,bottom] 或 [h,v] 或单值
    if isinstance(padding, (list, tuple)) and len(padding) == 4:
        bottom = padding[3]
    elif isinstance(padding, (list, tuple)) and len(padding) == 2:
        bottom = padding[1]
    elif isinstance(padding, (int, float)):
        bottom = padding
    else:
        bottom = 0

    assert bottom >= NAV_HEIGHT, (
        f"_week_card_container.padding bottom={bottom} < NAV_HEIGHT={NAV_HEIGHT}，"
        "本周合计会被 navtab 遮挡。请给 container 添加足够的 bottom padding。"
    )


def test_week_total_label_inside_scroll_container() -> None:
    """本周合计 label 应位于 ScrollView 的可滚动容器内，
    而不是悬浮在 ScrollView 外部（否则会被 navtab 固定遮挡）。"""
    screen = HistoryScreen(history_service=_make_service())  # type: ignore[arg-type]

    # _week_total_label 应是 _week_card_container 的子控件
    container_children = screen._week_card_container.children
    assert screen._week_total_label in container_children, (
        "_week_total_label 不在 _week_card_container 中——"
        "它被固定在 ScrollView 外部，navtab 会把它遮挡。"
        "请将 footer label 移入 _week_card_container。"
    )
