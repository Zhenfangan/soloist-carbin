# backend-05-eventbus-sideeffects: 事件总线副作用与隔离审计

## 职责

审计 EventBus 广播机制的异常隔离能力、发布-订阅的环状依赖风险、以及同步广播模式对核心事务的级联影响。确保事件管道是"尽力而为"的旁路通知，而非核心业务的事务参与者。

## 自查核心痛点

### E-1: 同步广播无异常隔离——一个订阅者崩溃，全链断裂

**现状** (`app/services/event_bus.py:53-57`)：

```python
def publish(self, event_type, payload=None):
    data = payload or {}
    for handler in self._subscribers[event_type]:
        handler(event_type, data)  # 无 try/except 包裹
```

致命问题：
- 若 `handler` 抛出任何异常（包括 UI 组件因渲染错误导致的 `AttributeError`），异常会**沿调用栈向上传播到 Service 层**
- **后续的 handler 全部被跳过**——订阅顺序决定了谁先崩溃谁堵死管道
- Service 层的 `check_in()` / `check_out()` 等核心方法在 `publish()` 调用处抛出异常，导致**已完成的数据库写入被上层调用者的 try/except 吞掉或导致不一致**

**攻击链示例**：
```
check_in() → DB 写入成功 → publish(CHECK_IN_COMPLETED)
  → handler_A: BetService 更新任务进度 ✅
  → handler_B: UI 刷新组件 💥 AttributeError (组件未挂载)
  → handler_C: MotivationService 更新连胜 ❌ 永远不会执行
  → 异常向上传播 → check_in() 外层 Screen 代码 try/except 捕获
  → 用户看到 "签到失败" → 但数据库已写入成功！
```

**自查项**：
- [ ] 确认所有 `publish()` 调用点是否在数据库写入**之后**（当前是——检查是否有在写入之前 publish 的情况）
- [ ] 确认所有 handler 注册点：UI 组件是否直接订阅了 EventBus（当前需要 Grep `subscribe` 调用确认）
- [ ] 评估如果将 `publish()` 改为 fire-and-forget（用线程池异步广播），对 Kivy 主线程安全性的影响

### E-2: 环形发布-订阅死循环隐患

**现状** — 已识别的潜在环路：

```
路径 A: BetService._on_week_closed
  → settle_week()
    → publish(BET_SETTLED) → ??? → 可能触发新的 week_closed
    → publish(WEEK_SETTLED) → ??? → 可能触发新的 week_closed

路径 B: CheckinService.check_out()
  → DB 写入 → publish(DAY_FINISHED)
    → ??? → 如果某个 handler 调用了 checkin_svc.check_in()
      → publish(CHECK_IN_COMPLETED)
        → ??? → 可能再次触发 check_out
```

**自查项**：
- [ ] 绘制完整的事件发布-订阅有向图：以每个 `EventType` 为节点，以"发布者 → 订阅者 → 订阅者内部可能触发的发布"为边，检测环路
- [ ] 为每个 handler 添加递归深度计数器（`_publish_depth`），超过阈值（如 5）时记录日志并截断
- [ ] 检查 `_on_week_closed` 的订阅逻辑——它订阅 `WEEK_CLOSED` 然后调用 `settle_week()`，而 `settle_week()` 发布 `WEEK_SETTLED`。如果某处订阅 `WEEK_SETTLED` 并再次触发 week close，就会环路

### E-3: 事件 payload 的可变性污染

**现状**：

```python
def publish(self, event_type, payload=None):
    data = payload or {}
    for handler in self._subscribers[event_type]:
        handler(event_type, data)  # 所有 handler 共享同一个 dict 引用
```

如果 handler_A 修改了 `data` 字典（例如 `data["status"] = "modified"`），handler_B 收到的就是污染后的数据。这是 Python 可变对象在共享引用下的经典问题。

**自查项**：
- [ ] 确认是否有 handler 修改了传入的 payload（Grep handler 实现中对 payload 的写操作）
- [ ] 评估是否需要浅拷贝（`dict(payload)`）传递

---

## 测试床验证思路

### T-1: 订阅者崩溃隔离验证（Error Barrier）

```python
# 核心思路：注册一个故意抛异常的 handler，断言后续 handler 不被影响

def crashing_handler(event_type, payload):
    raise RuntimeError("模拟 UI 组件崩溃")

def normal_handler(event_type, payload):
    normal_handler.called = True

bus = EventBus()
bus.subscribe(EventType.CHECK_IN_COMPLETED, crashing_handler)
bus.subscribe(EventType.CHECK_IN_COMPLETED, normal_handler)

# 修复前：publish 直接抛异常，normal_handler 不会被调用
# 修复后：每个 handler 包裹在 try/except 中，normal_handler 正常执行
```

**验证步骤**：
1. 注册 3 个 handler：`[crashing, normal_1, normal_2]`
2. 调用 `publish()`
3. 断言 `normal_1.called == True` 且 `normal_2.called == True`
4. 断言 `publish()` 自身不抛异常
5. 断言 crashing handler 的异常被记录到日志（不静默吞掉）

### T-2: 环形发布死循环检测

```python
# 核心思路：构造一个已知的环，验证深度截断机制

bus = EventBus()

def loop_handler(event_type, payload):
    bus.publish(EventType.CHECK_IN_COMPLETED, {"depth": payload.get("depth", 0) + 1})

bus.subscribe(EventType.CHECK_IN_COMPLETED, loop_handler)

# 修复前：无限递归，栈溢出
# 修复后：深度截断（例如 max_depth=5），第 6 次 publish 被忽略并 log 警告
```

**验证步骤**：
1. 注册一个 handler 在收到事件后立即 publish 同类型事件
2. 调用 `publish()` 一次
3. 断言不会导致 `RecursionError` 或进程卡死
4. 断言截断日志被输出

### T-3: Service 层不受订阅者崩溃影响（集成验证）

```python
# 核心思路：在真实 Service 调用链中注入崩溃的 handler

# 1. 初始化完整环境（CheckinService + BetService + 临时 DB）
# 2. 注册一个崩溃的 handler 到 CHECK_IN_COMPLETED
# 3. 调用 checkin_svc.check_in()
# 4. 断言：签到记录成功写入 DB（不受 handler 崩溃影响）
# 5. 断言：check_in() 返回正常 CheckinResult（不被 handler 异常污染）
```

### T-4: Payload 可变性隔离验证

```python
# 注册两个 handler，第一个修改 payload，第二个读取原始值
# 断言第二个 handler 读到的值未被修改
```

---

## 交付合格线

- [ ] `python run_backend_eventbus_test.py` 执行无 traceback 崩溃
- [ ] 崩溃 handler 的异常不阻断同一事件的后续 handler 执行
- [ ] 崩溃 handler 的异常不向上传播到 Service 调用者
- [ ] 环形发布在深度阈值处被截断，输出警告日志
- [ ] Service 层核心方法（check_in / check_out / settle_week）在 handler 崩溃后仍正常返回
- [ ] 所有现有 128 个单元测试无回归
