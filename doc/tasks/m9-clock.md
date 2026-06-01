# M9 — 时间抽象层 子任务

> 职责：统一时间源（Clock），支持系统时间和模拟时间切换

---

## 核心实现

- [ ] **9.1** 创建 `app/utils/clock.py`：`Clock` 抽象基类（`now()` / `today_str()` / `current_time_str()`）
- [ ] **9.2** 实现 `SystemClock`：封装 `datetime.now()`
- [ ] **9.3** 实现 `SimulatedClock`：`set_time()` / `set_date_and_time()` / `advance()` / `set_speed()` / `pause()` / `resume()`
- [ ] **9.4** 实现全局单例 `get_clock()` / `set_clock(clock)` 注入机制

## 集成触发

- [ ] **9.5** `SimulatedClock.advance()` 越过凌晨 4:00 时自动检查并触发 `DAY_CLOSED` 事件

## 事件总线

- [ ] **9.6** 创建 `app/services/event_bus.py`：`subscribe(event_type, handler)` / `publish(event_type, data)` / `unsubscribe(event_type, handler)`
- [ ] **9.7** 定义 `EventType` 枚举（全部 11 种事件类型）

## 测试面板

- [ ] **9.8** 设置页底部实现隐藏入口（连续点击版本号 5 次）
- [ ] **9.9** 创建时间模拟面板：日期选择器 + 时间滑块 + 快进按钮 + 倍速滑块 + 暂停/恢复 + 重置
- [ ] **9.10** 仅开发模式可用（Release 构建时禁用）

## 全局替换

- [ ] **9.11** 全局扫描替换直接 `datetime.now()` → `get_clock().now()`

## 测试

- [ ] **9.12** SystemClock / SimulatedClock 基本功能测试
- [ ] **9.13** 时间快进越过 4:00 触发 DAY_CLOSED 测试
- [ ] **9.14** EventBus 发布订阅正确性测试
