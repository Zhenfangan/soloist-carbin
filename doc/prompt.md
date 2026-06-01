# Soloist Cabin Pro — Vibe Coding 主控 Prompt

你是一个**主控 Agent**，负责将 Soloist Cabin Pro 从零实现到完整的可运行工程。你不会离开这个对话，整个过程不需要人工参与。

---

## 1. 项目概述

**Soloist Cabin Pro** — 面向自媒体从业者的自律打卡 Android APP（Python + Kivy + KivyMD + SQLite + FastAPI 后端）。

### 技术栈

| 层 | 技术 |
|----|------|
| 前端 APP | Python 3.10+ / Kivy 2.3+ / KivyMD 1.2+ |
| 本地存储 | SQLite |
| 后端同步 | FastAPI + WebSocket |
| 测试 | pytest |
| 静态检查 | mypy (strict) + ruff |
| 模板引擎 | Jinja2 |

### 需求与设计文档

- 需求文档：[proposal.md](./proposal.md)
- 详细设计：[detailed-design.md](./detailed-design.md)
- 任务划分：[tasks/](./tasks/)

---

## 2. 模块体系（9 个模块）

| 编号 | 模块 | 职责 | 任务文件 |
|------|------|------|----------|
| M9 | 时间抽象层 + EventBus | 统一时间源 + 模块间事件通信 | [tasks/m9-clock.md](./tasks/m9-clock.md) |
| M6 | 设置模块 | 全部可配置参数 + 首次引导 | [tasks/m6-settings.md](./tasks/m6-settings.md) |
| M1 | 考勤模块 | 打卡/签退 + 出勤判定 + 请假 + 提醒 | [tasks/m1-checkin.md](./tasks/m1-checkin.md) |
| M2 | 奖惩模块 | 奖惩计算 + 对赌任务 + 男友承诺 + 账本 | [tasks/m2-penalty.md](./tasks/m2-penalty.md) |
| M4 | 拍摄日模块 | 拍摄日设定 + 复盘问卷 + 总结生成 | [tasks/m4-shooting.md](./tasks/m4-shooting.md) |
| M8 | 激励模块 | 连续出勤天数 + 通知栏卡片 | [tasks/m8-motivation.md](./tasks/m8-motivation.md) |
| M3 | 战报模块 | 手账长图生成 (HTML→截图) | [tasks/m3-report.md](./tasks/m3-report.md) |
| M5 | 历史模块 | 周/月/年三维度数据展示 | [tasks/m5-history.md](./tasks/m5-history.md) |
| M7 | 同步模块 | WebSocket 推送 + 云端备份恢复 + 检阅端 | [tasks/m7-sync.md](./tasks/m7-sync.md) |

### 模块依赖拓扑

```
M9 (基础设施) ──→ 所有模块
M6 (设置)    ──→ M1, M2, M4, M8
M1 (考勤)    ──→ M2, M3, M5, M8
M2 (奖惩)    ──→ M3, M5
M4 (拍摄日)  ──→ M3, M5
M3, M5       ──→ 无下游（只读消费者）
M7 (同步)    ──→ 依赖所有模块（最后实现）
```

---

## 3. 你（主控 Agent）的工作流程

### 阶段 0：搭建项目骨架

**由你亲自完成，不派生子 Agent。**

按顺序执行：

```
0.1  创建完整目录结构
0.2  编写 requirements.txt（Kivy, KivyMD, FastAPI, Jinja2, pytest, mypy, ruff 等）
0.3  创建 app/main.py（Kivy APP 入口，最小可运行骨架）
0.4  实现 M9 时间抽象层（Clock 抽象基类 + SystemClock + SimulatedClock + get_clock/set_clock 单例）
0.5  实现 EventBus（EventType 枚举 + subscribe/publish/unsubscribe）
0.6  创建数据库初始化模块（app/db.py，建表 SQL）
0.7  创建 Repository 基类（app/repositories/base.py，统一 SQLite 连接管理）
0.8  创建 app/utils/config.py（APP 配置常量）
0.9  添加 mypy.ini 和 ruff.toml 配置
```

**阶段 0 完成条件（缺一不可）：**

- `pytest` 在项目根目录运行，阶段 0 相关测试全部通过
- `mypy --strict app/` 零错误
- `ruff check app/` 零错误

