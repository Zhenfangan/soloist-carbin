"""拍摄日端到端集成 — 真实服务栈(照 main.py 组装) + 真实 DB, 跑完整流程。

覆盖: 设为拍摄日(双表示写入) → 时段卡隐藏 → 提交复盘(存库+奖励入账)
      → 卡片变"已完成" → 战报读到复盘数据; 以及上午前取消回退。
"""

from __future__ import annotations

from kivy.clock import Clock

from app.repositories.checkin_repo import CheckinRepo
from app.repositories.ledger_repo import LedgerRepo
from app.repositories.settings_repo import SettingsRepo
from app.repositories.shooting_repo import ShootingRepo
from app.services.checkin_service import CheckinService
from app.services.report_service import ReportService
from app.services.settings_service import SettingsService
from app.services.shooting_service import ShootingService
from app.ui.screens.checkin_screen import CheckinScreen
from app.utils.clock import get_clock
from app.utils.config import LEDGER_TYPE_SHOOTING_REWARD

_DATE = "2026-06-08"  # 周一


def _build(temp_db: str):
    """照 main.py 真实组装服务栈 + CheckinScreen。"""
    settings_repo = SettingsRepo(temp_db)
    checkin_repo = CheckinRepo(temp_db)
    ledger_repo = LedgerRepo(temp_db)
    shooting_repo = ShootingRepo(temp_db)
    shooting_svc = ShootingService(shooting_repo, ledger_repo, settings_repo)
    checkin_svc = CheckinService(checkin_repo, settings_repo, shooting_service=shooting_svc)
    report_svc = ReportService(checkin_repo, ledger_repo, shooting_repo, settings_repo)
    settings_svc = SettingsService(settings_repo)
    screen = CheckinScreen(
        checkin_service=checkin_svc,
        shooting_service=shooting_svc,
        report_service=report_svc,
        settings_service=settings_svc,
    )
    Clock.tick()
    return screen, checkin_svc, shooting_svc, ledger_repo, report_svc


class TestShootingEndToEnd:
    def test_full_shooting_day_flow(self, temp_db: str) -> None:
        get_clock().set_date_and_time(_DATE, "08:00")  # 上午上班前
        screen, checkin_svc, shooting_svc, ledger_repo, report_svc = _build(temp_db)

        # 1) 上午前、非拍摄日 → 显示"设为拍摄日"入口
        screen._apply_shooting_ui()
        assert screen._shooting_card._state == "idle"
        assert screen._shooting_card.opacity == 1.0

        # 2) 设为拍摄日 → 两套表示都写入 + 时段卡隐藏 + 卡片变 active
        screen._on_set_shooting_day()
        assert shooting_svc.is_shooting_day(_DATE) is True           # 表示 A
        recs = CheckinRepo(temp_db).get_all_by_date(_DATE)
        assert len(recs) == 3 and all(r.is_shooting for r in recs)   # 表示 B
        assert screen._shooting_card._state == "active"
        assert screen._period_cards["morning"].opacity == 0.0
        assert screen._status_box.opacity == 0.0

        # 3) 提交复盘 → 存库 + 奖励入账 + 卡片变 done
        screen._on_reflection_submit({
            "content": "宣传片", "location": "创意园",
            "smoothness": "smooth", "thoughts": "光线很好",
        })
        assert shooting_svc.get_reflection(_DATE) is not None
        rewards = [
            e for e in ledger_repo.get_by_date(_DATE)
            if e.type == LEDGER_TYPE_SHOOTING_REWARD
        ]
        assert len(rewards) == 1
        assert rewards[0].amount == 30
        assert screen._shooting_card._state == "done"

        # 4) 战报读到复盘数据
        data = report_svc.collect_data(_DATE)
        assert data.is_shooting_day is True
        assert data.shooting_content == "宣传片"
        assert data.shooting_location == "创意园"
        assert "宣传片" in data.shooting_reflection

    def test_reflection_reward_not_double_credited(self, temp_db: str) -> None:
        get_clock().set_date_and_time(_DATE, "08:00")
        screen, _, _, ledger_repo, _ = _build(temp_db)
        screen._on_set_shooting_day()
        answers = {"content": "a", "location": "b", "smoothness": "normal", "thoughts": "c"}
        screen._on_reflection_submit(answers)
        screen._on_reflection_submit(answers)  # 再次编辑复盘
        rewards = [
            e for e in ledger_repo.get_by_date(_DATE)
            if e.type == LEDGER_TYPE_SHOOTING_REWARD
        ]
        assert len(rewards) == 1  # 仍只入账一次

    def test_cancel_before_morning_reverts_to_normal(self, temp_db: str) -> None:
        get_clock().set_date_and_time(_DATE, "08:00")
        screen, checkin_svc, shooting_svc, _, _ = _build(temp_db)

        screen._on_set_shooting_day()
        assert shooting_svc.is_shooting_day(_DATE) is True

        screen._on_cancel_shooting_day()
        assert shooting_svc.is_shooting_day(_DATE) is False
        recs = CheckinRepo(temp_db).get_all_by_date(_DATE)
        assert all(not r.is_shooting for r in recs)
        # UI 回到正常时段卡
        screen._apply_shooting_ui()
        assert screen._period_cards["morning"].opacity == 1.0

    def test_cancel_after_morning_blocked(self, temp_db: str) -> None:
        # 先在上午前设为拍摄日
        get_clock().set_date_and_time(_DATE, "08:00")
        screen, checkin_svc, shooting_svc, _, _ = _build(temp_db)
        screen._on_set_shooting_day()
        # 时间推进到上午上班后, 取消应被拒绝
        get_clock().set_date_and_time(_DATE, "09:30")
        screen._on_cancel_shooting_day()
        assert shooting_svc.is_shooting_day(_DATE) is True
