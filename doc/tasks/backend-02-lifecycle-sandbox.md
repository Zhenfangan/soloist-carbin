# backend-02-lifecycle-sandbox: 全生命周期状态机脚本测试

## 职责

利用 `SimulatedClock` 构建跨时间、跨行为的连续业务链条。在 0% UI 挂载下，通过一个独立脚本 `run_backend_closure_test.py` 模拟一周完整周期，断言状态机转向、旷工判定、周结算数据完整性。

## 脚本架构

### 文件路径

```
D:\my-project\soloist-carbin\run_backend_closure_test.py
```

### 初始化骨架

```python
"""后端全生命周期闭环测试 — SimulatedClock 驱动一周业务流"""
import os, tempfile
from app.db import init_db, close_db
from app.utils.clock import SimulatedClock, set_clock
from app.services.event_bus import EventBus, set_event_bus
from app.repositories.settings_repo import SettingsRepo
from app.repositories.checkin_repo import CheckinRepo
from app.repositories.ledger_repo import LedgerRepo
from app.repositories.bet_repo import BetRepo
from app.services.checkin_service import CheckinService
from app.services.bet_service import BetService
from app.services.history_service import HistoryService
from app.services.settings_service import SettingsService

def main():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(db_path)
    clock = SimulatedClock()
    set_clock(clock)
    set_event_bus(EventBus())

    settings_repo = SettingsRepo(db_path)
    settings_svc = SettingsService(settings_repo)
    checkin_svc = CheckinService(CheckinRepo(db_path), settings_repo)
    ledger_repo = LedgerRepo(db_path)
    bet_svc = BetService(BetRepo(db_path), ledger_repo, settings_repo)
    history_svc = HistoryService(CheckinRepo(db_path), ledger_repo, None)

    # === 业务流在此展开 ===

    close_db()
    os.unlink(db_path)
    print("\n=== 全生命周期测试完毕 ===")

if __name__ == "__main__":
    main()
```

---

## 剧情节点

### Story-0: 环境校验

- [ ] 脚本可无报错执行到 `main()` 末尾
- [ ] `settings_svc.get("morning_start")` 返回 `"09:00"` (默认值)
- [ ] `settings_svc.get("afternoon_end")` 返回 `"18:00"`

### Story-1: 周一正常打卡（2026-06-01）

```
clock.set_date_and_time("2026-06-01", "08:55")
```

- [ ] 调用 `checkin_svc.check_in("2026-06-01", "morning")`
- [ ] 断言 `result.status == "normal"`，`result.checkin_time == "08:55:00"`
- [ ] 调用 `clock.set_date_and_time("2026-06-01", "12:05")`
- [ ] 调用 `checkin_svc.check_out("2026-06-01", "morning")`
- [ ] 断言 `result.status == "normal"`，`result.checkout_time == "12:05:00"`
- [ ] 下午: `clock.set_date_and_time("2026-06-01", "13:55")` → `check_in("afternoon")` → 断言 normal
- [ ] `clock.set_date_and_time("2026-06-01", "18:05")` → `check_out("afternoon")` → 断言 normal

### Story-2: 周二全部旷工（2026-06-02）

```
clock.set_date_and_time("2026-06-02", "23:00")
```

- [ ] **不做任何打卡操作**，直接调用 `checkin_svc.mark_absent("2026-06-02")`
- [ ] 断言返回列表中包含 `morning` 和 `afternoon` 两条 absent 记录
- [ ] 调用 `checkin_svc.get_today_status("2026-06-02")`，断言 morning/afternoon 状态为 `absent_morning`/`absent_afternoon`

### Story-3: 周三上午迟到、下午早退（2026-06-03）

```
clock.set_date_and_time("2026-06-03", "09:30")  # 迟到
```

- [ ] `check_in("morning")` → 断言 `result.status == "late"`
- [ ] `clock.set_date_and_time("2026-06-03", "11:30")` → `check_out("morning")` → 断言 `early_leave`，且迟到标记**保留**为 `late`
- [ ] 下午: `clock.set_date_and_time("2026-06-03", "14:00")` → `check_in("afternoon")` → normal
- [ ] `clock.set_date_and_time("2026-06-03", "17:00")` → `check_out("afternoon")` → 断言 `early_leave`

### Story-4: 周四请假（2026-06-04）

```
clock.set_date_and_time("2026-06-04", "08:30")
```

- [ ] `get_leave_options("2026-06-04", "08:30")` → 断言包含 `morning`, `afternoon`, `all_day`
- [ ] `apply_leave("2026-06-04", "all_day")` → 断言返回 2 条记录，状态均为 `leave`
- [ ] `get_today_status("2026-06-04")` → 断言 morning/afternoon 状态均为 `leave`

### Story-5: 周五晚间隔夜间弹性打卡（2026-06-05）

```
clock.set_date_and_time("2026-06-05", "20:00")
```

- [ ] 白天**不打卡** → `mark_absent("2026-06-05")` → 断言 morning/afternoon 标记为 absent
- [ ] 晚上: `check_in("evening")` → 断言 `normal`
- [ ] `clock.set_date_and_time("2026-06-05", "23:00")` → `check_out("evening")` → 断言 `normal`

### Story-6: 周日深夜 — 对赌结算（2026-06-07）

```
clock.set_date_and_time("2026-06-07", "23:30")
```

- [ ] 调用 `bet_svc.get_week_summary("2026-06-01")`（周起始周一）
- [ ] 断言 summary 字典包含 keys: `completed`, `extra_count`, `total_reward`, `completion_rate`, `total_tasks`
- [ ] 断言 `summary["completed"]` ≥ 0（不应为 None）
- [ ] 断言 `summary["total_reward"]` 为 int/float
- [ ] 调用 `history_svc.get_week_view("2026-06-01")`
- [ ] 断言返回 `WeekViewData` 对象，`.days` 字段为 7 条记录

### Story-7: 状态一致性与自愈校验

- [ ] 对 Story-1 的周一日期再次调用 `get_today_status("2026-06-01")`，断言 morning/afternoon 仍为 normal
- [ ] 对所有 7 天调用 `get_today_status`，断言均返回 3 个 periods（morning/afternoon/evening）
- [ ] 脚本全程零 Exception 抛出

---

## 交付标准

- [ ] `python run_backend_closure_test.py` 执行无报错退出（exit code 0）
- [ ] 控制台输出完整 7 天业务流日志
- [ ] 所有 `assert` 通过，无一失败
- [ ] 无 `Logger.error` 或 traceback 输出

任何一步 assert 失败即为 Stage-2 不通过，需定位根因后重新执行全流程。
