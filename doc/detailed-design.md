# Soloist Cabin Pro — 详细设计文档

## 1. 概述

本文档是 [proposal.md](./proposal.md) 的详细设计，定义各模块的职责边界、接口、数据流和关键流程。

### 1.1 技术决策摘要

| 决策点 | 结论 |
|--------|------|
| 模块划分 | 8 个独立模块，通过 Repository 层解耦 |
| 战报生成 | HTML + CSS 模板 → Android WebView 截图 |
| 拍摄复盘 | 本地模板拼接 |
| 男友承诺 | 女友本地输入实物奖励，同步至后端 |
| 后端认证 | 预共享 Token（`Authorization: Bearer <token>`） |
| 日结算时间 | 次日凌晨 4:00 |
| 周结算时间 | 周一凌晨 4:00 |
| 忘记签退 | 自动按设定下班时间签退，标记 `auto_checkout` |
| 时间源 | Clock 抽象层，生产用系统时间，测试用模拟时间 |

### 1.2 模块列表

| 编号 | 模块 | 职责一句话 |
|------|------|-----------|
| M1 | 考勤模块 | 打卡动作 + 出勤状态判定 + 打卡提醒 |
| M2 | 奖惩模块 | 考勤奖惩计算 + 对赌任务结算 + 男友承诺 + 统一账本 |
| M3 | 战报模块 | 手账风格长图生成（HTML→截图） |
| M4 | 拍摄日模块 | 拍摄日切换 + 复盘问卷 + 文字总结 |
| M5 | 历史模块 | 周/月/年三维度数据展示 |
| M6 | 设置模块 | 全部可配置参数管理 + 首次引导流程 |
| M7 | 同步模块 | WebSocket 实时推送 + 云端备份恢复 |
| M8 | 激励模块 | 连续出勤天数 + 通知栏常驻卡片 |
| M9 | 时间抽象层 | 统一时间源 (Clock)，支持真实时间和模拟时间切换 |

---

## 2. 系统架构

### 2.1 分层架构

```
┌──────────────────────────────────────────────────────────┐
│                    UI 层 (Kivy/KivyMD)                      │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐  │
│  │M1 打卡 │ │M3 战报 │ │M4 拍摄 │ │M5 历史 │ │M6 设置 │  │
│  │  页面  │ │  页面  │ │  页面  │ │  页面  │ │  页面  │  │
│  └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘  │
├──────┼─────────┼─────────┼─────────┼─────────┼──────────┤
│      │    服务层 (Service) — 各模块业务逻辑              │
│  ┌───┴────┐ ┌───┴────┐ ┌───┴────┐ ┌───┴────┐             │
│  │M1 考勤 │ │M2 奖惩 │ │M4 拍摄 │ │M8 激励 │             │
│  │Service │ │Service │ │Service │ │Service │             │
│  └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘             │
│      │          │          │          │                    │
│  ┌───┴──────────┴──────────┴──────────┴────┐              │
│  │         M7 同步 Service                  │              │
│  └──────────────────┬──────────────────────┘              │
├─────────────────────┼─────────────────────────────────────┤
│     基础设施层                                               │
│  ┌──────────────────┴──────────────────────┐              │
│  │  M9 Clock (get_clock) — 统一时间源       │              │
│  ├─────────────────────────────────────────┤              │
│  │  EventBus — 模块间事件通信               │              │
│  └─────────────────────────────────────────┘              │
├───────────────────────────────────────────────────────────┤
│     数据访问层 (Repository)                                │
│  ┌──────────────────────────────────────────┐             │
│  │   Repository: checkin / ledger / bet     │             │
│  │   / settings / shooting / task / sync    │             │
│  └──────────────────┬──────────────────────┘              │
├─────────────────────┼─────────────────────────────────────┤
│     存储层                                                 │
│  ┌──────────────────┴──────────────────────┐              │
│  │         SQLite (本地)                    │              │
│  └─────────────────────────────────────────┘              │
└──────────────────────────────────────────────────────────┘
```

### 2.2 模块间交互原则

- 模块间**不直接调用对方的 Service 方法**
- 模块 A 消费模块 B 的数据 → 通过 Repository 读取
- 模块 A 触发模块 B 的行为 → 通过**事件总线 (EventBus)** 发布事件，模块 B 订阅
- 示例：考勤模块打卡完成 → 发布 `CheckInCompletedEvent` → 奖惩模块订阅并计算奖惩

### 2.3 事件总线 (EventBus)

位于 `app/services/event_bus.py`，提供轻量级发布-订阅机制：

```python
# 事件类型枚举
class EventType(Enum):
    CHECK_IN_COMPLETED = "check_in_completed"        # 打卡完成
    CHECK_OUT_COMPLETED = "check_out_completed"      # 签退完成
    ATTENDANCE_JUDGED = "attendance_judged"           # 出勤判定完成
    DAY_FINISHED = "day_finished"                     # 一天工作结束（最后签退）
    DAY_CLOSED = "day_closed"                         # 日切完成（4:00 结算，数据封存）
    WEEK_CLOSED = "week_closed"                       # 周切完成（周一 4:00 结算）
    SHOOTING_DAY_SET = "shooting_day_set"             # 拍摄日设定
    BET_SETTLED = "bet_settled"                       # 对赌结算完成
    REPORT_GENERATED = "report_generated"             # 战报生成完成
    SETTINGS_CHANGED = "settings_changed"             # 设置参数变更
    WEEK_SETTLED = "week_settled"                     # 周结算完成
```

### 2.4 日切与周结算

系统在每天凌晨 4:00 执行日切，处理前一天的数据封存。

#### 日切流程（每天 4:00）

```
触发方式: APP 启动时检查 / 4:00 AlarmManager 定时触发
处理日期: 前一日 (昨天)

1. 扫描前一日所有未签退的时段
      │
2. 对每个未签退时段:
      ├── 有签到无签退 → 自动签退，时间 = 设定下班时间，标记 auto_checkout
      ├── 无签到无签退 (工作日) → 标记为旷工 (absent)
      └── 无签到无签退 + 已请假 → 保持 leave 状态
      │
3. 所有时段状态写定后 → 数据封存（状态不可再修改）
      │
4. 计算当日奖惩 (调用 M2)
      │
5. 生成战报 (调用 M3)
      │
6. 触发 DAY_CLOSED 事件
      │
7. 启动新一天的调度（提醒、打卡重置等）
```

#### 周结算流程（周一 4:00）