**如果任一条件不通过，必须修复后重新自检，通过后方可进入阶段 1。**

---

### 阶段 1~9：逐模块实现

**通过派生子 Agent 完成。** 每个子 Agent 是独立上下文对话，遵循统一的执行模板（见第 4 节）。

#### 执行顺序与并行策略

```
阶段 1: M6 设置      （独立，最先）
阶段 2: M1 考勤      （依赖 M9+M6）
阶段 3: M2 奖惩 ─┬─→ 并行派发 3 个子 Agent
         M4 拍摄日 ─┤
         M8 激励   ─┘
阶段 4: M3 战报 ─┬─→ 并行派发 2 个子 Agent
         M5 历史 ─┘
阶段 5: M7 同步      （最后，依赖所有模块）
```

**规则：**
- 同阶段内的模块可以并行派发，因为它们之间无依赖或仅依赖已完成模块
- 每个子 Agent 完成后，你必须验证其交付物（见第 5 节），通过后才能标记该模块完成
- 一个子 Agent 失败时，修复它或重新派发，不可跳过

---

### 进度追踪

你维护两个进度维度：

**维度 1 — `doc/tasks/progress.md`**：模块级别的 checkbox，完成后打勾。
**维度 2 — 各 `doc/tasks/mX-*.md`**：子任务级别的 checkbox，子 Agent 完成后由你打勾。

**每个子 Agent 返回后，你必须：**
1. 检查其是否通过 pytest + mypy + ruff
2. 检查其是否完成了对应 task 文件中的所有子任务
3. 更新 `progress.md` 勾选对应模块
4. 更新对应的 `mX-*.md` 勾选所有子任务

---

## 4. 子 Agent 执行模板（分发给每个子 Agent）

向子 Agent 发出的 prompt 必须包含以下结构：

```
## 任务

实现 Soloist Cabin Pro 的 [模块名称]（[模块编号]）。

## 上下文

你是子 Agent，在 Soloist Cabin Pro 项目中实现 [模块名称]。
主 Agent 已完成项目骨架，以下是你可以依赖的已有代码：

### 项目目录结构
[当前完整的目录树]

### 已有基础设施
- app/utils/clock.py — Clock 抽象基类 + SystemClock + SimulatedClock + get_clock()/set_clock()
- app/services/event_bus.py — EventBus + EventType 枚举（含 subscribe/publish/unsubscribe）
- app/db.py — SQLite 数据库初始化 + get_db() 连接获取
- app/repositories/base.py — BaseRepo 基类（统一 SQLite 连接管理）
- app/utils/config.py — APP 配置常量
- app/main.py — Kivy APP 入口

### 依赖的已有模块接口
[列出该模块依赖的 Repo / Service 接口签名]

## 要求

1. 按照任务清单逐项实现（见 doc/tasks/[mX-*.md]）
2. 实现顺序：数据模型 → Repository → Service → UI 组件 → 测试
3. 完整 pytest 单元测试（Service + Repository 层全覆盖；UI 层用 Kivy headless (Config.set('graphics', 'backend', 'offscreen')) 覆盖关键交互路径，其余 UI 至少通过 mypy/ruff）
4. 通过 `mypy --strict app/` 和 `ruff check app/`
5. 所有时间获取必须用 `get_clock().now()`，禁止直接调用 `datetime.now()`
6. 模块间通信通过 EventBus 发布/订阅事件，禁止直接跨模块调用 Service
7. 模块间数据读取通过 Repository 接口，禁止直接访问其他模块的数据库表
8. Android 特定功能使用抽象接口（定义在 app/interfaces/），测试时 mock，真机运行时用 Plyer/pyjnius 实现

## 交付标准

任务完成后返回以下信息：
- 新增/修改的文件列表
- pytest 运行结果（必须全部通过）
- mypy 检查结果（必须零错误）
- ruff 检查结果（必须零错误）
- 剩余未完成的子任务（如有，需说明原因）
```

---

## 5. 质量门禁（适用于你和所有子 Agent）

### 必须通过的三道检查

```bash
# 1. 单元测试
pytest app/ server/ -v

# 2. 类型检查
mypy --strict app/ server/

# 3. 代码规范
ruff check app/ server/
```

**三者全部通过才视为完成。任一失败必须修复。**

### 测试覆盖率要求

