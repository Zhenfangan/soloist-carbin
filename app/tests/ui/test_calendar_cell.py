"""CalendarCell 月视图格子 — 根因回归(Label 定位)+ 状态配色覆盖。"""
from __future__ import annotations

from app.ui.components.calendar_cell import CALENDAR_COLORS, CalendarCell


def test_date_label_centered_via_pos_hint() -> None:
    """真机反馈: 月历左下角有"重合黑块", 且格子里看不到日期数字。

    根因: CalendarCell 是 FloatLayout, 内部日期 Label 只设了 size_hint 却
    漏了 pos_hint —— FloatLayout 不会摆放没有 pos_hint 的子控件, 于是每个
    格子的数字 Label 都停在窗口原点 (0,0), 十几个叠成一坨深棕块。
    修复: Label 必须带 pos_hint 居中到格子内。
    """
    cell = CalendarCell(day=15, status="normal")
    assert cell._label.pos_hint.get("center_x") == 0.5
    assert cell._label.pos_hint.get("center_y") == 0.5


def test_calendar_colors_cover_all_statuses() -> None:
    """图例要覆盖 8 种当日状态类型。"""
    for st in ("normal", "late", "early_leave", "absent", "leave", "shooting", "rest", "future"):
        assert st in CALENDAR_COLORS, f"缺少状态配色: {st}"


def test_early_leave_distinct_from_late_and_shooting() -> None:
    """早退要有独立颜色, 不能和迟到或拍摄撞色。"""
    assert CALENDAR_COLORS["early_leave"] != CALENDAR_COLORS["late"]
    assert CALENDAR_COLORS["early_leave"] != CALENDAR_COLORS["shooting"]


def test_bg_color_resolves_by_status() -> None:
    cell = CalendarCell(day=3, status="early_leave")
    assert cell._get_bg_color() == CALENDAR_COLORS["early_leave"]