```
触发方式: DAY_CLOSED 中判断昨日是否为周日
处理周期: 上一周 (周一～周日)

1. 确认上周 7 天全部已封存（未封存的先执行日切）
      │
2. 全勤判定 (调用 M2.PenaltyService)
      │
3. 对赌结算 (调用 M2.BetService)
      │
4. 统一写入账本流水
      │
5. 触发 WEEK_CLOSED 事件
```

#### 4:00 触发的实现方式

1. **APP 启动时检查**：每次 APP 打开/回到前台，检查上一个 4:00 是否已执行过日切，未执行则补执行
2. **AlarmManager 定时**：通过 Android AlarmManager 注册 4:00 闹钟，准时触发（APP 在后台也能收到）
3. 两种机制互补，确保日切不遗漏

#### auto_checkout 标记

在 `checkins` 表增加字段：

```sql
ALTER TABLE checkins ADD COLUMN checkout_type TEXT DEFAULT 'manual';
-- 'manual': 用户手动签退
-- 'auto': 系统自动签退 (忘记签退时)
```

战报展示时，`auto` 类型的签退时间旁显示 `（自动）`，提醒用户注意。

---

### 2.5 时间抽象层 (Clock)

所有模块**禁止直接调用 `datetime.now()`**，统一通过 Clock 接口获取当前时间。这使得测试时可以注入模拟时间，实现时间旅行和加速。

#### 接口定义

```python
# app/utils/clock.py

from abc import ABC, abstractmethod
from datetime import datetime

class Clock(ABC):
    """时间源抽象接口"""

    @abstractmethod
    def now(self) -> datetime:
        """返回当前时间"""
        ...

    @abstractmethod
    def today_str(self) -> str:
        """返回今天日期 YYYY-MM-DD"""
        ...

    @abstractmethod
    def current_time_str(self) -> str:
        """返回当前时间 HH:MM:SS"""
        ...


class SystemClock(Clock):
    """生产环境：封装系统真实时间"""

    def now(self) -> datetime:
        return datetime.now()

    def today_str(self) -> str:
        return self.now().strftime("%Y-%m-%d")

    def current_time_str(self) -> str:
        return self.now().strftime("%H:%M:%S")


class SimulatedClock(Clock):
    """测试环境：可控制的时间"""

    def __init__(self, start_time: datetime = None):
        self._time = start_time or datetime.now()
        self._speed = 1.0       # 时间倍速 (1=正常, 60=一分钟过一小时)
        self._paused = False

    def now(self) -> datetime:
        return self._time

    def today_str(self) -> str:
        return self._time.strftime("%Y-%m-%d")

    def current_time_str(self) -> str:
        return self._time.strftime("%H:%M:%S")

    # --- 控制方法 ---
    def set_time(self, dt: datetime) -> None:
        """设为指定时间"""
        self._time = dt

    def set_date_and_time(self, date_str: str, time_str: str) -> None:
        """快捷设时间 set_date_and_time('2026-06-01', '08:55')"""
        self._time = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")

    def advance(self, **kwargs) -> None:
        """快进时间 advance(minutes=30) 或 advance(hours=2, minutes=15)"""
        from datetime import timedelta
        self._time += timedelta(**kwargs)

    def set_speed(self, multiplier: float) -> None:
        """设置时间倍速 60 = 1 分钟过 1 小时"""
        self._speed = multiplier

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False
```

#### 注入方式

Clock 实例在 APP 启动时创建，通过**全局单例**注入到所有 Service：

```python
# app/utils/clock.py

_clock: Clock = None

def get_clock() -> Clock:
    """全局时钟获取器"""
    global _clock
    if _clock is None:
        _clock = SystemClock()
    return _clock

def set_clock(clock: Clock) -> None:
    """注入时钟 (测试时使用)"""
    global _clock
    _clock = clock
```

各模块中使用：

```python
# 不用: from datetime import datetime; datetime.now()
# 改用:
from app.utils.clock import get_clock

clock = get_clock()
now = clock.now()
today = clock.today_str()
```

#### 对日切结算的影响

SimulatedClock 在时间推进越过 4:00 时，主动检查并触发 `DAY_CLOSED` 事件，确保自动化测试可以覆盖完整日切流程。

#### 测试面板 (开发者工具)

在设置页面底部增加**隐藏入口**（连续点击版本号 5 次），进入时间模拟面板：

| 控件 | 功能 |
|------|------|
| 日期选择器 | 设定模拟日期 |
| 时间滑块 | 设定模拟时间 (00:00 ~ 23:59) |
| 快进按钮 | +5 分钟 / +1 小时 / +1 天 / +1 周 |
| 倍速滑块 | 1× / 10× / 60× / 600× |
| 暂停/恢复 | 暂停时间推进 |
| 重置 | 恢复为系统真实时间 |

测试面板仅在**开发模式**下可用（通过构建配置控制，Release APK 中禁用）。

---

## 3. 数据层设计

### 3.1 Repository 模式

所有数据访问通过 Repository 类进行，每个 Repository 对应一组相关数据表。Service 层通过构造函数注入 Repository 实例，便于单元测试时 Mock。

```
app/
├── repositories/
│   ├── checkin_repo.py      # 打卡记录 CRUD
│   ├── ledger_repo.py       # 账本流水 CRUD
│   ├── bet_repo.py          # 对赌任务 CRUD
│   ├── shooting_repo.py     # 拍摄日 + 复盘 CRUD
│   ├── settings_repo.py     # 设置参数读写
│   ├── task_repo.py         # 工作任务清单 CRUD
│   └── sync_repo.py         # 同步状态记录
```

### 3.2 数据库表设计

