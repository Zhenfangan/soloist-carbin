"""历史模块服务层 — 周/月/年/周期多维度数据查询"""

from __future__ import annotations

import calendar
from datetime import datetime, timedelta

from app.utils.clock import get_clock
from typing import TYPE_CHECKING

from app.models.history import (
    CalendarCell,
    CycleSummary,
    DayCard,
    MonthSummary,
    MonthViewData,
    PeriodSummary,
    WeekViewData,
    YearViewData,
)
from app.models.ledger import LedgerEntry
from app.repositories.checkin_repo import CheckinRepo
from app.repositories.ledger_repo import LedgerRepo
from app.repositories.shooting_repo import ShootingRepo
from app.utils.config import LEDGER_TYPE_SHOOTING_REWARD

if TYPE_CHECKING:
    from app.repositories.bet_repo import BetRepo
    from app.repositories.settings_repo import SettingsRepo


class HistoryService:
    """历史数据查询（只读消费）"""

    def __init__(
        self,
        checkin_repo: CheckinRepo,
        ledger_repo: LedgerRepo,
        shooting_repo: ShootingRepo,
        bet_repo: BetRepo | None = None,
        settings_repo: SettingsRepo | None = None,
    ) -> None:
        self._checkin_repo = checkin_repo
        self._ledger_repo = ledger_repo
        self._shooting_repo = shooting_repo
        self._bet_repo = bet_repo
        self._settings_repo = settings_repo

    def get_week_view(self, week_start: str) -> WeekViewData:
        """周视图：每天一张卡片，含打卡状态/工时/奖惩"""
        start_dt = datetime.strptime(week_start, "%Y-%m-%d")
        week_end = (start_dt + timedelta(days=6)).strftime("%Y-%m-%d")

        checkins = self._checkin_repo.get_all_by_week(week_start)
        entries = self._ledger_repo.get_by_week(week_start)
        entries_by_date: dict[str, list[LedgerEntry]] = {}
        for e in entries:
            if e.entry_date not in entries_by_date:
                entries_by_date[e.entry_date] = []
            entries_by_date[e.entry_date].append(e)

        days: list[DayCard] = []
        weekly_net = 0.0

        for i in range(7):
            date = (start_dt + timedelta(days=i)).strftime("%Y-%m-%d")
            day_checkins = [c for c in checkins if c.checkin_date == date]

            total_hours = 0.0
            periods = []
            is_shooting = False
            for c in day_checkins:
                periods.append(PeriodSummary(
                    period=c.period,
                    status=c.status or "pending",
                    checkin_time=c.checkin_time,
                    checkout_time=c.checkout_time,
                ))
                if c.is_shooting:
                    is_shooting = True
                if c.checkin_time and c.checkout_time:
                    ci = self._time_to_minutes(c.checkin_time)
                    co = self._time_to_minutes(c.checkout_time)
                    diff = co - ci
                    if diff > 0:
                        total_hours += diff / 60.0

            day_entries = entries_by_date.get(date, [])
            day_net = sum(e.amount for e in day_entries)
            weekly_net += day_net

            days.append(DayCard(
                date=date,
                periods=periods,
                total_hours=total_hours,
                daily_ledger=day_entries,
                is_shooting=is_shooting,
            ))

        return WeekViewData(
            week_start=week_start,
            week_end=week_end,
            days=days,
            weekly_net=weekly_net,
        )

    def get_month_view(self, year: int, month: int) -> MonthViewData:
        """月视图：日历格子 + 颜色标记 + 按周汇总"""
        checkins = self._checkin_repo.get_all_by_month(year, month)
        entries = self._ledger_repo.get_by_month(year, month)

        entries_by_date: dict[str, float] = {}
        for e in entries:
            entries_by_date[e.entry_date] = entries_by_date.get(e.entry_date, 0.0) + e.amount

        num_days = calendar.monthrange(year, month)[1]
        cells: list[CalendarCell] = []

        for day in range(1, num_days + 1):
            date = f"{year}-{month:02d}-{day:02d}"

            if self._is_rest_day(date):
                # 休息期优先级最高 —— 即便当天恰好有打卡记录也标为休息
                cells.append(CalendarCell(date=date, color="rest", has_data=True))
                continue

            day_checkins = [c for c in checkins if c.checkin_date == date]

            if not day_checkins:
                cells.append(CalendarCell(date=date, color="empty", has_data=False))
                continue

            statuses = {c.status for c in day_checkins}
            is_shooting = any(c.is_shooting for c in day_checkins)

            if is_shooting:
                color = "shooting"
            elif "absent_morning" in statuses or "absent_afternoon" in statuses:
                color = "absent"
            elif "leave" in statuses:
                color = "leave"
            elif "late" in statuses:
                color = "late"
            elif "early_leave" in statuses:
                color = "early_leave"
            elif all(s == "normal" for s in statuses):
                color = "normal"
            else:
                color = "empty"

            cells.append(CalendarCell(date=date, color=color, has_data=True))

        # Weekly summaries
        weekly_summaries: list[dict[str, object]] = []
        current_week_start: str | None = None
        week_net = 0.0

        for cell in cells:
            dt = datetime.strptime(cell.date, "%Y-%m-%d")
            week_start = (dt - timedelta(days=dt.weekday())).strftime("%Y-%m-%d")
            if current_week_start is None:
                current_week_start = week_start
            if week_start != current_week_start:
                weekly_summaries.append({"week_start": current_week_start, "net": week_net})
                current_week_start = week_start
                week_net = 0.0
            week_net += entries_by_date.get(cell.date, 0.0)
        if current_week_start is not None:
            weekly_summaries.append({"week_start": current_week_start, "net": week_net})

        # 各状态类型本月天数统计(供"各状态统计"卡片展示, 未出现的状态不计入)
        status_counts: dict[str, int] = {}
        for cell in cells:
            if cell.color in ("future", "empty"):
                continue
            status_counts[cell.color] = status_counts.get(cell.color, 0) + 1

        return MonthViewData(
            year=year,
            month=month,
            cells=cells,
            weekly_summaries=weekly_summaries,
            status_counts=status_counts,
        )

    def _is_rest_day(self, date: str) -> bool:
        """指定日期是否落在当前休息期内(含首尾) —— 无 settings_repo 时恒为 False。"""
        if not self._settings_repo:
            return False
        start = self._settings_repo.get("rest_start")
        end = self._settings_repo.get("rest_end")
        if not start or not end:
            return False
        return start <= date <= end

    def get_year_view(self, year: int) -> YearViewData:
        """年视图：12 个月汇总卡片（含对赌数据）"""
        months: list[MonthSummary] = []

        for month in range(1, 13):
            checkins = self._checkin_repo.get_all_by_month(year, month)
            entries = self._ledger_repo.get_by_month(year, month)

            work_days = len({c.checkin_date for c in checkins})
            late_count = sum(1 for c in checkins if c.status in ("late", "early_leave"))
            absent_count = sum(1 for c in checkins
                             if c.status in ("absent_morning", "absent_afternoon"))
            total_hours = 0.0
            for c in checkins:
                if c.checkin_time and c.checkout_time:
                    ci = self._time_to_minutes(c.checkin_time)
                    co = self._time_to_minutes(c.checkout_time)
                    diff = co - ci
                    if diff > 0:
                        total_hours += diff / 60.0

            total_ledger = sum(e.amount for e in entries)

            # 对赌数据：按月查询 bet 相关流水
            bet_cycles = 0
            bet_net = 0.0
            if self._bet_repo:
                month_start = f"{year}-{month:02d}-01"
                if month == 12:
                    month_end = f"{year}-12-31"
                else:
                    month_end = f"{year}-{month+1:02d}-01"
                bet_rows = self._bet_repo.conn.execute(
                    "SELECT COUNT(DISTINCT week_start) as cycles,"
                    " COALESCE(SUM(amount), 0) as net"
                    " FROM ledger_entries"
                    " WHERE type IN ('bet_reward', 'bet_extra', 'bet_penalty', 'bet_late_fee')"
                    " AND entry_date >= ? AND entry_date < ?",
                    (month_start, month_end),
                ).fetchone()
                if bet_rows:
                    bet_cycles = bet_rows["cycles"] or 0
                    bet_net = bet_rows["net"] or 0.0

            months.append(MonthSummary(
                month=month,
                work_days=work_days,
                late_count=late_count,
                absent_count=absent_count,
                total_hours=total_hours,
                total_ledger=total_ledger,
                bet_cycles=bet_cycles,
                bet_net=bet_net,
            ))

        return YearViewData(year=year, months=months)

    def _row_to_cycle_summary(self, row: object) -> CycleSummary:
        """单条 bet_configs 行 → CycleSummary(含任务/金额/滞纳统计)。"""
        ws = row["week_start"]
        week_end = (datetime.strptime(ws, "%Y-%m-%d") + timedelta(days=6)).strftime("%Y-%m-%d")
        status = row["status"]
        late_start = row["late_start_date"] if "late_start_date" in row.keys() else None

        # 任务统计
        tasks = self._bet_repo.conn.execute(
            "SELECT COUNT(*) as total,"
            " SUM(CASE WHEN is_completed THEN 1 ELSE 0 END) as done"
            " FROM bet_tasks WHERE week_start = ?",
            (ws,),
        ).fetchone()
        total_tasks = tasks["total"] if tasks else 0
        completed_tasks = tasks["done"] if tasks else 0

        # 金额统计
        ledger_rows = self._bet_repo.conn.execute(
            "SELECT type, SUM(amount) as amt FROM ledger_entries"
            " WHERE week_start = ? GROUP BY type",
            (ws,),
        ).fetchall()

        base_reward = 0.0
        extra_reward = 0.0
        penalty = 0.0
        late_fees = 0.0
        for lr in ledger_rows:
            amt = abs(lr["amt"]) if lr["amt"] else 0.0
            if lr["type"] == "bet_reward":
                base_reward = amt
            elif lr["type"] == "bet_extra":
                extra_reward = amt
            elif lr["type"] == "bet_penalty":
                penalty = amt
            elif lr["type"] == "bet_late_fee":
                late_fees += amt

        # 滞纳天数
        late_days = 0
        if late_start:
            late_start_dt = datetime.strptime(late_start, "%Y-%m-%d")
            if status == "late":
                late_days = (get_clock().now() - late_start_dt).days + 1
            else:
                late_days = max(0, (get_clock().now() - late_start_dt).days)

        net = base_reward + extra_reward - penalty - late_fees

        # 其他收入(如拍摄日奖励) —— 按日期范围(周期起 7 天), 不接入对赌
        # 结算的 week_start 标记体系(拍摄奖励入账时不打这个标)。
        income_row = self._bet_repo.conn.execute(
            "SELECT COALESCE(SUM(amount), 0) as total FROM ledger_entries"
            " WHERE type = ? AND entry_date >= ? AND entry_date < date(?, '+7 days')",
            (LEDGER_TYPE_SHOOTING_REWARD, ws, ws),
        ).fetchone()
        other_income = income_row["total"] if income_row else 0.0

        return CycleSummary(
            week_start=ws,
            week_end=week_end,
            status=status,
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            base_reward=base_reward,
            extra_reward=extra_reward,
            penalty=penalty,
            late_fees=late_fees,
            late_days=late_days,
            net=net,
            actual_end_date=late_start,
            other_income=other_income,
        )

    def get_cycle_history(self, limit: int = 50) -> list[CycleSummary]:
        """对赌周期历史：每条周期含时长条 + 金额统计。

        按 week_start 倒序返回最近 N 个已结算/滞纳中周期。
        """
        if not self._bet_repo:
            return []

        configs = self._bet_repo.conn.execute(
            "SELECT * FROM bet_configs WHERE status IN ('settled', 'late')"
            " ORDER BY week_start DESC LIMIT ?",
            (limit,),
        ).fetchall()

        return [self._row_to_cycle_summary(row) for row in configs]


    @staticmethod
    def _time_to_minutes(time_str: str) -> int:
        parts = time_str.split(":")
        return int(parts[0]) * 60 + int(parts[1])
