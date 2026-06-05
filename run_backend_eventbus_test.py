"""后端事件总线副作用与隔离测试"""
from __future__ import annotations

import os
import tempfile

from app.db import init_db, close_db
from app.utils.clock import SimulatedClock, set_clock
from app.services.event_bus import EventBus, EventType, set_event_bus, MAX_PUBLISH_DEPTH
from app.repositories.settings_repo import SettingsRepo
from app.repositories.checkin_repo import CheckinRepo
from app.services.checkin_service import CheckinService


def main():
    passed = 0
    failed = 0

    def check(desc: str, condition: bool, detail: str = "") -> None:
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  [PASS] {desc}")
        else:
            failed += 1
            print(f"  [FAIL] {desc} — {detail}")

    # ============================================================
    # T-1: 订阅者崩溃隔离 — 不阻断后续 handler
    # ============================================================
    print("\n=== T-1: 订阅者崩溃隔离 ===")
    bus = EventBus()

    call_log: list[str] = []

    def crashing_handler(et, data):
        call_log.append("crashing")
        raise RuntimeError("模拟 UI 组件崩溃")

    def normal_handler_1(et, data):
        call_log.append("normal_1")

    def normal_handler_2(et, data):
        call_log.append("normal_2")

    bus.subscribe(EventType.CHECK_IN_COMPLETED, crashing_handler)
    bus.subscribe(EventType.CHECK_IN_COMPLETED, normal_handler_1)
    bus.subscribe(EventType.CHECK_IN_COMPLETED, normal_handler_2)

    try:
        bus.publish(EventType.CHECK_IN_COMPLETED, {"test": True})
        check("publish 自身不抛异常", True)
    except Exception as e:
        check("publish 自身不抛异常", False, f"异常: {type(e).__name__}: {e}")

    check("crashing handler 被调用", "crashing" in call_log)
    check("normal_handler_1 被调用（未被 crashing 阻断）", "normal_1" in call_log,
          f"调用日志: {call_log}")
    check("normal_handler_2 被调用（未被 crashing 阻断）", "normal_2" in call_log,
          f"调用日志: {call_log}")
    check("handler 执行顺序正确",
          call_log == ["crashing", "normal_1", "normal_2"],
          f"实际: {call_log}")

    # ============================================================
    # T-2: 环形发布深度截断
    # ============================================================
    print("\n=== T-2: 环形发布深度截断 ===")
    bus2 = EventBus()
    loop_count = [0]

    def loop_handler(et, data):
        loop_count[0] += 1
        bus2.publish(EventType.CHECK_IN_COMPLETED, {"depth": loop_count[0]})

    bus2.subscribe(EventType.CHECK_IN_COMPLETED, loop_handler)

    try:
        bus2.publish(EventType.CHECK_IN_COMPLETED, {"depth": 0})
        check("环形发布不导致 RecursionError", True)
    except RecursionError:
        check("环形发布不导致 RecursionError", False, "栈溢出!")
    except Exception as e:
        check("环形发布不导致崩溃", False, f"异常: {type(e).__name__}: {e}")

    check("环形发布被深度截断", loop_count[0] <= MAX_PUBLISH_DEPTH + 1,
          f"实际循环: {loop_count[0]} 次 (阈值: {MAX_PUBLISH_DEPTH})")

    # ============================================================
    # T-3: Payload 浅拷贝隔离
    # ============================================================
    print("\n=== T-3: Payload 浅拷贝隔离 ===")
    bus3 = EventBus()

    def modifier_handler(et, data):
        data["corrupted"] = True
        data["test"] = "modified"

    def reader_handler(et, data):
        reader_handler.received_test = data.get("test")
        reader_handler.received_corrupted = data.get("corrupted", False)

    bus3.subscribe(EventType.SETTINGS_CHANGED, modifier_handler)
    bus3.subscribe(EventType.SETTINGS_CHANGED, reader_handler)

    bus3.publish(EventType.SETTINGS_CHANGED, {"test": "original"})

    check("reader 收到的 test 未被 modifier 修改",
          reader_handler.received_test == "original",
          f"实际: {reader_handler.received_test}")
    check("reader 未收到 corrupted 字段",
          reader_handler.received_corrupted == False,
          f"实际: {reader_handler.received_corrupted}")

    # ============================================================
    # T-4: Service 层不被 handler 崩溃影响（集成验证）
    # ============================================================
    print("\n=== T-4: Service 层集成隔离 ===")
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(db_path)
    clock = SimulatedClock()
    set_clock(clock)
    bus4 = EventBus()
    set_event_bus(bus4)

    checkin_svc = CheckinService(CheckinRepo(db_path), SettingsRepo(db_path))

    # 注册一个会崩溃的 handler
    def crashing_subscriber(et, data):
        raise RuntimeError("模拟 UI handler 崩溃")

    bus4.subscribe(EventType.CHECK_IN_COMPLETED, crashing_subscriber)

    clock.set_date_and_time("2026-06-01", "09:00")
    try:
        result = checkin_svc.check_in("2026-06-01", "morning")
        check("check_in() 不抛异常（handler 崩溃已隔离）", True)
        check("check_in() 返回正常结果", result is not None)
        check("签到状态为 normal", result.status == "normal", f"实际: {result.status}")
    except Exception as e:
        check("check_in() 不抛异常", False, f"异常: {type(e).__name__}: {e}")

    # 验证数据已正确落盘
    records = CheckinRepo(db_path).get_all_by_date("2026-06-01")
    morning = [r for r in records if r.period == "morning"]
    check("DB 中 morning 记录已落盘（事件在 DB 写入之后发布）",
          len(morning) == 1 and morning[0].checkin_time is not None,
          f"记录数: {len(morning)}")

    close_db()
    os.unlink(db_path)

    # ============================================================
    print(f"\n=== 事件总线隔离测试完毕 ===")
    print(f"通过: {passed}, 失败: {failed}")
    if failed > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