```sql
-- 打卡记录表
CREATE TABLE checkins (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    checkin_date  TEXT NOT NULL,          -- 日期 YYYY-MM-DD
    period        TEXT NOT NULL,          -- 时段: morning / afternoon / night
    checkin_time  TEXT,                   -- 签到时间 HH:MM:SS
    checkout_time TEXT,                   -- 签退时间 HH:MM:SS
    checkout_type TEXT DEFAULT 'manual',  -- 签退方式: manual / auto
    status        TEXT,                   -- 判定状态 (见 3.3)
    is_shooting   INTEGER DEFAULT 0,      -- 是否拍摄日
    created_at    TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at    TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(checkin_date, period)
);

-- 账本流水表
CREATE TABLE ledger_entries (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_date    TEXT NOT NULL,          -- 日期 YYYY-MM-DD
    week_start    TEXT,                   -- 所属周起始日期 YYYY-MM-DD (周一)
    type          TEXT NOT NULL,          -- 类型: late / early_leave / absent / full_attendance_bonus
                                          --      / boyfriend_promise / bet_reward / bet_penalty
                                          --      / bet_extra / shooting_reward
    amount        REAL NOT NULL,          -- 金额 (正=收入, 负=支出)
    description   TEXT,                   -- 描述 (如 "上午迟到 5 分钟")
    reward_item   TEXT,                   -- 实物奖励描述 (仅 boyfriend_promise) 如 "一杯奶茶"
    reward_qty    INTEGER DEFAULT 1,      -- 实物奖励数量
    fulfilled     INTEGER DEFAULT 0,      -- 是否已兑现 (实物奖励)
    source_id     INTEGER,               -- 来源记录 ID (关联 checkins.id 等)
    created_at    TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 男友承诺表
CREATE TABLE boyfriend_promises (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    promise_date  TEXT NOT NULL UNIQUE,   -- 日期 YYYY-MM-DD
    reward_desc   TEXT NOT NULL,          -- 奖励描述 如 "一杯奶茶"
    reward_qty    INTEGER DEFAULT 1,      -- 数量
    fulfilled     INTEGER DEFAULT 0,      -- 是否触发 (总工作时长 >= 门槛)
    created_at    TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 对赌任务表
CREATE TABLE bet_tasks (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    week_start    TEXT NOT NULL,          -- 周起始日期 YYYY-MM-DD (周一)
    task_desc     TEXT NOT NULL,          -- 任务描述
    is_completed  INTEGER DEFAULT 0,      -- 是否完成
    is_extra      INTEGER DEFAULT 0,      -- 是否超额任务
    created_at    TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 对赌配置表 (每周一份)
CREATE TABLE bet_configs (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    week_start        TEXT NOT NULL UNIQUE,  -- 周起始日期
    base_reward       REAL NOT NULL,         -- 完成奖励金额
    extra_reward      REAL NOT NULL,         -- 超额单任务奖励
    penalty           REAL NOT NULL,         -- 未完成惩罚金额
    status            TEXT DEFAULT 'active', -- active / settled
    created_at        TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 拍摄日记录表
CREATE TABLE shooting_days (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    shoot_date    TEXT NOT NULL UNIQUE,   -- 日期 YYYY-MM-DD
    reward_desc   TEXT,                   -- 拍摄奖励描述 (非金额)
    status        TEXT DEFAULT 'active',  -- active / completed
    created_at    TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 拍摄复盘表
CREATE TABLE shooting_reflections (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    shoot_date      TEXT NOT NULL UNIQUE,    -- 日期 YYYY-MM-DD
    content         TEXT,                    -- 拍摄内容
    location        TEXT,                    -- 拍摄地点
    was_smooth      TEXT,                    -- 是否顺利: smooth / normal / rough
    thoughts        TEXT,                    -- 感想
    summary         TEXT,                    -- 自动生成的文字总结
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 工作任务清单表
CREATE TABLE task_items (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    task_date     TEXT NOT NULL,          -- 日期 YYYY-MM-DD
    content       TEXT NOT NULL,          -- 任务内容
    is_completed  INTEGER DEFAULT 0,      -- 是否完成
    sort_order    INTEGER DEFAULT 0,      -- 排序
    created_at    TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 设置参数表 (键值对)
CREATE TABLE settings (
    key           TEXT PRIMARY KEY,
    value         TEXT NOT NULL,
    updated_at    TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 连续出勤记录表
CREATE TABLE attendance_streak (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    current_streak    INTEGER DEFAULT 0,       -- 当前连续天数
    last_checkin_date TEXT,                     -- 最后打卡日期
    updated_at        TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### 3.3 出勤状态枚举

| 状态值 | 含义 | 判定条件 |
|--------|------|---------|
| `pending` | 待判定 | 尚未打卡 |
| `normal` | 正常 | 设定时间之前打卡 / 设定时间之后签退 |
| `late` | 迟到 | 晚于设定上班时间打卡 |
| `early_leave` | 早退 | 早于设定下班时间签退 |
| `absent_morning` | 旷工(上午) | 晚于设定时间 1 小时未打卡 |
| `absent_afternoon` | 旷工(下午) | 晚于设定时间 1.5 小时未打卡 |
| `leave` | 请假 | 打卡窗口期手动请假 |
| `shooting` | 拍摄日 | 当天为拍摄日 |

---

## 4. 模块详细设计

### 4.1 M1 — 考勤模块

#### 4.1.1 职责边界

- **管**：打卡动作（签到/签退）、出勤状态判定、请假逻辑、打卡提醒调度
- **不管**：判定结果怎么罚款（那是 M2 的事）、判定结果怎么展示（那是 M5 的事）

#### 4.1.2 文件结构

```
app/
├── services/
│   ├── checkin_service.py       # 打卡业务逻辑
│   └── reminder_service.py      # 提醒调度
├── repositories/
│   └── checkin_repo.py          # 打卡数据 CRUD
├── components/
│   ├── checkin_button.py        # 打卡按钮组件
│   ├── attendance_status.py     # 出勤状态展示组件（含请假按钮）
│   └── task_list.py             # 工作任务清单组件 (3.5)
```

#### 4.1.3 核心接口

```python
# checkin_service.py

class CheckinService:
    def __init__(self, checkin_repo: CheckinRepo, settings_repo: SettingsRepo):
        ...

    # --- 打卡动作 ---
    def check_in(self, date: str, period: str) -> CheckinResult:
        """
        执行签到。
        period: 'morning' | 'afternoon' | 'night'
        返回: CheckinResult (包含打卡时间 + 判定状态)
        触发事件: EventType.CHECK_IN_COMPLETED
        """

    def check_out(self, date: str, period: str) -> CheckinResult:
        """
        执行签退。
        触发事件:
          - EventType.CHECK_OUT_COMPLETED
          - EventType.DAY_FINISHED (当天所有时段都签退完毕时)
        """

    # --- 请假 ---
    def get_leave_options(self, date: str, current_time: str) -> list[str]:
        """
        返回当前可选的请假范围: ['morning'] / ['afternoon'] / ['morning','afternoon','all_day'] / []
        规则:
          - 上午打卡时间之前: morning / afternoon / all_day
          - 上午签退后、下午打卡前: afternoon
          - 其他时间: 不允许 (返回 [])
        """

    def apply_leave(self, date: str, scope: str) -> CheckinResult:
        """
        scope: 'morning' | 'afternoon' | 'all_day'
        """

    # --- 状态查询 ---
    def get_today_status(self, date: str) -> dict:
        """返回今天各时段的状态快照，主界面使用"""

    # --- 提醒 ---
    def schedule_reminders(self) -> None:
        """根据设置中的时间参数，调度明天的四个提醒时间点"""
```

```python
# checkin_repo.py

