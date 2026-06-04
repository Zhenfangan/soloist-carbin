# backend-03-boundary-stress: 控制台边界与压力测试

## 职责

轰炸 Service 层边界——非法时间、重复动作、未初始化状态——验证后端在所有异常输入下优雅返回（拒绝服务或降级处理），而非抛出未捕获异常导致进程崩溃。

## 测试脚本

```
D:\my-project\soloist-carbin\run_backend_stress_test.py
```

初始化骨架与 Stage-2 脚本一致：临时数据库 + `SimulatedClock` + `EventBus` 重置。

---

## S-1: 异常时间轰炸

### S-1a: 凌晨 3 点打卡

```
clock.set_date_and_time("2026-06-01", "03:00")
```

- [ ] 调用 `checkin_svc.check_in("2026-06-01", "morning")`
- [ ] 断言 **不抛异常**，返回 `CheckinResult` 对象
- [ ] 断言 `result.status` 为 `"normal"`（提前到，窗口未开但接受）
- [ ] 调用 `checkin_svc.check_in("2026-06-01", "afternoon")`
- [ ] 断言不抛异常，返回结果

### S-1b: 非法 period 名称

- [ ] 调用 `checkin_svc.check_in("2026-06-01", "midnight")`
- [ ] 断言不抛 `KeyError`，返回正常结果（状态为 `normal`——因 `_PERIOD_START_KEY.get("midnight", "")` 返回空字符串，走 normal 分支）

### S-1c: 非法日期格式

- [ ] 调用 `checkin_svc.check_in("not-a-date", "morning")`
- [ ] 断言不抛异常（Repo 层 SQLite 接受任意字符串作为日期）

### S-1d: 签退时间早于上班时间

```
clock.set_date_and_time("2026-06-01", "06:00")
svc.check_in("2026-06-01", "morning")   # 提前到，正常
clock.set_date_and_time("2026-06-01", "07:00")
```

- [ ] 调用 `svc.check_out("2026-06-01", "morning")` → 断言 `result.status == "early_leave"`
- [ ] 不抛异常

---

## S-2: 并发/重复动作幂等性

### S-2a: 同日期同时段连续 3 次打卡

```
clock.set_date_and_time("2026-06-01", "08:55")
```

- [ ] `r1 = svc.check_in("2026-06-01", "morning")`
- [ ] `r2 = svc.check_in("2026-06-01", "morning")`  ← 第二次
- [ ] `r3 = svc.check_in("2026-06-01", "morning")`  ← 第三次
- [ ] 断言 `r1`, `r2`, `r3` 均返回 `CheckinResult`
- [ ] 断言三者 `checkin_time` 相同（不产生新时间戳，因为模拟时钟未推进）
- [ ] 查询 DB：`checkin_repo.get_all_by_date("2026-06-01")` 中 `morning` 记录**只有 1 条**（`UNIQUE(checkin_date, period)` 约束保证）
- [ ] 断言记录 `checkin_time` 不为 NULL

### S-2b: 同日期同时段连续 3 次签退

```
clock.set_date_and_time("2026-06-01", "12:05")
```

- [ ] `r1 = svc.check_out("2026-06-01", "morning")`
- [ ] `r2 = svc.check_out("2026-06-01", "morning")`
- [ ] `r3 = svc.check_out("2026-06-01", "morning")`
- [ ] 均不抛异常
- [ ] DB 中仍仅 1 条 morning 记录，`checkout_time` 为最后一次的值

### S-2c: 签退未签到时段（已修复逻辑回归验证）

- [ ] 使用全新日期 `"2026-07-15"`，仅调用 `svc.check_out("2026-07-15", "morning")`
- [ ] 断言抛出 `ValueError`，消息包含 `"尚未签到"`
- [ ] DB 中不存在 `"2026-07-15"` 的任何记录

---

## S-3: 未初始化结算

### S-3a: 不配置周赏罚金额直接结算

```python
# 确保 bet_configs 表为空（不使用 BetRepo 写入任何配置）
bet_svc = BetService(BetRepo(db_path), ledger_repo, settings_repo)
summary = bet_svc.get_week_summary("2026-06-01")
```

- [ ] 断言 `summary` 为 dict
- [ ] 断言 `summary.get("total_reward", -1)` 为 0（而非 None 或抛异常）
- [ ] 断言 `summary.get("completion_rate", -1)` 为 0

### S-3b: 在未完成任何打卡时强行结算

- [ ] 对所有 7 天不做任何打卡操作，直接 `bet_svc.get_week_summary("2026-07-01")`
- [ ] 断言不抛异常，返回 dict 各字段为 0

### S-3c: 空 DB 状态查询

- [ ] 全新临时 DB，不做任何操作，调用 `checkin_svc.get_today_status("2099-01-01")`
- [ ] 断言返回 `DayStatus`，`periods` 长度为 3，全部 `status == "pending"`
- [ ] 不抛异常

---

## S-4: 快速状态翻转（状态机抖动）

模拟用户在极短时间内改变决策：签到 → 立刻签退 → 立刻再次签到的边界行为。

```
clock.set_date_and_time("2026-06-01", "08:55")
```

- [ ] `svc.check_in("2026-06-01", "morning")` → normal
- [ ] `svc.check_out("2026-06-01", "morning")` → 此时状态取决于签退时间（08:55 < 12:00 → early_leave）
- [ ] `svc.check_in("2026-06-01", "morning")` → 第二次签到，此时记录已有 checkin_time 和 checkout_time
- [ ] 断言第二次签到的结果不抛异常，返回 `CheckinResult`
- [ ] 断言第二次签到后，`checkout_time` 被清空或覆盖（取决于 upsert 逻辑）
- [ ] DB 中仍仅 1 条 morning 记录

---

## S-5: None / 空字符串注入

- [ ] `svc.check_in("", "morning")` → 不抛异常（空日期写入 DB）
- [ ] `svc.check_in("2026-06-01", "")` → 不抛异常（空 period 写入 DB）
- [ ] `settings_svc.set("morning_start", "")` → 不抛异常
- [ ] 设置空字符串后调用 `svc.check_in("2026-06-01", "morning")` → 不抛异常，返回 normal（空字符串 ≤ 任何时间）

---

## 交付标准

- [ ] `python run_backend_stress_test.py` 执行无 traceback 崩溃
- [ ] 所有 S-1 ~ S-5 的 assert 全部通过
- [ ] 无 `KeyError`、`AttributeError`、`NoneType` 未捕获异常
- [ ] DB 幂等性验证：重复操作不产生重复记录

三项任务书全部达标后，后端质量审计封闭，方可返回 UI 层修复。
