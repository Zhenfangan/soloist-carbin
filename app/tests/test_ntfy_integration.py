"""NtfyPushService 与 CheckinService + EventBus 的集成测试。"""
from __future__ import annotations

import time
from pathlib import Path

from app.db import init_db
from app.repositories.checkin_repo import CheckinRepo
from app.repositories.settings_repo import SettingsRepo
from app.services.checkin_service import CheckinService
from app.services.ntfy_service import NtfyPushService
from app.services.settings_service import SettingsService
from app.utils.clock import get_clock


class _Resp:
    def __init__(self, code: int = 200) -> None:
        self.status_code = code


def _wait_for(predicate, timeout: float = 2.0) -> None:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return
        time.sleep(0.05)


def test_check_in_triggers_ntfy(tmp_path: Path) -> None:
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    posts: list[bytes] = []

    def fake_post(url: str, data: bytes = b"", timeout: float = 0) -> _Resp:
        posts.append(data)
        return _Resp(200)

    settings_repo = SettingsRepo(db_path)
    settings_repo.set("ntfy_enabled", "1")
    settings_repo.set("ntfy_topic", "andy_test")
    settings_repo.set("morning_start", "09:00")
    settings_repo.set("morning_end", "12:00")

    get_clock().set_date_and_time("2026-06-18", "08:55")

    checkin_svc = CheckinService(CheckinRepo(db_path), settings_repo)
    ntfy = NtfyPushService(
        SettingsService(settings_repo),
        queue_path=tmp_path / "push_queue.json",
        http_post=fake_post,
    )
    ntfy.start()
    try:
        checkin_svc.check_in("2026-06-18", "morning")
        _wait_for(lambda: len(posts) >= 1)
    finally:
        ntfy.stop()

    assert len(posts) >= 1
    decoded = posts[0].decode("utf-8")
    assert "签到" in decoded
    assert "上午" in decoded


def test_mark_absent_triggers_ntfy_once(tmp_path: Path) -> None:
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    posts: list[bytes] = []

    def fake_post(url: str, data: bytes = b"", timeout: float = 0) -> _Resp:
        posts.append(data)
        return _Resp(200)

    settings_repo = SettingsRepo(db_path)
    settings_repo.set("ntfy_enabled", "1")
    settings_repo.set("ntfy_topic", "andy_test")
    settings_repo.set("morning_start", "09:00")
    settings_repo.set("morning_end", "12:00")

    # 时间设为 13:00，超过 morning_end
    get_clock().set_date_and_time("2026-06-18", "13:00")

    checkin_svc = CheckinService(CheckinRepo(db_path), settings_repo)
    ntfy = NtfyPushService(
        SettingsService(settings_repo),
        queue_path=tmp_path / "push_queue.json",
        http_post=fake_post,
    )
    ntfy.start()
    try:
        # mark_absent 可能被前端反复调用，去重应只推一次
        checkin_svc.mark_absent("2026-06-18")
        checkin_svc.mark_absent("2026-06-18")
        _wait_for(lambda: len(posts) >= 1)
        time.sleep(0.2)
    finally:
        ntfy.stop()

    assert len(posts) == 1
    assert "旷工" in posts[0].decode("utf-8")
