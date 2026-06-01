"""pytest 全局 fixtures — 模拟时钟 + EventBus 重置 + 内存数据库"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Generator

import pytest

from app.db import close_db, init_db
from app.services.event_bus import EventBus, set_event_bus
from app.utils.clock import SimulatedClock, set_clock


@pytest.fixture(autouse=True)
def reset_globals() -> None:
    """每个测试前重置全局时钟和事件总线"""
    set_clock(SimulatedClock())
    set_event_bus(EventBus())


@pytest.fixture
def clock() -> SimulatedClock:
    """返回当前模拟时钟实例"""
    from app.utils.clock import get_clock

    return get_clock()  # type: ignore[return-value]


@pytest.fixture
def bus() -> EventBus:
    """返回当前事件总线实例"""
    from app.services.event_bus import get_event_bus

    return get_event_bus()


@pytest.fixture
def temp_db() -> Generator[str, None, None]:
    """创建临时数据库文件，测试结束后清理"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    close_db()
    os.unlink(path)
