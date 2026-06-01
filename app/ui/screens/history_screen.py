"""HistoryScreen — 主历史页面。

顶部 HistoryTabs + 三个视图容器: 周视图 / 月视图 / 年视图。
默认打开周视图，当前周。
"""

from __future__ import annotations

import calendar
from datetime import datetime, timedelta
from typing import Any, cast

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView

from app.models.history import CalendarCell as CalendarCellModel
from app.models.history import DayCard as DayCardModel
from app.models.history import MonthViewData, WeekViewData, YearViewData
from app.services.history_service import HistoryService
from app.ui.components.calendar_cell import CalendarCell
from app.ui.components.day_card import DayCard
from app.ui.components.history_tabs import HistoryTabs
from app.ui.components.month_card import MonthCard
from app.ui.components.pixel_button import PixelButton
from app.ui.tokens import (
    BTN_HEIGHT,
    FONT_SIZE_BODY,
    FONT_SIZE_SMALL,
    GRID_UNIT,
    TEXT_BROWN,
    TEXT_GRAY,
)
from app.utils.clock import get_clock

# 星期表头
WEEKDAY_HEADERS = ["一", "二", "三", "四", "五", "六", "日"]


class HistoryScreen(FloatLayout):  # type: ignore[misc]
    """主历史页面。

    属性:
        history_service: HistoryService 实例（构造函数注入）
    """

    def __init__(
        self,
        history_service: HistoryService,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)

        self._service: HistoryService = history_service

        # 当前导航偏移
        self._tab_index: int = 0  # 0=周, 1=月, 2=年
        self._week_offset: int = 0
        self._month_offset: int = 0
        self._year_offset: int = 0

        # 根布局
        root = BoxLayout(orientation="vertical", size_hint=(1, 1))
        self.add_widget(root)

        # --- 顶部 Tab ---
        self.tabs = HistoryTabs(on_tab_change=self._switch_tab)
        root.add_widget(self.tabs)

        # --- 内容区域（三个视图叠放，通过 opacity 控制显示） ---
        self.content = FloatLayout(size_hint=(1, 1))
        root.add_widget(self.content)

        # 周视图
        self._week_view = self._build_week_view()
        self.content.add_widget(self._week_view)

        # 月视图
        self._month_view = self._build_month_view()
        self.content.add_widget(self._month_view)

        # 年视图
        self._year_view = self._build_year_view()
        self.content.add_widget(self._year_view)

        # --- 初始加载：周视图，当前周 ---
        now = get_clock().now()
        self._current_week_start = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
        self._current_year = now.year
        self._current_month = now.month

        self._refresh_week_view()
        self._switch_tab(0)

    # ================================================================
    # 周视图
    # ================================================================

    def _build_week_view(self) -> BoxLayout:
        layout = BoxLayout(orientation="vertical", size_hint=(1, 1))

        # 导航栏
        nav = BoxLayout(
            orientation="horizontal",
            size_hint=(1, None),
            height=BTN_HEIGHT,
            padding=[GRID_UNIT, 0],
        )
        self._week_prev_btn = PixelButton(text="←", size_mode="small", on_press=lambda: self._navigate_week(-1))
        self._week_label = Label(
            text="",
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(1, 1),
            halign="center",
            valign="middle",
        )
        self._week_next_btn = PixelButton(text="→", size_mode="small", on_press=lambda: self._navigate_week(1))
        nav.add_widget(self._week_prev_btn)
        nav.add_widget(self._week_label)
        nav.add_widget(self._week_next_btn)
        layout.add_widget(nav)

        # DayCard 列表 (可滚动)
        self._week_scroll = ScrollView(size_hint=(1, 1))
        self._week_card_container = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=GRID_UNIT,
            padding=[GRID_UNIT, GRID_UNIT],
        )
        self._week_card_container.bind(
            minimum_height=self._week_card_container.setter("height")
        )
        self._week_scroll.add_widget(self._week_card_container)
        layout.add_widget(self._week_scroll)

        # 本周合计
        self._week_total_label = Label(
            text="",
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(1, None),
            height=BTN_HEIGHT,
            halign="center",
            valign="middle",
        )
        layout.add_widget(self._week_total_label)

        return layout

    def _navigate_week(self, direction: int) -> None:
        """切换周 (direction: -1 上一周, +1 下一周)。"""
        self._week_offset += direction
        self._refresh_week_view()

    def _refresh_week_view(self) -> None:
        """重新加载周视图数据并更新 UI。"""
        start_dt = datetime.strptime(self._current_week_start, "%Y-%m-%d")
        offset_dt = start_dt + timedelta(weeks=self._week_offset)
        week_start = offset_dt.strftime("%Y-%m-%d")
        week_end = (offset_dt + timedelta(days=6)).strftime("%Y-%m-%d")

        try:
            data: WeekViewData = self._service.get_week_view(week_start)
        except Exception:
            return

        # 更新标题
        self._week_label.text = f"{week_start} ~ {week_end}"

        # 重建卡片
        self._week_card_container.clear_widgets()
        for day in data.days:
            card = DayCard(day_summary=day, on_click=self._on_day_click)
            self._week_card_container.add_widget(card)

        # 更新合计
        net = data.weekly_net
        sign = "+" if net >= 0 else ""
        self._week_total_label.text = f"本周合计: {sign}{net}"

    # ================================================================
    # 月视图
    # ================================================================

    def _build_month_view(self) -> BoxLayout:
        layout = BoxLayout(orientation="vertical", size_hint=(1, 1))

        # 导航栏
        nav = BoxLayout(
            orientation="horizontal",
            size_hint=(1, None),
            height=BTN_HEIGHT,
            padding=[GRID_UNIT, 0],
        )
        self._month_prev_btn = PixelButton(
            text="←", size_mode="small", on_press=lambda: self._navigate_month(-1)
        )
        self._month_label = Label(
            text="",
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(1, 1),
            halign="center",
            valign="middle",
        )
        self._month_next_btn = PixelButton(
            text="→", size_mode="small", on_press=lambda: self._navigate_month(1)
        )
        nav.add_widget(self._month_prev_btn)
        nav.add_widget(self._month_label)
        nav.add_widget(self._month_next_btn)
        layout.add_widget(nav)

        # 日历区域
        self._month_calendar = BoxLayout(
            orientation="vertical",
            size_hint=(1, None),
            spacing=2,
            padding=[GRID_UNIT, GRID_UNIT],
        )
        self._month_calendar.bind(
            minimum_height=self._month_calendar.setter("height")
        )
        month_scroll = ScrollView(size_hint=(1, 1))
        month_scroll.add_widget(self._month_calendar)
        layout.add_widget(month_scroll)

        return layout

    def _navigate_month(self, direction: int) -> None:
        """切换月 (direction: -1 上一月, +1 下一月)。"""
        self._month_offset += direction
        self._refresh_month_view()

    def _refresh_month_view(self) -> None:
        """重新加载月视图数据并更新 UI。"""
        # 计算目标年月
        total_months = self._current_month + self._month_offset - 1
        year = self._current_year + total_months // 12
        month = total_months % 12 + 1

        try:
            data: MonthViewData = self._service.get_month_view(year, month)
        except Exception:
            return

        # 更新标题
        self._month_label.text = f"{year}年 {month}月"

        # 重建日历
        self._month_calendar.clear_widgets()

        # 表头: 周一~周日
        header = BoxLayout(orientation="horizontal", size_hint=(1, None), height=24)
        for wd_name in WEEKDAY_HEADERS:
            lbl = Label(
                text=wd_name,
                font_size=FONT_SIZE_SMALL,
                color=self._to_rgba(TEXT_GRAY),
                size_hint=(1, 1),
                halign="center",
                valign="middle",
            )
            header.add_widget(lbl)
        self._month_calendar.add_widget(header)

        # 构建日历格子
        cells_by_day: dict[int, CalendarCellModel] = {}
        for cell in data.cells:
            try:
                day_num = int(cell.date.split("-")[2])
                cells_by_day[day_num] = cell
            except (IndexError, ValueError):
                continue

        cal_weeks = calendar.monthcalendar(year, month)
        for week in cal_weeks:
            row = BoxLayout(orientation="horizontal", size_hint=(1, None), height=36)
            for day_num in week:
                if day_num == 0:
                    # 空白占位
                    placeholder = BoxLayout(size_hint=(1, 1))
                    row.add_widget(placeholder)
                else:
                    cell_model = cells_by_day.get(day_num)
                    if cell_model and cell_model.has_data:
                        status = self._model_color_to_status(cell_model.color)
                        cell_widget = CalendarCell(
                            day=day_num,
                            status=status,
                            is_work_day=True,
                        )
                    else:
                        cell_widget = CalendarCell(
                            day=day_num,
                            status="future",
                            is_work_day=False,
                        )
                    row.add_widget(cell_widget)
            self._month_calendar.add_widget(row)

        # 按周汇总
        for ws in data.weekly_summaries:
            ws_start = cast(str, ws.get("week_start", ""))
            ws_net = cast(float, ws.get("net", 0.0))
            sign = "+" if ws_net >= 0 else ""
            summary_row = BoxLayout(
                orientation="horizontal",
                size_hint=(1, None),
                height=28,
                padding=[GRID_UNIT, 0],
            )
            summary_label = Label(
                text=f"{ws_start}  小计: {sign}{ws_net}",
                font_size=FONT_SIZE_SMALL,
                color=self._to_rgba(TEXT_BROWN),
                size_hint=(1, 1),
                halign="left",
                valign="middle",
            )
            summary_row.add_widget(summary_label)
            self._month_calendar.add_widget(summary_row)

    @staticmethod
    def _model_color_to_status(color: str) -> str:
        """将 CalendarCell 的 color 字段映射为 status。"""
        mapping = {
            "green": "normal",
            "yellow": "late",
            "red": "absent",
            "blue": "leave",
            "orange": "shooting",
            "empty": "future",
        }
        return mapping.get(color, "future")

    # ================================================================
    # 年视图
    # ================================================================

    def _build_year_view(self) -> BoxLayout:
        layout = BoxLayout(orientation="vertical", size_hint=(1, 1))

        # 导航栏
        nav = BoxLayout(
            orientation="horizontal",
            size_hint=(1, None),
            height=BTN_HEIGHT,
            padding=[GRID_UNIT, 0],
        )
        self._year_prev_btn = PixelButton(
            text="←", size_mode="small", on_press=lambda: self._navigate_year(-1)
        )
        self._year_label = Label(
            text="",
            font_size=FONT_SIZE_BODY,
            color=self._to_rgba(TEXT_BROWN),
            size_hint=(1, 1),
            halign="center",
            valign="middle",
        )
        self._year_next_btn = PixelButton(
            text="→", size_mode="small", on_press=lambda: self._navigate_year(1)
        )
        nav.add_widget(self._year_prev_btn)
        nav.add_widget(self._year_label)
        nav.add_widget(self._year_next_btn)
        layout.add_widget(nav)

        # MonthCard 列表 (可滚动)
        self._year_scroll = ScrollView(size_hint=(1, 1))
        self._year_card_container = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            spacing=GRID_UNIT,
            padding=[GRID_UNIT, GRID_UNIT],
        )
        self._year_card_container.bind(
            minimum_height=self._year_card_container.setter("height")
        )
        self._year_scroll.add_widget(self._year_card_container)
        layout.add_widget(self._year_scroll)

        return layout

    def _navigate_year(self, direction: int) -> None:
        """切换年 (direction: -1 上一年, +1 下一年)。"""
        self._year_offset += direction
        self._refresh_year_view()

    def _refresh_year_view(self) -> None:
        """重新加载年视图数据并更新 UI。"""
        year = self._current_year + self._year_offset

        try:
            data: YearViewData = self._service.get_year_view(year)
        except Exception:
            return

        self._year_label.text = f"{year}年"

        self._year_card_container.clear_widgets()
        for ms in data.months:
            card = MonthCard(month_summary=ms)
            self._year_card_container.add_widget(card)

    # ================================================================
    # Tab 切换
    # ================================================================

    def _switch_tab(self, tab_index: int) -> None:
        """Tab 切换：显示对应视图，隐藏其他。"""
        self._tab_index = tab_index

        # 先刷新数据再切换
        if tab_index == 0:
            self._refresh_week_view()
        elif tab_index == 1:
            self._refresh_month_view()
        elif tab_index == 2:
            self._refresh_year_view()

        # 控制视图显示
        self._week_view.opacity = 1.0 if tab_index == 0 else 0.0
        self._month_view.opacity = 1.0 if tab_index == 1 else 0.0
        self._year_view.opacity = 1.0 if tab_index == 2 else 0.0

        # 禁用不可见视图的触摸
        self._week_view.disabled = tab_index != 0
        self._month_view.disabled = tab_index != 1
        self._year_view.disabled = tab_index != 2

    # ================================================================
    # DayCard 点击
    # ================================================================

    def _on_day_click(self, day_summary: DayCardModel) -> None:
        """DayCard 点击回调，暂用 print 替代 Toast。"""
        print(f"[HistoryScreen] 点击日卡片: {day_summary.date}")

    # ================================================================
    # 工具方法
    # ================================================================

    @staticmethod
    def _to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
        h = hex_color.lstrip("#")
        return (
            int(h[0:2], 16) / 255.0,
            int(h[2:4], 16) / 255.0,
            int(h[4:6], 16) / 255.0,
            alpha,
        )
