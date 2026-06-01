"""测试历史页面 UI 组件 — DayCard / CalendarCell / MonthCard / HistoryScreen"""

from __future__ import annotations

from app.models.history import (
    CalendarCell as CalendarCellModel,
)
from app.models.history import (
    DayCard as DayCardModel,
)
from app.models.history import (
    MonthSummary,
    MonthViewData,
    PeriodSummary,
    WeekViewData,
    YearViewData,
)
from app.models.ledger import LedgerEntry
from app.ui.components.calendar_cell import CalendarCell
from app.ui.components.day_card import DayCard
from app.ui.components.history_tabs import HistoryTabs
from app.ui.components.month_card import MonthCard
from app.ui.screens.history_screen import HistoryScreen

# ================================================================
# Mock HistoryService
# ================================================================

class MockHistoryService:
    """模拟 HistoryService，返回固定数据。"""

    def __init__(self) -> None:
        self.get_week_view_calls: list[str] = []
        self.get_month_view_calls: list[tuple[int, int]] = []
        self.get_year_view_calls: list[int] = []

    def get_week_view(self, week_start: str) -> WeekViewData:
        self.get_week_view_calls.append(week_start)
        return WeekViewData(
            week_start=week_start,
            week_end="2026-06-07",
            days=[
                DayCardModel(
                    date="2026-06-01",
                    periods=[
                        PeriodSummary(period="morning", status="normal", checkin_time="08:00", checkout_time="12:00"),
                        PeriodSummary(period="afternoon", status="normal", checkin_time="13:00", checkout_time="18:00"),
                    ],
                    total_hours=9.0,
                    daily_ledger=[LedgerEntry(entry_date="2026-06-01", type="reward", amount=50.0)],
                    is_shooting=False,
                ),
                DayCardModel(
                    date="2026-06-02",
                    periods=[
                        PeriodSummary(period="morning", status="late", checkin_time="09:30", checkout_time="12:00"),
                        PeriodSummary(period="afternoon", status="normal", checkin_time="13:00", checkout_time="18:00"),
                    ],
                    total_hours=7.5,
                    daily_ledger=[LedgerEntry(entry_date="2026-06-02", type="penalty", amount=-20.0)],
                    is_shooting=True,
                ),
                DayCardModel(
                    date="2026-06-03",
                    periods=[
                        PeriodSummary(period="morning", status="leave", checkin_time=None, checkout_time=None),
                        PeriodSummary(period="afternoon", status="leave", checkin_time=None, checkout_time=None),
                    ],
                    total_hours=0.0,
                    daily_ledger=[],
                    is_shooting=False,
                ),
            ],
            weekly_net=30.0,
        )

    def get_month_view(self, year: int, month: int) -> MonthViewData:
        self.get_month_view_calls.append((year, month))
        return MonthViewData(
            year=year,
            month=month,
            cells=[
                CalendarCellModel(date=f"{year}-{month:02d}-{d:02d}", color=c, has_data=True)
                for d, c in [
                    (1, "green"), (2, "green"), (3, "yellow"), (4, "green"),
                    (5, "red"), (6, "blue"), (7, "orange"),
                ]
            ],
            weekly_summaries=[
                {"week_start": f"{year}-{month:02d}-01", "net": 150.0},
            ],
        )

    def get_year_view(self, year: int) -> YearViewData:
        self.get_year_view_calls.append(year)
        return YearViewData(
            year=year,
            months=[
                MonthSummary(
                    month=m,
                    work_days=20,
                    late_count=2,
                    absent_count=1,
                    total_hours=160.0,
                    total_ledger=200.0,
                )
                for m in range(1, 13)
            ],
        )


# ================================================================
# Test DayCard
# ================================================================


