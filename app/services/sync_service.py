"""同步模块 — APP 端 WebSocket + 备份恢复"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.repositories.sync_repo import SyncRepo
from app.services.event_bus import EventType, get_event_bus
from app.utils.clock import get_clock


class SyncService:
    """同步服务"""

    def __init__(self, sync_repo: SyncRepo, server_url: str = "http://localhost:8000", token: str = "") -> None:
        self._repo = sync_repo
        self._server_url = server_url
        self._token = token
        self._connected = False
        self._cache: list[dict[str, object]] = []
        self._on_message: Callable[[dict[str, object]], None] | None = None

        bus = get_event_bus()
        for et in EventType:
            bus.subscribe(et, self._on_event)

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def push_event(self, event_type: EventType, payload: dict[str, object]) -> None:
        msg: dict[str, object] = {
            "type": event_type.value,
            "timestamp": get_clock().now().isoformat(),
            "payload": payload,
        }
        if self._connected:
            self._send(msg)
        else:
            self._cache.append(msg)

    def flush_cache(self) -> int:
        count = 0
        for msg in self._cache:
            self._send(msg)
            count += 1
        self._cache.clear()
        return count

    def backup_full(self) -> dict[str, object]:
        clock = get_clock()
        data = self._repo.export_all_data()
        self._repo.set_last_backup(clock.now().isoformat())
        result: dict[str, object] = {
            "backed_up": True,
            "data": data,
            "timestamp": clock.now().isoformat(),
        }
        return result

    def restore_full(self, data: dict[str, list[dict[str, Any]]]) -> bool:
        self._repo.import_all_data(data)
        return True

    def set_on_message(self, callback: Callable[[dict[str, object]], None]) -> None:
        self._on_message = callback

    def _send(self, msg: dict[str, object]) -> None:
        if self._on_message:
            self._on_message(msg)

    def _on_event(self, event_type: EventType, payload: dict[str, object]) -> None:
        self.push_event(event_type, payload)
