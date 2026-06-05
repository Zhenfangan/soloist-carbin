# backend-06-race-conditions: 并发、重入与幂等性轰炸

## 职责

审计数据库 Schema 级硬防御完备性、Service 层的读-改-写竞态窗口、以及高并发重入场景下的状态机一致性。目标是确保系统在"用户狂点按钮"级别的并发压力下，数据库零污染、状态机零错乱。

## 自查核心痛点

### R-1: upsert 的 SELECT-then-write 竞态窗口（TOCTOU）

**现状** (`app/repositories/checkin_repo.py:22-59`)：

```python
def upsert(self, checkin):
    existing = self.get_by_date_period(checkin.checkin_date, checkin.period)
    if existing:
        self._execute("UPDATE ...")
    else:
        rid = self._insert("INSERT ...")
```

经典的 Time-of-Check-to-Time-of-Use（TOCTOU）漏洞：
- 线程 A：`get_by_date_period()` → `None`（不存在）
- 线程 B：`get_by_date_period()` → `None`（也不存在）
- 线程 A：`_insert()` → 成功
- 线程 B：`_insert()` → **`IntegrityError: UNIQUE constraint failed`** → 未捕获，向上传播崩溃

虽然 DDL 中有 `UNIQUE(checkin_date, period)` 硬约束，但应用层没有处理冲突，而是依赖"先查后写"的乐观假设。正确的做法是使用 `INSERT OR IGNORE` 或 `INSERT ... ON CONFLICT DO UPDATE`（SQLite 3.24+ 支持 upsert 语法），由数据库引擎原子地处理冲突。

**自查项**：
- [ ] 列出所有使用"SELECT → if exists UPDATE else INSERT"模式的 Repository 方法（CheckinRepo.upsert、BetRepo.upsert_config）
- [ ] 检查 `bet_tasks` 表是否有合适的 UNIQUE 约束（当前无——`week_start + task_desc` 组合应唯一）
- [ ] 检查 `bet_configs` 表 `UNIQUE(week_start)` 是否被正确利用（当前 upsert_config 也是 SELECT-then-write）

### R-2: update_task_progress 的读-改-写丢失更新

**现状** (`app/repositories/bet_repo.py:39-51`)：

```python
def update_task_progress(self, task_id, current_qty):
    task_row = self._fetch_one("SELECT * FROM bet_tasks WHERE id = ?", (task_id,))
    target = task_row["target_qty"]
    is_completed = 1 if current_qty >= target else task_row["is_completed"]
    self._execute("UPDATE bet_tasks SET current_qty = ?, is_completed = ? WHERE id = ?",
                  (current_qty, is_completed, task_id))
```

典型丢失更新（Lost Update）场景：
1. 任务 target_qty=3, current_qty=1
2. 用户快速点击两次 [+1]，触发两个并发请求
3. 线程 A：读 current_qty=1 → 计算 new=2 → UPDATE current_qty=2
4. 线程 B：读 current_qty=1（在 A 写入前）→ 计算 new=2 → UPDATE current_qty=2
5. 最终 current_qty=2，但正确值应为 3

**修复方向**：使用原子更新 `UPDATE bet_tasks SET current_qty = current_qty + 1` 而非"读-算-写"。

**自查项**：
- [ ] 确认所有涉及计数器/进度更新的 SQL 是否使用了原子操作（`SET x = x + ?`）而非先读后写
- [ ] 检查 `complete_task()` 是否存在类似的竞态（当前是 `UPDATE SET is_completed=1`，是原子的，无问题）

### R-3: settle_week 的非原子多步写入

**现状** (`app/services/bet_service.py:69-145`)：

```python
def settle_week(self, week_start):
    # ... 计算 entries ...
    for entry in entries:       # 逐条写入，每条独立 commit
        self._ledger_repo.insert(entry)
    # 标记 config 已结算（又一次 commit）
    if config:
        config.status = "settled"
        self._bet_repo.upsert_config(config)
```

若在第 2 条 ledger 写入后进程崩溃：
- 第 1 条 ledger 已持久化
- 第 2、3 条 ledger 丢失
- config 未标记 settled → 下次启动可再次结算 → **重复写入 ledger**

**自查项**：
- [ ] 确认 `settle_week()` 是否需要幂等守卫（例如结算前检查 config.status 是否为 'settled'）
- [ ] 确认所有多步写入的 Service 方法是否需要包裹在同一个 SQLite 事务中