class TestDayCard:
    """DayCard 组件测试"""

    def test_create_normal_day(self) -> None:
        """正常日渲染。"""
        day = DayCardModel(
            date="2026-06-01",
            periods=[
                PeriodSummary(period="morning", status="normal"),
                PeriodSummary(period="afternoon", status="normal"),
            ],
            total_hours=9.0,
            daily_ledger=[LedgerEntry(entry_date="2026-06-01", type="reward", amount=50.0)],
            is_shooting=False,
        )
        card = DayCard(day_summary=day)
        assert card._day is day
        assert card._date_label.text == "6月1日 周一"
        assert "上午: 正常" in card._status_label.text
        assert "下午: 正常" in card._status_label.text
        assert "9.0h" in card._hours_label.text
        assert "+50" in card._hours_label.text

    def test_create_late_day(self) -> None:
        """迟到日渲染。"""
        day = DayCardModel(
            date="2026-06-02",
            periods=[
                PeriodSummary(period="morning", status="late"),
                PeriodSummary(period="afternoon", status="normal"),
            ],
            total_hours=7.5,
            daily_ledger=[LedgerEntry(entry_date="2026-06-02", type="penalty", amount=-20.0)],
            is_shooting=False,
        )
        card = DayCard(day_summary=day)
        assert "上午: 迟到" in card._status_label.text
        assert "下午: 正常" in card._status_label.text
        assert "-20" in card._hours_label.text

    def test_create_shooting_day(self) -> None:
        """拍摄日渲染（橙色背景）。"""
        day = DayCardModel(
            date="2026-06-03",
            periods=[
                PeriodSummary(period="morning", status="normal"),
            ],
            total_hours=8.0,
            daily_ledger=[],
            is_shooting=True,
        )
        card = DayCard(day_summary=day)
        assert card._day.is_shooting

    def test_create_leave_day(self) -> None:
        """请假日渲染。"""
        day = DayCardModel(
            date="2026-06-04",
            periods=[
                PeriodSummary(period="morning", status="leave"),
                PeriodSummary(period="afternoon", status="leave"),
            ],
            total_hours=0.0,
            daily_ledger=[],
            is_shooting=False,
        )
        card = DayCard(day_summary=day)
        assert "上午: 请假" in card._status_label.text
        assert "下午: 请假" in card._status_label.text

    def test_day_card_click_callback(self) -> None:
        """点击回调触发。"""
        clicked: list[DayCardModel] = []
        day = DayCardModel(
            date="2026-06-01",
            periods=[],
            total_hours=0.0,
            daily_ledger=[],
            is_shooting=False,
        )
        card = DayCard(day_summary=day, on_click=lambda d: clicked.append(d))

        # 设置位置与尺寸，使得 (5, 5) 被包含
        card.size = (300, 80)
        card.pos = (0, 0)
        card.on_touch_down(type("Touch", (), {"pos": (5, 5)})())
        assert clicked == [day]

    def test_day_card_click_without_callback(self) -> None:
        """无回调时点击不报错。"""
        day = DayCardModel(
            date="2026-06-01",
            periods=[],
            total_hours=0.0,
            daily_ledger=[],
            is_shooting=False,
        )
        card = DayCard(day_summary=day)  # no on_click
        assert card._on_click is None
        # 模拟触控不应抛异常
        card.size = (300, 80)
        card.pos = (0, 0)
        card.on_touch_down(type("Touch", (), {"pos": (5, 5)})())


# ================================================================
# Test CalendarCell
# ================================================================


class TestCalendarCell:
    """CalendarCell 组件测试"""

    def test_create_normal_cell(self) -> None:
        """正常日状态（绿色）。"""
        cell = CalendarCell(day=1, status="normal", is_work_day=True)
        assert cell._day == 1
        assert cell._status == "normal"
        assert cell._label.text == "1"

    def test_create_late_cell(self) -> None:
        """迟到状态（黄色）。"""
        cell = CalendarCell(day=15, status="late", is_work_day=True)
        assert cell._status == "late"

    def test_create_absent_cell(self) -> None:
        """旷工状态（红色）。"""
        cell = CalendarCell(day=20, status="absent", is_work_day=True)
        assert cell._status == "absent"

    def test_create_leave_cell(self) -> None:
        """请假状态（蓝色）。"""
        cell = CalendarCell(day=10, status="leave", is_work_day=True)
        assert cell._status == "leave"

    def test_create_shooting_cell(self) -> None:
        """拍摄日状态（橙色）。"""
        cell = CalendarCell(day=7, status="shooting", is_work_day=True)
        assert cell._status == "shooting"

    def test_create_rest_cell(self) -> None:
        """非工作日显示团团图标。"""
        cell = CalendarCell(day=8, status="rest", is_work_day=False)
        assert not cell._is_work_day
        # 非工作日的 label 应显示 🐼
        assert cell._label.text == "🐼"

    def test_create_future_cell(self) -> None:
        """未来日期显示 ○。"""
        cell = CalendarCell(day=30, status="future", is_work_day=True)
        assert cell._label.text == "○"

    def test_cell_size(self) -> None:
        """格子尺寸固定。"""
        cell = CalendarCell(day=1, status="normal", is_work_day=True)
        assert cell.width == 36 and cell.height == 36


# ================================================================
# Test MonthCard
# ================================================================


class TestMonthCard:
    """MonthCard 组件测试"""

    def test_create_month_card(self) -> None:
        """月度汇总卡片渲染。"""
        ms = MonthSummary(
            month=6,
            work_days=22,
            late_count=3,
            absent_count=1,
            total_hours=176.0,
            total_ledger=320.0,
        )
        card = MonthCard(month_summary=ms)
        assert "6月" in card._title_label.text
        assert "22" in card._stats_label.text
        assert "3" in card._stats_label.text
        assert "1" in card._stats_label.text
        assert "176.0" in card._bottom_label.text
        assert "+320" in card._bottom_label.text or "320" in card._bottom_label.text


# ================================================================
# Test HistoryTabs
# ================================================================


