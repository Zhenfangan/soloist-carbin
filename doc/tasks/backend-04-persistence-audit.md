# backend-04-persistence-audit: 持久化与数据残留审计

## 职责

审计 SQLite 持久层的连接生命周期、事务原子性、冷启动恢复完整性，确保真实磁盘 I/O 场景下零数据损坏、零死锁残留。

## 自查核心痛点

### P-1: 线程本地连接 + check_same_thread=False 的语义冲突

**现状** (`app/db.py:103-114`)：

```python
_local = threading.local()
conn = sqlite3.connect(db_path, check_same_thread=False)
```

`threading.local()` 为每个线程创建独立连接，但同时设置了 `check_same_thread=False`。这两者叠加意味着：
- 同一线程复用同一连接（正确）
- 但如果某个对象跨线程传递了 `Connection` 引用，SQLite 不会拒绝（危险）
- WAL 模式下，写线程持有写锁期间，其他线程的读操作会立即收到 `database is locked`（SQLITE_BUSY），而非等待

**自查项**：
- [ ] 确认所有 Repository 实例是否可能被多个线程共享（当前 `BaseRepo.__init__` 接收 `db_path` 而非 `Connection`，每个 Repo 通过 `get_db(path)` 按线程获取连接——检查是否存在跨线程传递 Repo 实例的路径）
- [ ] 确认 WAL 模式下的 busy timeout 是否配置（当前仅设置了 `journal_mode=WAL`，未设置 `busy_timeout`）

### P-2: 隐式自动提交导致多语句操作非原子

**现状** (`app/repositories/base.py:20-24`)：

```python
def _execute(self, sql, params=()):
    cursor = self.conn.execute(sql, params)
    self.conn.commit()  # 每条语句后立即提交
    return cursor
```

每个 `_execute` / `_insert` 调用后立即 `commit()`，意味着：
- `CheckinRepo.upsert()` 的 SELECT → UPDATE/INSERT 是**两次独立事务**，中间窗口期可能被其他操作插入
- `BetService.settle_week()` 写入多条 `LedgerEntry` + 更新 `BetConfig`，若中途崩溃，**部分 ledger 已持久化但 config 未标记 settled**，导致重复结算

**自查项**：
- [ ] 排查所有涉及 ≥2 次 `_execute` 调用的 Service 方法，标注哪些需要包裹在显式 `BEGIN`/`COMMIT` 事务中
- [ ] 设计事务回滚验证：在 `settle_week()` 的第 N 条 ledger 写入后人为触发异常，断言前 N-1 条被回滚

### P-3: 冷启动状态恢复完整性

**现状**：所有持久状态存储在 SQLite `.db` 文件中。但以下运行时状态在重启后丢失：

| 状态 | 存储位置 | 冷启动后 |
|------|----------|----------|
| 打卡记录 | `checkins` 表 | 完整保留 |
| 对赌任务 | `bet_tasks` / `bet_configs` | 完整保留 |
| 设置项 | `settings` 表 | 完整保留 |
| EventBus 订阅关系 | 内存 | **丢失**（需重新订阅） |
| 当日旷工判定 | `checkins` 表（通过 status 字段） | 完整保留 |
| 当日未完成的自动签退 | 无持久化 | **丢失**（需重新触发 `auto_checkout`） |

**自查项**：
- [ ] 验证 Service 初始化时是否重新注册了所有必需的 EventBus 订阅（当前 `BetService.__init__` 注册了 `WEEK_CLOSED` 处理器——检查是否还有其他隐式依赖）
- [ ] 验证 `auto_checkout` 在冷启动后能否被正确触发（当前依赖 APP 前台调用 `mark_absent` 时级联触发——无独立的后台守护逻辑）

---

## 测试床验证思路

### T-1: 真实磁盘文件 30 天连续存取 + 冷启动注入

```python
# 核心思路
# 1. 使用真实磁盘路径（非 :memory:），模拟 30 天完整业务流
# 2. 每 10 天模拟一次"冷启动"：close_db() → 清空 EventBus → 重新 init_db() → 重新创建所有 Service
# 3. 断言冷启动前后状态完全一致
```

**步骤**：

1. 创建物理 `.db` 文件（`tempfile.mkstemp` 产生真实文件）
2. 运行 30 天混合业务流（打卡、请假、旷工、对赌任务创建/完成、结算）
3. 在第 10、20 天结束时：
   - 记录当前快照：所有表的行数、checkins 的 status 分布、ledger 的 amount 总和
   - 调用 `close_db()` 断开所有连接
   - 重新 `init_db(path)` + 重建所有 Service/Repo 实例
   - 断言快照完全一致
4. 第 30 天结束后，直接读取 SQLite 文件（绕过 ORM），用原始 SQL 断言数据完整性

**需要断言的快照字段**：
- `SELECT COUNT(*) FROM checkins` 记录数
- `SELECT COUNT(*) FROM ledger_entries` 记录数
- `SELECT status, COUNT(*) FROM checkins GROUP BY status` 状态分布
- `SELECT SUM(amount) FROM ledger_entries` 账本总额
- `SELECT COUNT(*) FROM bet_tasks WHERE is_completed=1` 已完成任务数

### T-2: 事务原子性崩溃注入

```python
# 核心思路：在 settle_week() 执行过程中模拟进程崩溃
# 1. 使用真实的 BEGIN/COMMIT 包裹（修复后）
# 2. 在写入第 2 条 ledger entry 后触发 KeyboardInterrupt 或 os._exit(1)
# 3. 重启后断言：0 条 ledger entry 被部分写入（全有或全无）
```

### T-3: WAL 文件残留验证

- [ ] 连续写操作后，断言 WAL 文件存在（`db_path + "-wal"`）
- [ ] 正常 `close_db()` 后，断言 WAL 文件被 checkpoint 合并（大小归零或文件消失）
- [ ] 异常崩溃后（不调用 `close_db()`），重启时断言 WAL 能通过 `PRAGMA wal_checkpoint` 恢复

---

## 交付合格线

- [ ] `python run_backend_persistence_test.py` 执行无 traceback 崩溃
- [ ] 30 天连续存取后，冷启动前后 5 项快照数据完全一致
- [ ] 事务原子性验证：中途崩溃后无部分写入的脏数据
- [ ] WAL 文件在正常关闭后正确清理，异常崩溃后可恢复
- [ ] 所有 Repository 方法均已标注事务边界（≥2 次写入的方法包裹在显式事务中）
- [ ] `busy_timeout` 已配置（建议 5000ms），`database is locked` 不再立即抛出