class CheckinRepo:
    def get_by_date_period(self, date: str, period: str) -> Optional[Checkin]:
        ...
    def upsert(self, checkin: Checkin) -> Checkin:
        ...
    def get_all_by_date(self, date: str) -> list[Checkin]:
        ...
    def get_all_by_week(self, week_start: str) -> list[Checkin]:
        ...
    def get_all_by_month(self, year: int, month: int) -> list[Checkin]:
        ...
```

#### 4.1.4 状态判定流程图

```
打卡/签退触发
      │
      ▼
┌─────────────┐   是    ┌──────────┐
│ 是拍摄日？   │───────▶│ 跳过判定  │
└──────┬──────┘         └──────────┘
       │ 否
       ▼
┌─────────────┐   是   ┌───────────┐
│ 已申请请假？ │──────▶│ status =  │
└──────┬──────┘       │ 'leave'   │
       │ 否           └───────────┘
       ▼
┌─────────────────┐
│ 对比设定时间     │
│ 签到: < 设定 → normal, >= 设定 → late
│ 签退: >= 设定 → normal, < 设定 → early_leave
└─────────────────┘
       │
       ▼
   返回 CheckinResult(status, time, ...)
       │
       ▼
   发布 ATTENDANCE_JUDGED 事件
```

#### 4.1.5 提醒调度

```python
# reminder_service.py

class ReminderService:
    """
    在 APP 启动时调用 schedule_all()，计算今天/明天的提醒时间，
    使用 Android AlarmManager (通过 Plyer 或 pyjnius) 设置系统闹钟。

    四个提醒时间点:
      - 上午上班前 5 分钟
      - 上午下班时间 (到点提醒签退)
      - 下午上班前 5 分钟
      - 下午下班时间 (到点提醒签退)
    """
    def schedule_all(self) -> None: ...
    def cancel_all(self) -> None: ...
```

#### 4.1.6 旷工判定

采用**打开时补判 + 4:00 兜底**策略：

- 每次 APP 打开/回到前台时，检查当日各时段
- 若某时段已过判定窗口（上午 +1h，下午 +1.5h）且无打卡记录且无请假 → 标记为旷工
- 若当日始终未打开 APP，则在次日 4:00 日切时统一补判

#### 4.1.7 忘记签退处理

- 日切时扫描昨日未签退时段：有签到但无签退 → 自动签退
- 签退时间 = 该时段设定的下班时间
- 签退方式标记为 `auto`
- 工时按实际上班打卡时间到设定下班时间计算
- 战报上显示"（自动签退）"，不做额外惩罚

#### 4.1.8 测试要点

| 测试场景 | 输入 | 预期输出 |
|---------|------|---------|
| 准时上班打卡 | 08:55 签到，设定 09:00 | status=normal |
| 迟到打卡 | 09:10 签到，设定 09:00 | status=late |
| 早退签退 | 17:30 签退，设定 18:00 | status=early_leave |
| 上午请假 | 08:00 请假 scope=morning | 上午 status=leave，下午正常 |
| 全天请假 | 08:00 请假 scope=all_day | 上下午均 leave |
| 下午请假非窗口期 | 12:30 请假 scope=morning | 抛出异常或忽略 |
| 旷工补判 | 10:05 APP启动，上午无打卡 | status=absent_morning |
| 拍摄日跳过判定 | 拍摄日签到 | status=shooting |

| 忘记签退自动处理 | 有签到无签退，4:00 日切 | checkin_time=09:00, checkout=18:00(auto), 工时=9h |
| 全天无打卡旷工 | 工作日全天无打卡无请假，4:00 日切 | status=absent |

---

#### 4.2.1 职责边界

- **管**：迟到/早退/旷工罚款计算、全勤奖励计算、男友承诺管理、对赌任务 CRUD 及结算、统一账本查询
- **不管**：出勤数据从哪来（读 M1 的 Repository）、战报怎么展示账本（那是 M3 的事）、历史怎么展示（那是 M5 的事）

#### 4.2.2 文件结构

```
app/
├── services/
│   ├── penalty_service.py       # 考勤奖惩计算
│   ├── boyfriend_promise_service.py  # 男友承诺管理
│   ├── bet_service.py           # 对赌任务 + 结算
│   └── ledger_service.py        # 统一账本查询 (只读)
├── repositories/
│   ├── ledger_repo.py           # 账本流水 CRUD
│   └── bet_repo.py              # 对赌数据 CRUD
```

#### 4.2.3 核心接口

```python
# penalty_service.py

class PenaltyService:
    def __init__(self, checkin_repo: CheckinRepo, ledger_repo: LedgerRepo, settings_repo: SettingsRepo):
        ...

    def calculate_daily(self, date: str) -> list[LedgerEntry]:
        """
        根据当天出勤判定结果计算奖惩流水。
        消费 M1 的 checkin 数据 (通过 CheckinRepo 读取)。
        订阅: EventType.ATTENDANCE_JUDGED, EventType.DAY_FINISHED
        """

    def calculate_weekly_full_attendance(self, week_start: str) -> Optional[LedgerEntry]:
        """
        计算全勤奖励。需满足: 本周无迟到/早退/旷工/请假(上午/下午/全天)。
        仅在周日最后签退后触发。
        """
```

```python
# boyfriend_promise_service.py

class BoyfriendPromiseService:
    def __init__(self, ledger_repo: LedgerRepo, settings_repo: SettingsRepo):
        ...

    def set_promise(self, date: str, reward_desc: str, reward_qty: int = 1) -> BoyfriendPromise:
        """
        每天上午第一次打卡后调用，弹框让女友输入。
        reward_desc 如 "一杯奶茶", "一顿火锅"
        触发事件: EventType.PROMISE_SET
        """

    def check_fulfill(self, date: str, total_work_hours: float) -> bool:
        """
        检测工作时长是否达标 (>= 门槛)，达标则:
          1. 标记 fulfilled = 1
          2. 生成 LedgerEntry (type=boyfriend_promise)
        订阅: EventType.DAY_FINISHED
        """

    def get_today_promise(self, date: str) -> Optional[BoyfriendPromise]:
        """查询当天的承诺，主界面长期展示用"""
```

```python
# bet_service.py