| 层级 | 要求 |
|------|------|
| Repository | 每个方法至少一个测试用例 |
| Service | 每个公开方法至少一个测试用例，边界条件覆盖 |
| UI | Kivy headless 关键交互路径（按钮点击→Service 调用→状态更新） |
| 模型 | 数据类创建和字段访问测试 |

### 时间相关测试

所有涉及时间的测试必须使用 `SimulatedClock`：
```python
from app.utils.clock import SimulatedClock, set_clock

def test_something():
    clock = SimulatedClock()
    clock.set_date_and_time("2026-06-01", "08:55")
    set_clock(clock)
    # ... 测试逻辑 ...
    clock.advance(minutes=30)  # 快进时间
```

严禁在测试中使用 `time.sleep()` 等待真实时间流逝。

---

## 6. Android 抽象接口规范

Android 特有功能必须在 `app/interfaces/` 目录定义抽象接口：

```python
# app/interfaces/notifier.py
from abc import ABC, abstractmethod

class Notifier(ABC):
    """Android 通知抽象接口"""
    @abstractmethod
    def show_ongoing(self, title: str, content: str) -> None: ...
    @abstractmethod
    def send_reminder(self, title: str, content: str) -> None: ...
    @abstractmethod
    def cancel_all(self) -> None: ...

# app/interfaces/screenshotter.py
class Screenshotter(ABC):
    """WebView 截图抽象接口"""
    @abstractmethod
    def capture_html(self, html: str) -> str:  # 返回图片路径
        ...

# app/interfaces/alarm_scheduler.py
class AlarmScheduler(ABC):
    """系统闹钟抽象接口"""
    @abstractmethod
    def schedule(self, alarm_time: str, tag: str) -> None: ...
    @abstractmethod
    def cancel(self, tag: str) -> None: ...
    @abstractmethod
    def cancel_all(self) -> None: ...
```

- 测试时注入 mock 实现
- 生产实现放在 `app/interfaces/android/` 目录，通过 Plyer/pyjnius 调用 Android API
- 生产 App 启动时通过工厂函数选择具体实现

---

## 7. 文件组织规范

```
soloist-carbin/
├── app/
│   ├── main.py                  # Kivy APP 入口
│   ├── db.py                    # SQLite 初始化（建表）
│   ├── screens/                 # 各个页面
│   │   ├── main_screen.py
│   │   ├── history_screen.py
│   │   ├── ledger_screen.py
│   │   ├── bet_screen.py
│   │   ├── settings_screen.py
│   │   ├── report_screen.py
│   │   └── onboarding.py
│   ├── components/              # 可复用 UI 组件
│   │   ├── checkin_button.py
│   │   ├── attendance_status.py
│   │   ├── task_list.py
│   │   ├── week_view.py
│   │   ├── month_view.py
│   │   ├── year_view.py
│   │   └── shooting_reflection_dialog.py
│   ├── services/                # 业务逻辑层
│   │   ├── event_bus.py         # EventBus + EventType
│   │   ├── checkin_service.py
│   │   ├── penalty_service.py
│   │   ├── bet_service.py
│   │   ├── boyfriend_promise_service.py
│   │   ├── ledger_service.py
│   │   ├── report_service.py
│   │   ├── shooting_service.py
│   │   ├── history_service.py
│   │   ├── settings_service.py
│   │   ├── reminder_service.py
│   │   ├── motivation_service.py
│   │   └── sync_service.py
│   ├── repositories/            # 数据访问层
│   │   ├── base.py              # BaseRepo 基类
│   │   ├── checkin_repo.py
│   │   ├── ledger_repo.py
│   │   ├── bet_repo.py
│   │   ├── shooting_repo.py
│   │   ├── task_repo.py
│   │   ├── settings_repo.py
│   │   ├── streak_repo.py
│   │   └── sync_repo.py
│   ├── models/                  # 数据类定义
│   │   ├── checkin.py
│   │   ├── ledger.py
│   │   ├── report.py
│   │   ├── shooting.py
│   │   ├── history.py
│   │   ├── streak.py
│   │   └── task.py
│   ├── interfaces/              # Android 抽象接口
│   │   ├── __init__.py
│   │   ├── notifier.py
│   │   ├── screenshotter.py
│   │   ├── alarm_scheduler.py
│   │   └── android/             # Plyer/pyjnius 真机实现
│   │       ├── __init__.py
│   │       ├── android_notifier.py
│   │       ├── android_screenshotter.py
│   │       └── android_alarm_scheduler.py
│   ├── utils/
│   │   ├── clock.py             # Clock 抽象 + SystemClock + SimulatedClock
│   │   └── config.py            # 全局常量
│   ├── assets/                  # 静态资源
│   │   ├── templates/
│   │   │   ├── daily_report.html
│   │   │   └── shooting_report.html
│   │   ├── fonts/
│   │   └── images/
│   └── tests/                   # 单元测试
│       ├── __init__.py
│       ├── conftest.py          # 全局 fixtures（模拟时钟、内存数据库等）
│       ├── test_checkin_service.py
│       ├── test_penalty_service.py
│       ├── test_bet_service.py
│       ├── test_boyfriend_promise_service.py
│       ├── test_ledger_service.py
│       ├── test_report_service.py
│       ├── test_shooting_service.py
│       ├── test_history_service.py
│       ├── test_settings_service.py
│       ├── test_motivation_service.py
│       ├── test_sync_service.py
│       ├── test_clock.py
│       ├── test_event_bus.py
│       ├── test_checkin_repo.py
│       ├── test_ledger_repo.py
│       ├── test_bet_repo.py
│       ├── test_shooting_repo.py
│       ├── test_task_repo.py
│       ├── test_settings_repo.py
│       ├── test_streak_repo.py
│       └── test_ui/             # UI headless 测试
│           ├── __init__.py
│           ├── test_checkin_button.py
│           ├── test_attendance_status.py
│           └── test_main_screen.py
├── server/                      # FastAPI 后端（在 M7 阶段创建）
│   ├── main.py
│   ├── routes/
│   │   ├── sync_routes.py
│   │   └── review_routes.py
│   ├── services/
│   │   └── push_service.py
│   ├── models/
│   │   └── sync_models.py
│   ├── templates/
│   │   └── review.html
│   └── tests/
│       ├── test_sync_routes.py
│       └── test_push_service.py
├── doc/
├── requirements.txt
├── mypy.ini
├── ruff.toml
└── pytest.ini
```

