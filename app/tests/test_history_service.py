"""HistoryService 历史模块测试"""

from __future__ import annotations

from app.models.checkin import Checkin
from app.repositories.bet_repo import BetRepo
from app.repositories.checkin_repo import CheckinRepo
from app.repositories.ledger_repo import LedgerRepo
from app.repositories.settings_repo import SettingsRepo
from app.repositories.shooting_repo import ShootingRepo
from app.services.bet_service import BetService
from app.services.history_service import HistoryService
from app.services.settings_service import SettingsService


class TestHistoryService:
    def setup_svc(self, temp_db: str) -> HistoryService:
        return HistoryService(CheckinRepo(temp_db), LedgerRepo(temp_db), ShootingRepo(temp_db))

    def test_empty_week_view(self, temp_db: str) -> None:
        svc = self.setup_svc(temp_db)
        view = svc.get_week_view("2026-06-01")
        assert view.week_start == "2026-06-01"
        assert view.week_end == "2026-06-07"
        assert len(view.days) == 7
        assert view.weekly_net == 0.0

    def test_week_view_with_data(self, temp_db: str) -> None:
        checkin_repo = CheckinRepo(temp_db)
        checkin_repo.upsert(Checkin(
            checkin_date="2026-06-01", period="morning",
            checkin_time="09:00:00", checkout_time="12:00:00", status="normal",
        ))

        svc = self.setup_svc(temp_db)
        view = svc.get_week_view("2026-06-01")
        monday = view.days[0]
        assert monday.date == "2026-06-01"
        assert len(monday.periods) == 1
        assert monday.total_hours == 3.0

    def test_month_view_colors(self, temp_db: str) -> None:
        checkin_repo = CheckinRepo(temp_db)
        checkin_repo.upsert(Checkin(
            checkin_date="2026-06-01", period="morning",
            checkin_time="09:00:00", checkout_time="12:00:00", status="normal",
        ))
        checkin_repo.upsert(Checkin(
            checkin_date="2026-06-01", period="afternoon",
            checkin_time="14:00:00", checkout_time="18:00:00", status="normal",
        ))
        checkin_repo.upsert(Checkin(
            checkin_date="2026-06-02", period="morning", status="late",
        ))
        checkin_repo.upsert(Checkin(
            checkin_date="2026-06-03", period="afternoon", status="early_leave",
        ))

        svc = self.setup_svc(temp_db)
        view = svc.get_month_view(2026, 6)
        assert len(view.cells) == 30

        # Day 1: 全天正常 → normal(语义色名, 不再用 "green")
        assert view.cells[0].color == "normal"

        # Day 2: 迟到 → late
        assert view.cells[1].color == "late"

        # Day 3: 早退 → early_leave(独立成色, 不再和迟到混成一色)
        assert view.cells[2].color == "early_leave"

    def test_month_view_status_counts(self, temp_db: str) -> None:
        """月历"各状态统计"卡片需要的原始数据: 按状态类型统计本月天数,
        供每个类型一张卡片(玻璃框+点 bar)展示, 零次数的类型不应出现在结果里
        (卡片按此过滤, 不显示当月没发生过的状态)。
        """
        checkin_repo = CheckinRepo(temp_db)
        checkin_repo.upsert(Checkin(
            checkin_date="2026-06-01", period="morning",
            checkin_time="09:00:00", checkout_time="12:00:00", status="normal",
        ))
        checkin_repo.upsert(Checkin(
            checkin_date="2026-06-01", period="afternoon",
            checkin_time="14:00:00", checkout_time="18:00:00", status="normal",
        ))
        checkin_repo.upsert(Checkin(
            checkin_date="2026-06-02", period="morning", status="late",
        ))
        checkin_repo.upsert(Checkin(
            checkin_date="2026-06-03", period="morning", status="late",
        ))

        svc = self.setup_svc(temp_db)
        view = svc.get_month_view(2026, 6)

        assert view.status_counts["normal"] == 1
        assert view.status_counts["late"] == 2
        # 本月没有旷工, 不应出现在统计里(供 UI 据此隐藏对应卡片)
        assert "absent" not in view.status_counts
        assert "future" not in view.status_counts
        assert "empty" not in view.status_counts

    def test_month_view_marks_rest_days(self, temp_db: str) -> None:
        """休息期内的日期在月视图里应标为 "rest"(灰蓝), 优先级高于其他状态
        —— 即便当天恰好有打卡记录(理论上不该发生, 但休息态应盖过它)。
        """
        checkin_repo = CheckinRepo(temp_db)
        checkin_repo.upsert(Checkin(
            checkin_date="2026-06-02", period="morning",
            checkin_time="09:00:00", checkout_time="12:00:00", status="normal",
        ))
        settings_repo = SettingsRepo(temp_db)
        SettingsService(settings_repo).start_rest_period("2026-06-02", 3)

        svc = HistoryService(
            checkin_repo, LedgerRepo(temp_db), ShootingRepo(temp_db),
            settings_repo=settings_repo,
        )
        view = svc.get_month_view(2026, 6)

        # 6/2 ~ 6/4 是休息期(含首尾)
        assert view.cells[1].color == "rest"   # 6/2 (即便有打卡记录)
        assert view.cells[2].color == "rest"   # 6/3
        assert view.cells[3].color == "rest"   # 6/4
        assert view.cells[4].color != "rest"   # 6/5 已恢复

    def test_cycle_history_includes_other_income(self, temp_db: str) -> None:
        """周期视图: 每条周期要把拍摄日奖励等"其他收入"和对赌净额加在一起,
        作为独立字段(other_income), 供 CycleBar 显示合计的一行。
        """
        from app.models.ledger import LedgerEntry
        from app.utils.config import LEDGER_TYPE_SHOOTING_REWARD

        bet_repo = BetRepo(temp_db)
        ledger_repo = LedgerRepo(temp_db)
        settings_repo = SettingsRepo(temp_db)
        bet_svc = BetService(bet_repo, ledger_repo, settings_repo)

        bet_svc.set_week_config("2026-06-01", 50, 30, 50)
        t1 = bet_svc.create_task("2026-06-01", "任务1")
        assert t1.id is not None
        bet_svc.complete_task(t1.id)
        bet_svc.settle_week("2026-06-01")

        # 本周期内(6/1~6/7)拍摄日奖励入账
        ledger_repo.insert(LedgerEntry(
            entry_date="2026-06-03", type=LEDGER_TYPE_SHOOTING_REWARD, amount=30.0,
        ))
        # 周期外的拍摄奖励不应计入
        ledger_repo.insert(LedgerEntry(
            entry_date="2026-06-20", type=LEDGER_TYPE_SHOOTING_REWARD, amount=99.0,
        ))

        svc = HistoryService(CheckinRepo(temp_db), ledger_repo, ShootingRepo(temp_db), bet_repo)
        cycles = svc.get_cycle_history()

        assert len(cycles) == 1
        assert cycles[0].net == 50.0
        assert cycles[0].other_income == 30.0

    def test_year_view(self, temp_db: str) -> None:
        checkin_repo = CheckinRepo(temp_db)
        for month in (1, 3, 5):
            checkin_repo.upsert(Checkin(
                checkin_date=f"2026-{month:02d}-01", period="morning",
                checkin_time="09:00:00", checkout_time="12:00:00", status="normal",
            ))

        svc = self.setup_svc(temp_db)
        view = svc.get_year_view(2026)
        assert len(view.months) == 12

        jan = view.months[0]
        assert jan.month == 1
        assert jan.work_days == 1

        feb = view.months[1]
        assert feb.work_days == 0