class BetService:
    def __init__(self, bet_repo: BetRepo, ledger_repo: LedgerRepo, settings_repo: SettingsRepo):
        ...

    # --- 任务管理 ---
    def create_task(self, week_start: str, task_desc: str) -> BetTask:
        ...

    def complete_task(self, task_id: int) -> BetTask:
        ...

    def delete_task(self, task_id: int) -> None:
        ...

    def set_week_config(self, week_start: str, base_reward: float,
                        extra_reward: float, penalty: float) -> BetConfig:
        ...

    # --- 结算 ---
    def settle_week(self, week_start: str) -> WeeklySettlementResult:
        """
        周日触发 (或手动触发)。
        返回: {
            tasks: [...],
            completed_count: int,
            extra_count: int,
            total_reward: float,   # 基础奖励 + 超额奖励
            total_penalty: float,  # 未完成的惩罚
            net: float,            # 净额
            ledger_entries: [...]  # 生成的账本流水
        }
        触发事件: EventType.BET_SETTLED, EventType.WEEK_SETTLED
        """

    def get_week_summary(self, week_start: str) -> dict:
        ...
```

```python
# ledger_service.py

class LedgerService:
    """统一账本查询（只读），供 M3 战报和 M5 历史使用"""

    def __init__(self, ledger_repo: LedgerRepo):
        ...

    def get_daily_summary(self, date: str) -> dict:
        """返回单日汇总: 各类型金额明细 + 总额"""

    def get_weekly_summary(self, week_start: str) -> dict:
        """返回单周汇总: 每天金额 + 总额"""

    def get_monthly_summary(self, year: int, month: int) -> dict:
        """返回单月汇总: 每周金额 + 总额"""

    def get_yearly_summary(self, year: int) -> dict:
        """返回年度汇总: 各月统计"""
```

#### 4.2.4 周结算统一入口

每周日最后签退后（或手动触发），执行顺序：

```
1. PenaltyService.calculate_weekly_full_attendance(week_start)
       │
2. BoyfriendPromiseService 检测本周每日承诺兑现情况（未达标的不生成流水）
       │
3. BetService.settle_week(week_start)
       │
       ▼
4. 所有 LedgerEntry → 写入 ledger_entries 表
       │
       ▼
5. 发布 EventType.WEEK_SETTLED
```

#### 4.2.5 测试要点

| 测试场景 | 输入 | 预期输出 |
|---------|------|---------|
| 迟到罚款 | status=late, 罚款设定=10 | LedgerEntry(type=late, amount=-10) |
| 全勤奖励 | 一周全部 normal, 奖励=100 | LedgerEntry(type=full_attendance_bonus, amount=+100) |
| 请假不罚款 | status=leave | 无罚款流水 |
| 男友承诺达标 | 工作 8.5h, 门槛 8h | fulfilled=1, LedgerEntry 生成 |
| 男友承诺未达标 | 工作 6h, 门槛 8h | 不触发 |
| 对赌全部完成 | 3/3 任务完成 | total_reward = base_reward |
| 对赌超额 | 5/3 任务完成, 2 个超额 | total_reward = base + 2*extra |
| 对赌未完成 | 1/3 任务完成 | total_penalty = penalty |
| 周结算汇总 | 一周混合场景 | 各条流水总额正确 |

---

### 4.3 M3 — 战报模块

#### 4.3.1 职责边界

- **管**：从其他模块收集当天数据 → HTML 模板渲染 → WebView 截图生成长图 → 保存到相册
- **不管**：数据从哪来、数据怎么算（只读消费）

#### 4.3.2 技术方案

```
JSON 数据 → Jinja2 HTML 模板 → Android WebView 渲染 → 截图 PNG → 相册
```

HTML 模板位于 `app/assets/templates/daily_report.html`，包含手账拼贴风装饰元素（贴纸 SVG、胶带 CSS 效果、手写字体）。

#### 4.3.3 文件结构

```
app/
├── services/
│   └── report_service.py        # 战报生成逻辑
├── assets/
│   ├── templates/
│   │   ├── daily_report.html    # 普通办公日战报模板
│   │   └── shooting_report.html # 拍摄日战报模板
│   ├── fonts/
│   │   └── handwriting.ttf      # 手写字体
│   └── images/
│       ├── sticker_*.svg        # 贴纸素材
│       └── tape_*.svg           # 胶带装饰
```

#### 4.3.4 核心接口

```python
# report_service.py

class ReportService:
    def __init__(self, checkin_repo: CheckinRepo, ledger_repo: LedgerRepo,
                 task_repo: TaskRepo, shooting_repo: ShootingRepo):
        ...

    def collect_data(self, date: str) -> ReportData:
        """
        从各 Repository 收集当天所有数据，组装成 ReportData 对象。
        包含:
          - 打卡详情 (时间、判定状态)
          - 奖惩明细 (金额汇总)
          - 工作时长统计
          - 是否超过 8 小时
          - 男友承诺及兑现情况
          - 完成任务清单
          - 随机鼓励语
        """

    def generate_html(self, data: ReportData) -> str:
        """Jinja2 渲染 HTML"""

    def screenshot(self, html: str) -> str:
        """
        Android WebView 加载 HTML → 截图 → 返回临时文件路径
        """

    def save_to_gallery(self, image_path: str) -> bool:
        """保存到系统相册"""

    def generate_and_save(self, date: str) -> str:
        """一键生成并保存，返回保存路径"""
```

#### 4.3.5 ReportData 数据结构

```python
@dataclass
class ReportData:
    date: str
    is_shooting_day: bool

    # 打卡详情
    periods: list[PeriodDetail]       # morning / afternoon / night 各一

    # 奖惩汇总
    penalty_total: float              # 罚款总额 (负值)
    reward_total: float               # 奖励总额 (正值)
    net_amount: float                 # 净额

    # 工时
    total_work_hours: float           # 总工作时长
    overtime_hours: float             # 加班时长

    # 男友承诺
    promise: Optional[PromiseDetail]

    # 任务清单
    completed_tasks: list[str]

    # 鼓励语
    encouragement: str                # 随机选取

@dataclass
class PeriodDetail:
    period: str                       # morning / afternoon / night
    checkin_time: Optional[str]
    checkout_time: Optional[str]
    status: str
    status_label: str                 # "正常" / "迟到" / ...

@dataclass
class PromiseDetail:
    reward_desc: str                  # "一杯奶茶"
    reward_qty: int
    fulfilled: bool