---

## 8. 数据库表（db.py 中创建）

9 张表，DDL 详见 [detailed-design.md](./detailed-design.md) 第 3.2 节：

`checkins` / `ledger_entries` / `boyfriend_promises` / `bet_tasks` / `bet_configs` / `shooting_days` / `shooting_reflections` / `task_items` / `settings` / `attendance_streak`

---

## 9. 关键数据流

### 打卡 → 奖惩 → 战报 完整链路

```
用户点击签到
  → CheckinService.check_in(date, period)
    → CheckinRepo.upsert(checkin)
    → 判定状态（normal/late/early_leave/...）
    → EventBus.publish(CHECK_IN_COMPLETED, payload)
    → PenaltyService 订阅到 ATTENDANCE_JUDGED
      → calculate_daily(date)
      → LedgerRepo.insert(entry)

用户签退（最后一个时段）
  → CheckinService.check_out(date, period)
    → 判定 + 发布 CHECK_OUT_COMPLETED
    → 检查所有时段是否都完成 → 发布 DAY_FINISHED
      → BoyfriendPromiseService.check_fulfill(date, hours)
      → MotivationService.update_streak(date)
      → SyncService.push_event(DAY_FINISHED, payload)

次日 4:00 日切
  → 扫描未签退 → 自动补签退
  → 计算当日奖惩 → 生成战报
  → 发布 DAY_CLOSED
    → 判断是否周日 → 发布 WEEK_CLOSED
      → 全勤判定 + 对赌结算 + 统一写入账本
```

---

## 10. 开始执行

现在以主控 Agent 的身份开始：

**第一步：阅读 doc/proposal.md 和 doc/detailed-design.md，确认你已理解项目全貌。**

**第二步：执行阶段 0 — 搭建项目骨架。** 完成后运行 pytest + mypy + ruff 自检，全部通过后汇报结果。

**第三步：按阶段 1→5 的顺序派生子 Agent。** 每个子 Agent 交付后运行质量门禁，通过后更新进度文件。

进度文件位置：
- 总体进度：`doc/tasks/progress.md`
- 各模块详情：`doc/tasks/m1-checkin.md` ~ `doc/tasks/m9-clock.md`
