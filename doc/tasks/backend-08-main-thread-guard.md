# backend-08-main-thread-guard: 异步主线程守卫与耗时 I/O 阻塞审计

## 职责

审计所有 Service 公开方法中涉及磁盘 I/O、跨表联查、模板渲染、全量数据导入导出的同步调用路径。确保任何可能超过 Kivy 单帧预算（16ms）的操作，在接入 UI 层时必须通过异步线程或 `Clock.schedule_once` 错峰调度，严禁同步霸占主线程导致窗口"未响应"白屏。

## 自查核心痛点

### T-1: 全表扫描导出/导入 —— 同步阻塞的原子弹

**现状** (`app/repositories/sync_repo.py:27-51`)：

```python
def export_all_data(self) -> dict[str, list[dict[str, Any]]]:
    """导出所有表数据为 JSON 格式"""
    tables = [
        "checkins", "ledger_entries", "boyfriend_promises",
        "bet_tasks", "bet_configs", "shooting_days",
        "shooting_reflections", "task_items", "settings",
        "attendance_streak",
    ]
    for table in tables:
        rows = self._fetch_all(f"SELECT * FROM {table}")  # 10 次全表扫描
        result[table] = [dict(r) for r in rows]           # 逐行 dict 转换
    return result

def import_all_data(self, data) -> None:
    for table, rows in data.items():
        for row in rows:
            self._execute(                                 # 逐行 INSERT
                f"INSERT OR REPLACE INTO {table} ...",
                tuple(row.values()),
            )
```

`SyncService.backup_full()` 和 `restore_full()` 直接调用这两个方法。在积累数月的打卡记录后：
- `export_all_data()`：10 张表全表扫描 + 每行 `dict()` 转换——数百条记录时耗时在 **50~200ms** 级别
- `import_all_data()`：逐行 `INSERT OR REPLACE`——每条触发一次 `commit()`（当前架构下 `_execute` 自动 commit），数百条记录时耗时在 **500ms~2s** 级别

若 UI 层将 `backup_full()` 绑定到一个按钮点击回调，且该回调在 Kivy 主线程同步执行，将导致窗口冻结数秒。

**自查项**：
- [ ] 确认 `SyncRepo.export_all_data()` 和 `import_all_data()` 的所有调用路径——当前仅 `SyncService.backup_full()` / `restore_full()` 调用
- [ ] 确认 `import_all_data()` 的逐行 commit 策略——这在大量数据时是性能灾难（每个 `_execute` 触发一次 fsync），应包裹在单事务中批量写入

### T-2: 报表生成的多 Repo 联查 + Jinja2 模板渲染

**现状** (`app/services/report_service.py:146-229`)：

```python
def collect_data(self, date: str) -> ReportData:
    records = self._checkin_repo.get_all_by_date(date)      # SQL 查询 1
    entries = self._ledger_repo.get_by_date(date)           # SQL 查询 2
    promise = self._ledger_repo.get_promise(date)           # SQL 查询 3
    task_repo = TaskRepo()                                  # 临时 Repo 实例化
    completed_tasks = task_repo.get_completed(date)         # SQL 查询 4 + for 循环
    # ... 4 次 for 循环计算 hours/penalties ...
    return ReportData(...)

def generate_html(self, data: ReportData) -> str:
    template = SHOOTING_REPORT_TEMPLATE if data.is_shooting_day else DAILY_REPORT_TEMPLATE
    return template.render(data=data)  # Jinja2 模板渲染 (CPU)
```

`generate_and_save()` 串行调用 `collect_data()` + `generate_html()`：
- 4 次独立 SQL 查询 + 4 次 Python for 循环 + Jinja2 模板渲染
- 在积累数据后，预估耗时 **30~80ms**
- 若绑定到 UI 按钮回调（如"查看今日战报"），超过 16ms 帧预算 → 掉帧/卡顿

**自查项**：
- [ ] 确认 `ReportService.generate_and_save()` 的 UI 调用路径——当前是否有可能从 Kivy 主线程同步调用？（目前仅被 `_on_day_closed` 事件处理器调用，但未来 UI 层可能直接调用）
- [ ] 确认 `ReportService.__init__` 中创建的临时 `TaskRepo()` 实例的连接生命周期——每次 `collect_data()` 调用都创建新的 `TaskRepo()` 实例

### T-3: 所有 Service 方法的 I/O 强度分级

以下方法列表供全量审计：

| 方法 | I/O 操作 | 预估耗时 | 风险等级 |
|------|---------|----------|----------|
| `CheckinService.check_in()` | 1 次 upsert + 1~2 次 EventBus publish | <5ms | 低 |
| `CheckinService.check_out()` | 1 次 SELECT + 1 次 upsert + publish | <5ms | 低 |
| `CheckinService.mark_absent()` | 2 次 SELECT + 2 次 upsert + publish | <10ms | 低 |
| `CheckinService.get_today_status()` | 1 次 SELECT (all_by_date) + for 循环 | <5ms | 低 |
| `BetService.settle_week()` | 1 次 SELECT tasks + 1 次 SELECT config + N 次 INSERT + publish | <20ms | 中 |
| `BetService.get_week_summary()` | 2 次 SELECT | <5ms | 低 |
| `ReportService.generate_and_save()` | 4 次 SELECT + Jinja2 渲染 + publish | 30~80ms | **高** |
| `SyncService.backup_full()` | 10 次全表 SELECT + dict 转换 | 50~200ms | **极高** |
| `SyncService.restore_full()` | N 次 INSERT OR REPLACE | 500ms~2s | **极高** |
| `HistoryService.get_week_view()` | 1 次 SELECT (all_by_week) + for 循环 | <10ms | 低 |
| `HistoryService.get_month_view()` | 1 次 SELECT (all_by_month) + for 循环 | <15ms | 中 |