```

#### 4.3.6 测试要点

| 测试场景 | 验证内容 |
|---------|---------|
| 普通办公室日战报 | 所有字段正确渲染，HTML 无异常 |
| 拍摄日战报 | 使用 shooting_report.html 模板 |
| 超 8 小时鼓励框 | 工时 ≥ 8h 显示特殊样式 |
| 男友承诺已兑现 | 显示兑现标记 |
| 男友承诺未兑现 | 显示未达标提示 |
| 截图尺寸 | 长图宽度固定，高度自适应内容 |
| 保存相册 | 权限申请 + 保存成功 |

---

### 4.4 M4 — 拍摄日模块

#### 4.4.1 职责边界

- **管**：拍摄日设定/切换、拍摄中状态展示、复盘问卷弹窗、答复合成为文字总结
- **不管**：拍摄日战报长图生成（复用 M3 的 shooting_report.html 模板）

#### 4.4.2 文件结构

```
app/
├── services/
│   └── shooting_service.py      # 拍摄日业务逻辑
├── repositories/
│   └── shooting_repo.py         # 拍摄日 + 复盘 CRUD
├── components/
│   └── shooting_reflection_dialog.py  # 复盘弹窗组件
```

#### 4.4.3 核心接口

```python
# shooting_service.py

class ShootingService:
    def __init__(self, shooting_repo: ShootingRepo):
        ...

    # --- 拍摄日设定 ---
    def set_shooting_day(self, date: str, reward_desc: str = "") -> ShootingDay:
        """
        将某天设为拍摄日。
        提前规划: 每周开始前预设
        当天切换: 在上午打卡时间之前可切换
        触发事件: EventType.SHOOTING_DAY_SET
        """

    def cancel_shooting_day(self, date: str) -> None:
        """取消拍摄日 (仅当天上午打卡时间前可取消)"""

    def is_shooting_day(self, date: str) -> bool:
        ...

    # --- 复盘 ---
    def get_reflection_questions(self) -> list[str]:
        """返回四个复盘问题"""
        # 1. 拍摄内容是什么？
        # 2. 拍摄地点在哪？
        # 3. 拍摄是否顺利？
        # 4. 有什么感想？

    def submit_reflection(self, date: str, answers: dict) -> ShootingReflection:
        """
        answers: {
            'content': str,
            'location': str,
            'smoothness': 'smooth' | 'normal' | 'rough',
            'thoughts': str,
        }
        自动调用 _generate_summary() 生成文字总结
        """

    def _generate_summary(self, answers: dict) -> str:
        """
        本地模板拼接:
          - smooth → "今天在{location}顺利完成了{content}的拍摄。{thoughts}"
          - normal → "今天在{location}进行了{content}拍摄，过程正常。{thoughts}"
          - rough → "今天在{location}拍摄{content}，遇到了一些挑战。{thoughts}"
        随机变换过渡词增加自然感
        """
```

#### 4.4.4 复盘触发时机

- 拍摄日当天 23:00，APP 检查今日是否为拍摄日
- 若是且未提交复盘 → 弹出对话框
- 用户可关闭稍后再填，但战报不会生成直到提交复盘

#### 4.4.5 测试要点

| 测试场景 | 输入 | 预期输出 |
|---------|------|---------|
| 提前预设拍摄日 | 周日设下周三为拍摄日 | 下周三自动进入拍摄模式 |
| 当天切换拍摄日 | 08:30 切换今天 | 切换成功，跳过打卡 |
| 超时不允许切换 | 09:05 切换今天(设定 09:00) | 拒绝切换 |
| 复盘顺利场景 | smooth + 各字段 | summary 包含"顺利完成" |
| 复盘不顺利场景 | rough + 各字段 | summary 包含"遇到挑战" |
| 23:00 未复盘 | 23:00 拍摄日未提交 | 弹出复盘弹窗 |

---

### 4.5 M5 — 历史模块

#### 4.5.1 职责边界

- **管**：周/月/年三种视图的数据查询和展示
- **不管**：数据怎么来（只读消费 Repository）

#### 4.5.2 文件结构

```
app/
├── services/
│   └── history_service.py       # 历史数据查询
├── components/
│   ├── week_view.py             # 周视图 (卡片流)
│   ├── month_view.py            # 月视图 (日历格子)
│   └── year_view.py             # 年视图 (汇总卡片)
```

#### 4.5.3 核心接口

```python
# history_service.py

class HistoryService:
    def __init__(self, checkin_repo: CheckinRepo, ledger_repo: LedgerRepo,
                 shooting_repo: ShootingRepo):
        ...

    def get_week_view(self, week_start: str) -> WeekViewData:
        """
        周视图数据: 每天一张卡片
        卡片内容: 日期、各时段打卡状态、工作时长、当日奖惩汇总
        """

    def get_month_view(self, year: int, month: int) -> MonthViewData:
        """
        月视图数据: 日历格子
        每格颜色:
          🟢 正常 (全部 normal)
          🟡 迟到或早退
          🔴 旷工 (任意时段)
          🔵 请假
          🟠 拍摄日
        奖惩金额按周汇总
        """

    def get_year_view(self, year: int) -> YearViewData:
        """
        年视图: 12 个月汇总卡片
        每月: 出勤天数、迟到/旷工次数、总时长、总奖惩
        """
```

#### 4.5.4 视图数据结构

```python
@dataclass
class WeekViewData:
    week_start: str
    week_end: str
    days: list[DayCard]
    weekly_net: float            # 本周净额

@dataclass
class DayCard:
    date: str
    periods: list[PeriodSummary]
    total_hours: float
    daily_ledger: list[LedgerEntry]  # 当天奖惩明细
    is_shooting: bool

@dataclass
class MonthViewData:
    year: int
    month: int
    cells: list[CalendarCell]     # 28-31 个
    weekly_summaries: list[WeekSummary]

@dataclass
class CalendarCell:
    date: str
    color: str                   # green / yellow / red / blue / orange / empty
    has_data: bool

@dataclass
class YearViewData:
    year: int
    months: list[MonthSummary]

@dataclass
class MonthSummary:
    month: int
    work_days: int
    late_count: int
    absent_count: int
    total_hours: float
    total_ledger: float
```

#### 4.5.5 测试要点

| 测试场景 | 验证内容 |
|---------|---------|
| 空周视图 | 无打卡记录的周，显示空白提示 |
| 混合状态周 | 颜色和金额正确 |
| 月视图颜色 | 每种出勤状态颜色正确 |
| 月末边界 | 跨月周的数据归属正确 |
| 年视图汇总 | 12 个月统计数据正确 |

---

### 4.6 M6 — 设置模块

#### 4.6.1 职责边界

- **管**：所有可配置参数的读写、首次使用引导流程
- **不管**：参数怎么被其他模块消费（其他模块通过 SettingsRepo 读取）

#### 4.6.2 文件结构

```
app/
├── services/
│   └── settings_service.py      # 设置管理
├── repositories/
│   └── settings_repo.py         # 设置键值对 CRUD
├── screens/
│   ├── settings_screen.py       # 设置页面
│   └── onboarding.py            # 首次引导页
```

#### 4.6.3 核心接口

```python
# settings_service.py

