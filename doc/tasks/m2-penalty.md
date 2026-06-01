# M2 — 奖惩模块 子任务

> 职责：考勤奖惩 + 对赌任务结算 + 男友承诺 + 统一账本

---

## 数据层

- [ ] **2.1** 创建 `app/models/ledger.py`：`LedgerEntry` / `BoyfriendPromise` / `BetTask` / `BetConfig` 数据类
- [ ] **2.2** 创建 `app/repositories/ledger_repo.py`：`insert` / `get_by_date` / `get_by_week` / `get_by_month` / `get_daily_summary`
- [ ] **2.3** 创建 `app/repositories/bet_repo.py`：任务 CRUD + 配置 CRUD

## 服务层 — 考勤奖惩

- [ ] **2.4** 创建 `app/services/penalty_service.py`：`calculate_daily(date)` — 根据出勤判定生成罚款流水
- [ ] **2.5** 实现 `calculate_weekly_full_attendance(week_start)` — 全勤判定 + 奖励流水
- [ ] **2.6** 订阅 `ATTENDANCE_JUDGED` → 自动计算当日奖惩

## 服务层 — 男友承诺

- [ ] **2.7** 创建 `app/services/boyfriend_promise_service.py`：`set_promise(date, desc, qty)`
- [ ] **2.8** 实现 `check_fulfill(date, total_hours)` — 时长 ≥ 门槛 → fulfilled + 生成流水

## 服务层 — 对赌任务

- [ ] **2.9** 创建 `app/services/bet_service.py`：任务 CRUD + `set_week_config`
- [ ] **2.10** 实现 `settle_week(week_start)`：完成→奖励 / 超额→额外 / 未完成→惩罚

## 服务层 — 统一账本

- [ ] **2.11** 创建 `app/services/ledger_service.py`：`get_daily_summary` / `get_weekly_summary` / `get_monthly_summary` / `get_yearly_summary`

## UI 层

- [ ] **2.12** 创建 `app/screens/ledger_screen.py`：流水列表 + 按类型/日期筛选 + 汇总
- [ ] **2.13** 创建 `app/screens/bet_screen.py`：本周任务管理 + 对赌配置 + 结算结果
- [ ] **2.14** 创建男友承诺弹窗：上午首次打卡后弹出，输入奖励描述

## 周结算入口

- [ ] **2.15** 实现周结算调度：`DAY_CLOSED` 中判断周日 → 全勤 + 承诺兑现 + 对赌结算 → 发布 `WEEK_CLOSED`

## 测试

- [ ] **2.16** 迟到/早退/旷工罚款 + 全勤奖励 计算测试
- [ ] **2.17** 男友承诺达标/未达标测试
- [ ] **2.18** 对赌完成/超额/未完成 + 周结算汇总 测试
