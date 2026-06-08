"""验证 CheckinScreen._handle_task_add 添加后刷新 TaskInlineList。"""

from __future__ import annotations

from unittest.mock import MagicMock

from app.models.ledger import BetTask
from app.ui.screens.checkin_screen import CheckinScreen


def test_handle_task_add_refreshes_task_list() -> None:
    """添加任务后 _task_list.set_tasks 应被调用, 且数据从 bet_service 重新获取。"""
    bet_svc = MagicMock()
    bet_svc.get_week_tasks.return_value = [
        BetTask(
            week_start="2026-06-01",
            task_desc="新任务",
            target_qty=1,
            current_qty=0,
            is_completed=0,
            id=1,
        ),
    ]
    bet_svc.create_task = MagicMock()

    screen = CheckinScreen(bet_service=bet_svc)
    screen._date_str = "2026-06-07"
    screen._task_list = MagicMock()

    screen._handle_task_add("新任务", 1)

    bet_svc.create_task.assert_called_once()
    screen._task_list.set_tasks.assert_called_once()

    # 验证传入的数据是 list[dict] 格式, 含 id/desc/done
    call_args = screen._task_list.set_tasks.call_args[0][0]
    assert isinstance(call_args, list)
    assert call_args[0]["id"] == 1
    assert call_args[0]["desc"] == "新任务"
    assert call_args[0]["done"] is False