class SettingsService:
    def __init__(self, settings_repo: SettingsRepo):
        ...

    # --- 参数读写 ---
    def get(self, key: str) -> Optional[str]:
        ...

    def set(self, key: str, value: str) -> None:
        """触发事件: EventType.SETTINGS_CHANGED"""

    def get_all(self) -> dict:
        """返回所有设置的字典"""

    def batch_set(self, settings: dict) -> None:
        """批量设置 (首次引导使用)"""

    # --- 默认值 ---
    DEFAULTS = {
        "morning_start": "09:00",
        "morning_end": "12:00",
        "afternoon_start": "14:00",
        "afternoon_end": "18:00",
        "late_penalty": "10",
        "early_leave_penalty": "10",
        "absent_penalty": "50",
        "full_attendance_bonus": "100",
        "bet_base_reward": "50",
        "bet_extra_reward": "30",
        "bet_penalty": "50",
        "work_days": "1,2,3,4,5",      # 周一至周五
        "shooting_reward": "30",
        "boyfriend_hour_threshold": "8",
    }

    # --- 首次引导 ---
    def is_first_launch(self) -> bool:
        """检查 APP 是否首次启动"""

    def complete_onboarding(self) -> None:
        """标记引导完成"""
```

#### 4.6.4 设置页面字段清单

| 参数 | key | 类型 | 默认值 |
|------|-----|------|--------|
| 上午上班时间 | `morning_start` | time | 09:00 |
| 上午下班时间 | `morning_end` | time | 12:00 |
| 下午上班时间 | `afternoon_start` | time | 14:00 |
| 下午下班时间 | `afternoon_end` | time | 18:00 |
| 迟到罚款 | `late_penalty` | number | 10 |
| 早退罚款 | `early_leave_penalty` | number | 10 |
| 旷工罚款 | `absent_penalty` | number | 50 |
| 全勤奖励 | `full_attendance_bonus` | number | 100 |
| 对赌基础奖励 | `bet_base_reward` | number | 50 |
| 对赌超额奖励 | `bet_extra_reward` | number | 30 |
| 对赌惩罚 | `bet_penalty` | number | 50 |
| 工作日选择 | `work_days` | multi-select | 周一至周五 |
| 拍摄日奖励 | `shooting_reward` | number | 30 |
| 男友奖励门槛 | `boyfriend_hour_threshold` | number | 8 |

#### 4.6.5 首次引导流程

```
Step 1: 设置上午上下班时间
    ↓
Step 2: 设置下午上下班时间
    ↓
Step 3: 选择工作日 (周一至周日勾选)
    ↓
Step 4: 设定罚款金额 (迟到/早退/旷工)
    ↓
Step 5: 设定全勤奖励
    ↓
Step 6: 设定男友奖励时长门槛
    ↓
Step 7: 设定拍摄日奖励
    ↓
Step 8: 规划未来拍摄日 (可选，可跳过)
    ↓
完成 → 进入主界面
```

#### 4.6.6 测试要点

| 测试场景 | 验证内容 |
|---------|---------|
| 默认值读取 | 首次安装返回 DEFAULTS |
| 写入/读取 | set 后 get 返回正确值 |
| 时间合法性 | 下班时间不早于上班时间 |
| 引导跳过 | 可选步骤跳过不影响后续 |
| 工作日勾选 | 全不选/全选的边界情况 |

---

### 4.7 M7 — 同步模块

#### 4.7.1 职责边界

- **管**：WebSocket 连接管理、数据推送、云端备份与恢复
- **不管**：推送什么数据（其他模块产生数据后，同步模块被动读取并推送）

#### 4.7.2 文件结构

```
app/
├── services/
│   └── sync_service.py          # 同步业务逻辑
├── repositories/
│   └── sync_repo.py             # 同步状态记录
server/
├── main.py                      # FastAPI 入口
├── routes/
│   ├── sync_routes.py           # 数据同步 API
│   └── review_routes.py         # 检阅端网页 API
├── services/
│   └── push_service.py          # WebSocket 推送管理
├── models/
│   └── sync_models.py           # 数据库模型 (SQLAlchemy)
├── templates/
│   └── review.html              # 检阅端网页
└── requirements.txt
```

#### 4.7.3 后端 API 设计

**Base URL:** `https://<server>/api/v1`

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| `POST` | `/sync/backup` | APP 上传完整数据备份 | Bearer Token |
| `GET` | `/sync/restore` | APP 下载完整数据备份 | Bearer Token |
| `POST` | `/sync/event` | APP 推送单条事件数据 | Bearer Token |
| `GET` | `/review/status` | 检阅端查询当前状态 | Bearer Token |
| `GET` | `/review/history?date=` | 检阅端查询历史 | Bearer Token |
| `WS` | `/ws` | WebSocket 实时推送 | Bearer Token (query param) |

#### 4.7.4 WebSocket 消息格式

```json
{
  "type": "check_in" | "check_out" | "report" | "promise" | "heartbeat",
  "timestamp": "2026-06-01T09:05:30",
  "payload": { ... }
}
```

具体 Payload 示例：

```json
// 打卡事件
{"type": "check_in", "payload": {
    "date": "2026-06-01", "period": "morning",
    "checkin_time": "09:05", "status": "late"
}}

// 战报事件
{"type": "report", "payload": {
    "date": "2026-06-01", "total_hours": 8.5,
    "net_amount": -10
}}

// 男友承诺
{"type": "promise", "payload": {
    "date": "2026-06-01", "reward_desc": "一杯奶茶",
    "reward_qty": 1, "fulfilled": false
}}
```

#### 4.7.5 核心接口

```python
# sync_service.py (APP 端)

class SyncService:
    def __init__(self, sync_repo: SyncRepo):
        self.ws = None            # WebSocket 连接
        self.token = None         # 从 SettingsRepo 读取

    def connect(self) -> bool:
        """建立 WebSocket 连接，自动重连"""

    def disconnect(self) -> None:
        ...

    def push_event(self, event_type: EventType, payload: dict) -> None:
        """推送单条事件到后端"""

    def backup_full(self) -> bool:
        """导出全部本地数据 → POST /sync/backup"""

    def restore_full(self) -> bool:
        """GET /sync/restore → 覆盖本地数据"""

    def is_connected(self) -> bool:
        ...
```

```python
# push_service.py (后端)

class PushService:
    """管理 WebSocket 连接池，向检阅端推送"""

    async def broadcast(self, message: dict) -> None:
        """向所有已连接的检阅端广播消息"""

    async def send_to_user(self, user_id: str, message: dict) -> None:
        """向特定用户推送"""
```