class TestHistoryTabs:
    """HistoryTabs 组件测试"""

    def test_create_tabs(self) -> None:
        """创建三 Tab。"""
        tabs = HistoryTabs()
        assert len(tabs._tab_buttons) == 3
        assert tabs._tab_buttons[0].text == "周"
        assert tabs._tab_buttons[1].text == "月"
        assert tabs._tab_buttons[2].text == "年"

    def test_active_tab_default(self) -> None:
        """默认选中第一个 Tab。"""
        tabs = HistoryTabs()
        assert tabs.active_tab == 0

    def test_tab_change_callback(self) -> None:
        """Tab 切换时触发回调。"""
        changed: list[int] = []
        tabs = HistoryTabs(on_tab_change=lambda idx: changed.append(idx))
        tabs._select_tab(1)
        assert tabs.active_tab == 1
        assert changed == [1]

    def test_select_same_tab_does_nothing(self) -> None:
        """重复选中同一 Tab 不触发回调。"""
        changed: list[int] = []
        tabs = HistoryTabs(on_tab_change=lambda idx: changed.append(idx))
        tabs._select_tab(0)  # 已经是 0
        assert changed == []

    def test_tab_switching_sequence(self) -> None:
        """依次切换三个 Tab。"""
        changed: list[int] = []
        tabs = HistoryTabs(on_tab_change=lambda idx: changed.append(idx))
        tabs._select_tab(1)
        tabs._select_tab(2)
        tabs._select_tab(0)
        assert changed == [1, 2, 0]


# ================================================================
# Test HistoryScreen
# ================================================================


class TestHistoryScreen:
    """HistoryScreen 集成测试"""

    def test_create_screen(self) -> None:
        """创建页面不报错。"""
        service = MockHistoryService()
        screen = HistoryScreen(history_service=service)  # type: ignore[arg-type]
        assert screen._service is service  # type: ignore[comparison-overlap]
        assert screen._tab_index == 0  # type: ignore[unreachable]

    def test_default_tab_is_week(self) -> None:
        """默认打开周视图。"""
        screen = HistoryScreen(history_service=MockHistoryService())  # type: ignore[arg-type]
        assert screen.tabs.active_tab == 0
        assert screen._week_view.opacity == 1.0
        assert screen._month_view.opacity == 0.0
        assert screen._year_view.opacity == 0.0

    def test_tab_switch_to_month(self) -> None:
        """切换到月视图。"""
        screen = HistoryScreen(history_service=MockHistoryService())  # type: ignore[arg-type]
        screen._switch_tab(1)
        assert screen._tab_index == 1
        assert screen._week_view.opacity == 0.0
        assert screen._month_view.opacity == 1.0
        assert screen._year_view.opacity == 0.0

    def test_tab_switch_to_year(self) -> None:
        """切换到年视图。"""
        screen = HistoryScreen(history_service=MockHistoryService())  # type: ignore[arg-type]
        screen._switch_tab(2)
        assert screen._tab_index == 2
        assert screen._week_view.opacity == 0.0
        assert screen._month_view.opacity == 0.0
        assert screen._year_view.opacity == 1.0

    def test_week_view_renders_day_cards(self) -> None:
        """周视图渲染 DayCard 列表。"""
        screen = HistoryScreen(history_service=MockHistoryService())  # type: ignore[arg-type]
        assert len(screen._week_card_container.children) == 3

    def test_week_navigation_calls_service(self) -> None:
        """周箭头切换调用服务。"""
        service = MockHistoryService()
        screen = HistoryScreen(history_service=service)  # type: ignore[arg-type]
        initial_calls = len(service.get_week_view_calls)
        screen._navigate_week(1)
        assert len(service.get_week_view_calls) == initial_calls + 1

    def test_month_navigation_calls_service(self) -> None:
        """月箭头切换调用服务。"""
        service = MockHistoryService()
        screen = HistoryScreen(history_service=service)  # type: ignore[arg-type]
        # 先切到月视图
        screen._switch_tab(1)
        initial_calls = len(service.get_month_view_calls)
        screen._navigate_month(1)
        assert len(service.get_month_view_calls) == initial_calls + 1

    def test_year_navigation_calls_service(self) -> None:
        """年箭头切换调用服务。"""
        service = MockHistoryService()
        screen = HistoryScreen(history_service=service)  # type: ignore[arg-type]
        screen._switch_tab(2)
        initial_calls = len(service.get_year_view_calls)
        screen._navigate_year(1)
        assert len(service.get_year_view_calls) == initial_calls + 1

    def test_week_total_label(self) -> None:
        """周视图底部合计显示。"""
        screen = HistoryScreen(history_service=MockHistoryService())  # type: ignore[arg-type]
        assert "30.0" in screen._week_total_label.text or "+30" in screen._week_total_label.text

    def test_year_view_renders_month_cards(self) -> None:
        """年视图渲染 12 张 MonthCard。"""
        screen = HistoryScreen(history_service=MockHistoryService())  # type: ignore[arg-type]
        screen._switch_tab(2)
        assert len(screen._year_card_container.children) == 12

    def test_month_view_renders_calendar(self) -> None:
        """月视图渲染日历格子。"""
        screen = HistoryScreen(history_service=MockHistoryService())  # type: ignore[arg-type]
        screen._switch_tab(1)
        # 日历区域应有 widgets (header + weeks + summaries)
        assert len(screen._month_calendar.children) > 0