**自查项**：
- [ ] 对所有标记为"高"和"极高"的方法，确认其 UI 层调用路径是否存在同步阻塞风险
- [ ] 确认 Kivy 的 `Clock.schedule_once` 是否已建立错峰调度基础设施（当前 UI 层大量使用 `Clock.schedule_once(lambda: self._load_data(), 0)`——这是在主线程内错峰，而非异步线程。数据仍在主线程处理，仅延迟到下一帧）

### T-4: Kivy 主线程（Main Loop）的帧预算模型

Kivy 渲染管线以 60fps 为目标：
- 每帧预算：**16.67ms**
- 其中：输入处理 ~2ms、布局计算 ~2ms、Canvas 绘制 ~5-8ms → 留给应用逻辑 ≤ **5ms**
- 任何超过 16ms 的同步操作都会导致"掉帧"（下一帧被推迟）
- 连续多帧超时 → Windows 将窗口标记为"未响应"（系统级白屏，约 5 秒阈值）

当前架构中不存在任何 `threading.Thread` 或 `concurrent.futures` 的异步委托机制。所有 SQLite I/O 和 Jinja2 渲染均在调用线程同步执行。若调用线程是 Kivy 主线程（UI 事件回调），则必然阻塞渲染。

**自查项**：
- [ ] 确认 `app/` 目录下是否存在任何 `threading.Thread` 或 `ThreadPoolExecutor` 的使用（当前 Grep 结果为 0）
- [ ] 评估引入 `Clock.create_trigger` 作为 I/O 操作的错峰调度统一入口的可行性

---

## 架构走查/验证思路

### V-1: 静态审计 —— I/O 调用链图谱

1. 以 `app/services/*.py` 为入口，逐方法标注"是否包含 DB 写入"、"是否包含全表扫描"、"预估最大记录数下的耗时"
2. 以 `app/ui/screens/*.py` 为出口，Grep 所有 Service 方法调用点，标注"是否在 Kivy 事件回调中同步调用"
3. 生成 I/O 调用链图谱，标记所有"从 UI 主线程直达磁盘 I/O"的同步路径

### V-2: 帧时预算验证脚本

```python
# 核心思路：在模拟高数据量环境下，测量每个 Service 方法的壁钟耗时
# 1. 预填充 365 天 × 2 periods 的模拟打卡数据
# 2. 对每个高风险方法调用 10 次，取 p99 耗时
# 3. 断言无任何方法超过 100ms（紧急阈值）或 16ms（警告阈值）
```

**验证步骤**：
1. 向临时数据库注入 365 天完整打卡数据（≈730 条 checkin 记录 + 52 周 bet 数据）
2. 对 `export_all_data()` 计时 10 次，取 p99
3. 对 `import_all_data()` 计时 10 次，取 p99
4. 对 `generate_and_save()` 计时 10 次，取 p99
5. 输出耗时报告，与帧预算（16ms）对比

### V-3: 主线程阻塞模拟

```python
# 核心思路：在 Kivy 主线程中同步调用高风险方法，测量 UI 帧率下降

# 1. 启动 Kivy App（headless 或 真实窗口）
# 2. 在按钮回调中调用 export_all_data()
# 3. 使用 Clock.schedule_interval 监控帧率（记录每帧实际间隔）
# 4. 断言按钮回调期间帧间隔不超过 50ms（约 20fps）
```

### V-4: 异步委托架构设计验证

设计并验证以下异步调度模式：

```python
# 方案 A: Clock.schedule_once 错峰（仍在主线程，但非同步嵌套）
Clock.schedule_once(lambda dt: self._do_heavy_work())

# 方案 B: threading.Thread + Clock.schedule_once 回调（真正异步）
def _on_backup_click(self):
    def worker():
        result = sync_svc.backup_full()
        Clock.schedule_once(lambda dt: self._on_backup_done(result))
    threading.Thread(target=worker, daemon=True).start()

# 方案 C: 专用后台线程 + 队列（适合频繁 I/O）
# 维护一个 ThreadPoolExecutor(max_workers=1)，所有 I/O 任务投递到该线程
# 结果通过 Clock.schedule_once 回传主线程更新 UI
```

**验证**：
1. 对比三种方案在 365 天数据量下的 UI 帧率表现
2. 确认方案 B/C 中 SQLite 连接的线程安全性（当前 `check_same_thread=False` + WAL 模式已具备基础，但需确认并发写入隔离）

---

## 封关交付合格线

- [ ] 全项目 I/O 调用链图谱已完成，所有从 UI 主线程到磁盘 I/O 的同步路径已标注
- [ ] 365 天数据量下，`export_all_data()` p99 耗时已测量（目标 <200ms，当前架构预期 <500ms）
- [ ] 365 天数据量下，`import_all_data()` 的逐行 commit 已改为单事务批量写入（目标 <500ms，当前架构预期 >2000ms）
- [ ] 所有"高"和"极高"风险的 Service 方法已建立异步委托方案（方案 A/B/C 之一）
- [ ] 至少一处 UI 按钮回调已实现 `threading.Thread` + `Clock.schedule_once` 的异步委托示范
- [ ] `import_all_data()` 的性能优化已完成（事务包裹 + 批量 INSERT，消除逐行 commit）
- [ ] 所有现有 128 个单元测试无回归
