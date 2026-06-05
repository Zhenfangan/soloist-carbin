# backend-07-memory-leak-gate: EventBus 订阅与 Kivy 组件生命周期走查

## 职责

审计 EventBus 发布-订阅机制与 Kivy Widget 生命周期的耦合关系，确立前端组件的解耦闭环规范，防止已销毁 UI 组件的死引用在事件总线中累积，导致垃圾回收（GC）失效与长期内存泄漏。

## 自查核心痛点

### M-1: 全局单例 EventBus 持有强引用 —— 无人可被 GC

**现状** (`app/services/event_bus.py:44-46`)：

```python
# 全局单例，进程存活期间永不释放
_event_bus: EventBus | None = None

class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[EventType, list[EventHandler]] = {
            event_type: [] for event_type in EventType
        }
```

`_subscribers` 字典中的 `EventHandler` 是 `Callable`，Python 中可调用对象（实例方法、闭包）持有对 `self` 或捕获变量的强引用。全局单例 `_event_bus` 生命周期等同于进程，因此**任何注册到 EventBus 的 handler 所引用的对象，永远不会被 GC 回收**。

当 Kivy Widget 实例方法被注册为 handler 时：
- Widget 持有对父组件、子组件、纹理、Canvas 指令的引用链
- EventBus 持有 Widget 方法的强引用 → Widget 无法被释放
- 每次页面切换创建新 Widget → 旧 Widget "幽灵"残留 → 内存单调递增

虽然当前 `app/ui/` 目录下**没有任何组件直接订阅 EventBus**（经 Grep 确认），但以下 Service 层对象在 `__init__` 中订阅，同样存在生命周期问题：

| 订阅者 | 订阅事件 | 是否有 unsubscribe |
|--------|----------|-------------------|
| `BetService.__init__` | `WEEK_CLOSED` | 无 |
| `PenaltyService.__init__` | `ATTENDANCE_JUDGED`, `DAY_FINISHED` | 无 |
| `MotivationService.__init__` | `DAY_FINISHED` | 无 |
| `ReportService.__init__` | `DAY_CLOSED` | 无 |
| `BoyfriendPromiseService.__init__` | `DAY_FINISHED` | 无 |
| `SyncService.__init__` | 全部 12 种事件 | 无 |

若这些 Service 实例在测试中被重建（如冷启动模拟），旧实例的 handler 仍残留在 EventBus 中。

**自查项**：
- [ ] 确认所有 Service 类的实例化频率：是否每次请求创建新实例（工厂模式），还是全局单例（如 `get_event_bus()` 模式）？当前 CheckinService 等由调用方在 `__init__` 中手动 `new`——每次页面进入都可能创建新实例
- [ ] 确认 `SyncService` 订阅全部 12 种事件的设计意图——这是最激进的订阅者，每条事件都会触发 `push_event`，是否有必要全量订阅？

### M-2: Kivy Widget 生命周期与订阅时机的错位

Kivy Widget 的关键生命周期节点：

```
__init__() → 创建 Python 对象
on_kv_post() → KV 规则应用完毕，Widget 树构建完成
on_parent() → 被添加到父 Widget
on_enter() → ScreenManager 切换到该 Screen（仅 Screen 子类）
on_leave() → ScreenManager 离开该 Screen（仅 Screen 子类）
__del__() → Python 对象销毁（GC 触发，时机不确定）
```

如果在 `__init__` 中订阅 EventBus，此时 Widget 树尚未构建，子组件引用为空——handler 中若访问子组件属性必然崩溃。
如果在 `on_kv_post` 中订阅，Widget 离开屏幕时若不取消订阅，死引用泄漏。
`__del__` 不可靠——GC 触发时机不确定（Python 不保证立即析构），且循环引用会导致 `__del__` 永不调用。

**自查项**：
- [ ] 审查当前所有 Screen 类的 `__init__` 方法，确认是否有通过 EventBus 订阅事件的路径（当前 Grep 结果为无——标记为"尚未发生但架构级风险"）
- [ ] 确立规范：订阅必须在 `on_enter`/`on_kv_post` 中执行，取消订阅必须在 `on_leave`/`on_parent( None )` 中执行

### M-3: EventBus 无内省能力 —— 无法审计当前订阅状态

当前 `EventBus` 类没有提供任何查询接口：
- 无法列出当前所有订阅者
- 无法统计每个事件类型的订阅者数量
- 无法检测"幽灵订阅"（handler 所属对象已被销毁但引用仍在）

这使得内存泄漏的排查完全依赖代码审查，无法通过运行时监控发现。

**自查项**：
- [ ] 评估是否为 EventBus 添加 `list_subscribers(event_type)` 和 `subscriber_count(event_type)` 诊断接口
- [ ] 评估是否使用 `weakref.WeakMethod` 包装 handler，使 Widget 销毁后自动解除引用

---

## 架构走查/验证思路

### V-1: 生命周期规范声明与全局审计

1. 在 EventBus 模块文档中声明"订阅者生命周期契约"：
   - 任何订阅者必须在 `unsubscribe` 或 `clear` 调用后，方允许其所属对象进入析构路径
   - Service 层对象若为单例（全局唯一），可在 `__init__` 中永久订阅，无需 unsubscribe
   - UI 层对象必须在 `on_enter`/`on_kv_post` 订阅，在 `on_leave`/`on_parent(None)` 取消订阅
2. Grep 全项目 `subscribe(` 调用，逐一标记：
   - 订阅者类型（Service / Widget / 临时闭包）
   - 生命周期管理模式（单例永不释放 / 显式 unsubscribe / **无管理——风险**）

### V-2: 内存泄漏模拟与验证脚本

```python
# 核心思路
# 1. 创建模拟 Screen，在 on_enter 中订阅 EventBus
# 2. 模拟多次页面切换（创建→销毁→创建），每次创建新 Screen 实例
# 3. 统计 EventBus 中残留的订阅者数量
# 4. 若数量持续增长 → 内存泄漏确认
```

**验证步骤**：

1. 创建 `DummyScreen` 类，在 `on_enter` 中订阅 `CHECK_IN_COMPLETED` 事件
2. 模拟切换 100 次：创建 Screen → 触发 on_enter → 销毁 Screen（不调用 on_leave）
3. 断言 EventBus 中 `CHECK_IN_COMPLETED` 的订阅者数量不随切换次数增长
4. 修复后（在 on_leave 中 unsubscribe）重复验证，断言订阅数量恒定为 1（当前活跃的 Screen）

### V-3: WeakRef 防护层验证

若采用 `weakref.WeakMethod` 方案：
1. 在 Widget 实例被显式删除后（`del widget`），触发 GC（`gc.collect()`）
2. 断言 EventBus 中对应的 handler 自动解除引用
3. 断言 `publish()` 在遇到已死亡的 WeakMethod 时优雅跳过（不抛 `ReferenceError`）

---

## 封关交付合格线

- [ ] 全项目 Grep `subscribe(` 结果已归档，每个订阅点已标注生命周期管理模式
- [ ] EventBus 模块文档中包含"订阅者生命周期契约"说明
- [ ] 模拟 100 次页面切换后，EventBus 订阅数量不随切换次数增长
- [ ] UI 层存在至少一处示范性的 `on_enter` 订阅 + `on_leave` 取消订阅的闭环实现
- [ ] Service 层对象若非单例，已在 `close_db` / `shutdown` 路径中显式 unsubscribe
- [ ] 所有现有 128 个单元测试无回归
