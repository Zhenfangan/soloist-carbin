"""统一账本查询服务（只读）"""

from __future__ import annotations

from app.repositories.ledger_repo import LedgerRepo


class LedgerService:
    """统一账本查询 — 供 M3 战报和 M5 历史使用"""

    def __init__(self, ledger_repo: LedgerRepo) -> None:
        self._repop = ledger_repo

    def get_daily_summary(self, date: str) -> dict[str, object]:
        """返回单日汇总：各类型金额 + 总额"""
        entries = self._repop.get_by_date(date)
        summary: dict[str, float] = {}
        total = 0.0
        for e in entries:
            summary[e.type] = summary.get(e.type, 0.0) + e.amount
            total += e.amount
        summary["total"] = total
        result: dict[str, object] = dict(summary)
        result["entries"] = entries
        return result

    def get_weekly_summary(self, week_start: str) -> dict[str, object]:
        """返回单周汇总：每天金额 + 总额"""
        entries = self._repop.get_by_week(week_start)
        daily: dict[str, float] = {}
        total = 0.0
        for e in entries:
            daily[e.entry_date] = daily.get(e.entry_date, 0.0) + e.amount
            total += e.amount
        return {"daily": daily, "total": total, "entries": entries}

    def get_monthly_summary(self, year: int, month: int) -> dict[str, object]:
        """返回单月汇总：每周金额 + 总额"""
        entries = self._repop.get_by_month(year, month)
        weekly: dict[str, float] = {}
        total = 0.0
        for e in entries:
            week_start = e.week_start or e.entry_date
            weekly[week_start] = weekly.get(week_start, 0.0) + e.amount
            total += e.amount
        return {"weekly": weekly, "total": total, "entries": entries}

    def get_yearly_summary(self, year: int) -> dict[str, object]:
        """返回年度汇总：各月统计"""
        entries = self._repop.get_by_year(year)
        monthly: dict[int, float] = {}
        total = 0.0
        for e in entries:
            month = int(e.entry_date[5:7])
            monthly[month] = monthly.get(month, 0.0) + e.amount
            total += e.amount
        return {"monthly": monthly, "total": total, "entries": entries}