#### 4.7.6 备份与恢复

```
备份 (APP → Server):
  1. SQLite .dump 导出为 JSON
  2. POST /sync/backup 上传
  3. 后端存储到服务器 SQLite / PostgreSQL

恢复 (Server → APP):
  1. GET /sync/restore 下载
  2. 清空本地 SQLite
  3. 逐表写入
  4. 触发所有相关模块的数据刷新
```

#### 4.7.7 检阅端网页

后端提供单页 HTML (`server/templates/review.html`)：
- 左侧：实时状态面板（今日打卡状态、工作时长、男友承诺）
- 右侧：历史数据查看（周/月切换）

无需前端框架，纯 HTML + 原生 JS + WebSocket 连接。

#### 4.7.8 测试要点

| 测试场景 | 验证内容 |
|---------|---------|
| WebSocket 连接 | 成功建立，心跳维持 |
| 断线重连 | 模拟断网 → 自动重连 |
| 打卡推送 | APP 打卡 → WebSocket 消息到达后端 |
| 备份→恢复 | 备份后清空本地 → 恢复后数据一致 |
| Token 认证失败 | 错误 Token → 401 |
| 离线缓存 | 无网络时缓存事件 → 恢复后批量推送 |

---

### 4.8 M8 — 激励模块

#### 4.8.1 职责边界

- **管**：连续出勤天数统计、通知栏常驻卡片
- **不管**：出勤判定（那是 M1 的事）、打卡提醒（那是 M1 的事）

#### 4.8.2 文件结构

```
app/
├── services/
│   └── motivation_service.py    # 连续天数 + 通知卡片
├── repositories/
│   └── streak_repo.py           # 连续出勤记录
```

#### 4.8.3 核心接口

```python
# motivation_service.py

class MotivationService:
    def __init__(self, checkin_repo: CheckinRepo, streak_repo: StreakRepo):
        ...

    def get_current_streak(self) -> int:
        """
        返回连续正常出勤天数。
        发生迟到/早退/旷工/请假(上午/下午/全天) → 计数归零。
        仅计算工作日，非工作日不影响计数。
        """

    def update_streak(self, date: str) -> int:
        """
        每天 DAY_FINISHED 事件后更新。
        订阅: EventType.DAY_FINISHED
        """

    # --- 通知栏卡片 ---
    def update_notification(self, status: str) -> None:
        """
        更新 Android 通知栏常驻卡片。
        status:
          - 'checked_in' → "今日已打卡 ✅"
          - 'not_checked_in' → "今日未打卡 ⏳"
          - 'shooting' → "拍摄中 📸"
        使用 Android Notification (ongoing + low priority)，
        用户无法手动划掉。
        """

    def show_morning_promise_dialog(self) -> None:
        """
        首次打卡后触发通知/弹窗，
        引导用户输入当日男友承诺 (调用 M2)。
        """
```

#### 4.8.4 连续天数判定规则

```
每日 DAY_FINISHED 事件 → 检查当天所有时段判定:
  ├── 全部 normal → streak += 1
  ├── 有 late / early_leave / absent / leave → streak = 0
  ├── 全部 shooting → streak 保持不变 (不增不减)
  └── 非工作日 → streak 保持不变
```

#### 4.8.5 测试要点

| 测试场景 | 验证内容 |
|---------|---------|
| 连续正常 | 5 天全 normal → streak = 5 |
| 中断重置 | 第 6 天迟到 → streak = 0 |
| 请假归零 | 请假 → streak = 0 |
| 拍摄日不影响 | 拍摄日 → streak 不变 |
| 周末不影响 | 非工作日 → streak 不变 |
| 通知卡片更新 | 签到后更新为 ✅ |

---

## 5. 模块依赖关系

```
                         ┌──────────┐
                         │ M6 设置  │ (无依赖，纯被读)
                         └────┬─────┘
                              │ 被读取
             ┌────────────────┼────────────────┐
             ▼                ▼                ▼
       ┌──────────┐    ┌──────────┐    ┌──────────┐
       │ M1 考勤  │    │ M2 奖惩  │    │ M4 拍摄日│
       └────┬─────┘    └────┬─────┘    └────┬─────┘
            │ 写数据        │ 写数据        │ 写数据
            ▼               ▼               ▼
       ┌─────────────────────────────────────────┐
       │           Repository 层                 │
       │  checkin / ledger / bet / shooting /   │
       │  task / settings / streak              │
       └────┬──────────────┬────────────────────┘
            │ 被读取        │ 被读取
            ▼               ▼
       ┌──────────┐    ┌──────────┐
       │ M3 战报  │    │ M5 历史  │
       └──────────┘    └──────────┘

       ┌──────────┐
       │ M7 同步  │ ← 订阅所有 EventType
       └──────────┘   读所有 Repository

       ┌──────────┐
       │ M8 激励  │ ← 读 CheckinRepo、读 SettingsRepo
       └──────────┘

┌──────────────────────────────────────────────────┐
│  基础设施 (所有模块依赖)                            │
│  ┌──────────┐  ┌──────────┐                      │
│  │ M9 Clock │  │ EventBus │                      │
│  └──────────┘  └──────────┘                      │
│  统一时间源    模块间事件通信                        │
└──────────────────────────────────────────────────┘
```

**独立测试验证：**
- 每个模块的 Service 接收 Mock Repository，可完全脱离其他模块运行
- 注入 SimulatedClock，可验证任意时间点下的行为
- 测试不需要真实等待时间流逝，`advance()` 瞬间跳转

---

## 6. 通用规范

### 6.1 时间格式

- 所有存储时间使用 24 小时制字符串：`HH:MM` 或 `HH:MM:SS`
- 所有存储日期使用 ISO 格式：`YYYY-MM-DD`
- 周起始日：周一

### 6.2 错误处理

- Service 层方法不吞异常，由 UI 层统一 try-catch 并展示 Toast
- Repository 层抛出明确的自定义异常（如 `RecordNotFoundError`）

### 6.3 日志

- 使用 Python `logging` 模块
- APP 端：关键操作（打卡、判定、奖惩计算、同步）记录 INFO 日志
- 后端：所有 API 请求记录请求路径和耗时

---

## 7. 待定事项

以下事项在 proposal 中提及但尚未明确，后续迭代中补充：

1. 战报手账风格的**具体视觉设计稿**（贴纸种类、字体、配色）
2. 微信/飞书机器人的接入方式和消息模板
3. 奖励兑换的现实流程（虚拟账本 → 实际转账）
4. 拍摄日奖励的描述字段具体格式
