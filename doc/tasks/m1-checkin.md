# M1 — 考勤模块 子任务

> 职责：打卡动作 + 出勤状态判定 + 请假 + 提醒

---

## 数据层

- [ ] **1.1** 创建 `app/models/checkin.py`：定义 `Checkin` 和 `CheckinResult` 数据类
- [ ] **1.2** 创建 `app/repositories/checkin_repo.py`：`get_by_date_period` / `upsert` / `get_all_by_date` / `get_all_by_week` / `get_all_by_month` / `get_unchecked_out`

## 服务层

- [ ] **1.3** 创建 `app/services/checkin_service.py`：`check_in(date, period)` — 签到 + 判定 + 发布 `CHECK_IN_COMPLETED`
- [ ] **1.4** 实现 `check_out(date, period)` — 签退 + 判定 + 发布 `CHECK_OUT_COMPLETED` / `DAY_FINISHED`
- [ ] **1.5** 实现 `get_leave_options(date, current_time)` — 请假窗口期判断（上午/下午/全天/不可请）
- [ ] **1.6** 实现 `apply_leave(date, scope)` — 执行请假 + 发布 `ATTENDANCE_JUDGED`
- [ ] **1.7** 实现 `get_today_status(date)` — 返回今日各时段状态快照
- [ ] **1.8** 实现旷工补判：APP 前台时检查，上午超 1h / 下午超 1.5h 无打卡无请假 → `absent`
- [ ] **1.9** 实现忘记签退处理：日切时扫描有签到无签退 → 自动补签退 (`checkout_type=auto`)
- [ ] **1.10** 创建 `app/services/reminder_service.py`：`schedule_all()` / `cancel_all()`，用 Android AlarmManager

## UI 层

- [ ] **1.11** 创建 `app/components/checkin_button.py`：根据时段/状态切换签到/签退按钮
- [ ] **1.12** 创建 `app/components/attendance_status.py`：三时段状态展示 + 请假按钮（窗口期限制）
- [ ] **1.13** 创建 `app/screens/main_screen.py`：集成打卡按钮、状态展示、请假入口

## 测试

- [ ] **1.14** 准时 / 迟到 / 早退 / 请假 / 旷工判定 各场景单元测试
- [ ] **1.15** 请假窗口期判断逻辑测试
- [ ] **1.16** 忘记签退自动处理测试