### R-4: SQLite 写锁争用 — 无 busy_timeout

**现状** (`app/db.py:111-113`)：

```python
conn = sqlite3.connect(db_path, check_same_thread=False)
conn.execute("PRAGMA journal_mode=WAL")
# 未设置 busy_timeout
```

SQLite 默认 `busy_timeout=0`，即遇到锁立即返回 `SQLITE_BUSY`。WAL 模式下，多个读可以并发，但**写操作是串行的**。如果两个线程同时尝试写入：
- 第一个获得写锁，执行写入
- 第二个立即收到 `OperationalError: database is locked`，无等待

**自查项**：
- [ ] 确认是否需要设置 `busy_timeout=5000`（等待 5 秒）
- [ ] 确认 WAL 模式下是否需要定期执行 `PRAGMA wal_checkpoint` 防止 WAL 文件无限增长

---

## 测试床验证思路

### T-1: 并发轰炸 — 同一毫秒 10 次打卡

```python
# 核心思路：使用 concurrent.futures.ThreadPoolExecutor
# 在同一时刻对同一 date+period 发起 10 个并发 check_in

import concurrent.futures

clock.set_date_and_time("2026-06-01", "09:00")

def bomb_checkin(i):
    try:
        return checkin_svc.check_in("2026-06-01", "morning")
    except Exception as e:
        return e

with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(bomb_checkin, i) for i in range(10)]
    results = [f.result() for f in futures]

# 断言
successes = [r for r in results if not isinstance(r, Exception)]
failures = [r for r in results if isinstance(r, Exception)]
```

**验证步骤**：
1. 使用 `ThreadPoolExecutor(max_workers=10)` 同时提交 10 个 `check_in` 请求
2. 断言至少 1 个成功（有结果返回）
3. 断言所有 `Exception` 类型的返回都被优雅捕获（非崩溃）
4. 断言 DB 中 `2026-06-01` 的 `morning` 记录仅 1 条
5. 断言该记录的数据完整（checkin_time 不为 NULL）

### T-2: update_task_progress 并发递增验证

```python
# 创建任务 target_qty=10
# 10 个线程同时调用 update_task_progress(task_id, current_qty)
# 但每个线程读到的 current_qty 可能相同（丢失更新）
# 正确做法：改为原子操作后，10 个并发 +1 应得到 current_qty=10
```

**验证步骤**：
1. 创建任务（target_qty=10）
2. 10 个线程，每个执行 `UPDATE bet_tasks SET current_qty = current_qty + 1 WHERE id = ?`
3. 读取最终 current_qty，断言为 10（无丢失更新）

### T-3: settle_week 重复调用幂等性

```python
# 对同一 week_start 连续调用 settle_week 两次
# 断言第二次调用检测到 config.status == 'settled'，直接返回（不重复写入 ledger）
```

### T-4: UNIQUE 约束完备性扫描

```python
# 编程化扫描所有建表 DDL，检查以下表是否有合理的 UNIQUE 约束：
# checkins:       UNIQUE(checkin_date, period) ✅ 已有
# bet_configs:    UNIQUE(week_start)            ✅ 已有
# bet_tasks:      UNIQUE(week_start, task_desc) ❌ 缺失
# settings:       PRIMARY KEY(key)              ✅ 等同 UNIQUE
# boyfriend_promises: UNIQUE(promise_date)      ✅ 已有
# shooting_days:  UNIQUE(shoot_date)            ✅ 已有
# shooting_reflections: UNIQUE(shoot_date)      ✅ 已有
```

---

## 交付合格线

- [ ] `python run_backend_race_test.py` 执行无 traceback 崩溃
- [ ] 10 线程并发打卡：DB 中仅 1 条记录，零 `IntegrityError` 未捕获崩溃
- [ ] 10 线程并发递增任务进度：最终 current_qty 精确等于并发数（无丢失更新）
- [ ] `settle_week()` 重复调用：第二次被幂等守卫拦截，ledger 表无重复记录
- [ ] SQLite `busy_timeout` 已设置为 ≥ 3000ms
- [ ] `INSERT OR IGNORE` / `ON CONFLICT` 语法替换所有 TOCTOU 模式的 upsert
- [ ] 所有现有 128 个单元测试无回归
- [ ] `mypy app/services/ app/repositories/ --strict` 零类型错误
