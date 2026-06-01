# Soloist Cabin Pro — UI 阶段 Vibe Coding 主控 Prompt

你是一个**主控 Agent**，负责将 Soloist Cabin Pro 的像素风 UI 从占位骨架实现到完整的可运行界面。你不会离开这个对话，整个过程不需要人工参与。

---

## 1. 当前项目状态

**后端已全部完成**（9 个模块，130+ 测试通过，mypy strict + ruff 零错误）。所有 Service / Repository / Model 层代码就绪，UI 层目前只有类定义占位。

```
当前可用的层:
  app/services/*     ← 全部完成，UI 直接调用 Service 公开方法
  app/repositories/* ← 全部完成，UI 不直接访问
  app/utils/clock.py ← get_clock() 单例，UI 中所有时间获取必须用它
  app/services/event_bus.py ← EventBus，UI 可订阅事件来刷新状态
  app/main.py        ← Kivy APP 入口（占位，需重写）
  app/screens/*      ← 占位，将被 app/ui/screens/ 替代
  app/components/*   ← 占位，将被 app/ui/components/ 替代
```

### 需求与设计文档

| 文档 | 路径 |
|------|------|
| 产品需求 | [proposal.md](../proposal.md) |
| 后端详细设计 | [detailed-design.md](../detailed-design.md) |
| **UI 设计** | [ui-design.md](../ui-design.md) |
| 后端任务划分 | [tasks/](../tasks/) |
| **UI 任务划分** | [tasks/](tasks/) |

---

## 2. UI 模块体系（7 个模块，4 个阶段）

| 编号 | 模块 | 职责 | 任务文件 |
|------|------|------|----------|
| UI-01 | 设计令牌 + 基础组件 | 配色常量/边框样式/网格/字体 + PixelButton/PixelInput/Dialog 等全局共用组件 | [tasks/ui-01-design-foundation.md](tasks/ui-01-design-foundation.md) |
| UI-02 | 像素资源 | 5 只角色 sprite sheet + 16 个功能图标 + 像素字体集成 | [tasks/ui-02-pixel-assets.md](tasks/ui-02-pixel-assets.md) |
| UI-03 | 打卡主界面 | PeriodCard/StatusBox/任务清单/男友承诺/打卡流程/动画 | [tasks/ui-03-checkin-page.md](tasks/ui-03-checkin-page.md) |
| UI-04 | 历史页 | 周/月/年三视图 + DayCard/CalendarCell/MonthCard | [tasks/ui-04-history-page.md](tasks/ui-04-history-page.md) |
| UI-05 | 对赌页 | 任务 CRUD/进度跟踪/周结算弹窗/滑动操作 | [tasks/ui-05-bet-page.md](tasks/ui-05-bet-page.md) |
| UI-06 | 设置页 | 4 组折叠设置/时间选择器/数字输入/工作日选择/备份恢复 | [tasks/ui-06-settings-page.md](tasks/ui-06-settings-page.md) |
| UI-07 | 引导流程 + 全局整合 | Onboarding/底部导航栏/页面路由/动画引擎/App入口 | [tasks/ui-07-integration.md](tasks/ui-07-integration.md) |

### 依赖拓扑

```
UI-01 (设计令牌 + 基础组件) ──→ UI-03, UI-04, UI-05, UI-06, UI-07
UI-02 (像素资源)            ──→ UI-03, UI-04, UI-05, UI-06, UI-07
UI-03~06 (4 个页面)        ──→ UI-07 (全局整合，依赖所有页面)
```

---

## 3. 你（主控 Agent）的工作流程

### 阶段 1：设计令牌 + 基础组件（由你亲自完成，不派生子 Agent）

按 `tasks/ui-01-design-foundation.md` 的清单逐项实现：

```
1.1~1.6   创建 app/ui/tokens.py（主色板/辅色/功能语义色/网格/字体/阴影常量）
1.7~1.8   创建 app/ui/components/pixel_button.py
1.9       创建 app/ui/components/pixel_input.py
1.10      创建 app/ui/components/pixel_dialog.py
1.11      创建 app/ui/components/collapsible_group.py
1.12      创建 app/ui/components/mascot_bubble.py
1.13      创建 app/ui/components/pixel_checkbox.py
1.14      创建 app/ui/components/pixel_stepper.py
1.15~1.18 创建 app/ui/utils.py（pixel_border_raised/inset/shadow/snap_to_grid）
1.19~1.20 编写测试
```

**阶段 1 完成条件：**
- `pytest app/tests/ui/test_tokens.py app/tests/ui/test_base_components.py -v` 全部通过
- `mypy --strict app/ui/tokens.py app/ui/components/ app/ui/utils.py` 零错误
- `ruff check app/ui/` 零错误
- 所有 20 项子任务勾选完成

---

### 阶段 2：像素资源（由你亲自完成，不派生子 Agent）

按 `tasks/ui-02-pixel-assets.md` 的清单逐项实现：

```
2.1~2.2   下载/配置像素字体，创建 app/ui/fonts.py
2.3~2.7   逐角色生成 5 个 sprite sheet PNG（兜兜/嗡嗡/团团/旺仔/咪咕，每个 4 帧）
2.8~2.9   逐图标生成 16 个功能图标 PNG
2.10~2.12 创建 app/ui/assets/loader.py（SpriteLoader + IconLoader + preload_all）
2.13~2.14 编写测试
```

**像素角色生成规范（严格遵守）：**
- 画布 16×16 或 32×32 像素，每帧等宽，横向排列
- 颜色 ≤4 色（主色 + 亮面 + 暗面 + 轮廓/特征色），色值严格使用 UI 设计文档第 5.3 节的色板
- 眼睛：2×2 黑块（豆豆眼）或 1×2 竖线（眯眼笑）
- 腮红：2×2 浅粉方块，位于眼下外侧
- PNG 格式，nearest-neighbor 放大（保持像素锯齿感）
- 用 Python 脚本逐像素生成（PIL/Pillow），不依赖外部素材

**阶段 2 完成条件：**
- `pytest app/tests/ui/test_assets.py -v` 全部通过
- `mypy --strict app/ui/assets/ app/ui/fonts.py` 零错误
- 所有 14 项子任务勾选完成

---

### 阶段 3：4 个页面并行（派生子 Agent）

**这是唯一派生子 Agent 的阶段。** 4 个页面无相互依赖，可并行。

同时派发 4 个子 Agent，每个 Agent 的完整派发 prompt 见第 4 节模板 + 对应任务文件：

| 子 Agent | 模块 | 任务文件 |
|----------|------|----------|
| Agent-A | UI-03 打卡主界面 | [tasks/ui-03-checkin-page.md](tasks/ui-03-checkin-page.md) |
| Agent-B | UI-04 历史页 | [tasks/ui-04-history-page.md](tasks/ui-04-history-page.md) |
| Agent-C | UI-05 对赌页 | [tasks/ui-05-bet-page.md](tasks/ui-05-bet-page.md) |
| Agent-D | UI-06 设置页 | [tasks/ui-06-settings-page.md](tasks/ui-06-settings-page.md) |

**每个子 Agent 返回后，你必须：**
1. 检查其是否通过 pytest + mypy + ruff
2. 检查其是否完成了对应 task 文件中的所有子任务
3. 更新 `progress.md` 勾选对应模块
4. 更新对应的任务文件勾选已完成子任务

---

### 阶段 4：引导流程 + 全局整合（由你亲自完成，不派生子 Agent）

4 个页面全部完成后，按 `tasks/ui-07-integration.md` 的清单逐项实现：

```
7.1~7.5   创建 app/ui/animations/core.py（FrameAnimator/SpritePlayer/过渡动画）
7.6~7.9   创建 app/ui/navigation.py（BottomTabBar + AppScreenManager + 页面路由）
7.10~7.16 创建 app/ui/screens/onboarding_screen.py（分步引导流程）
7.17~7.20 重写 app/main.py（字体加载/资源预加载/首次启动判断/全局主题）
7.21~7.23 创建 app/ui/components/report_preview.py（战报弹层集成）
7.24~7.26 全局一致性检查（像素风格/角色出场/网格对齐）
7.27~7.30 编写测试
```

**阶段 4 完成条件：**
- 全部 30 项子任务完成
- `pytest app/tests/ui/ -v` 全部通过
- `mypy --strict app/` 零错误
- `ruff check app/` 零错误
- 4 个页面均可通过 AppScreenManager 正常切换
- 首次启动 → Onboarding → 主界面 完整链路可走通

---

## 4. 子 Agent 执行模板（阶段 3 使用）

向子 Agent 发出的 prompt 必须包含以下结构：

```
## 任务

实现 Soloist Cabin Pro 的 [页面名称]（[模块编号]）。

## 上下文

你是子 Agent，在 Soloist Cabin Pro 项目中实现 [页面名称] 的 UI。
主 Agent 已完成设计令牌 + 基础组件 + 像素资源。

### 已有基础设施（可直接 import 使用）

**设计系统 (app/ui/):**
- app/ui/tokens.py — 全部设计常量：COLORS, DOPAMINE_COLORS, SEMANTIC_COLORS, GRID, FONTS, SHADOWS
- app/ui/utils.py — pixel_border_raised(), pixel_border_inset(), pixel_shadow(), snap_to_grid()
- app/ui/fonts.py — load_pixel_fonts()

**基础组件 (app/ui/components/):**
- pixel_button.py — PixelButton (凸起 3D 像素按钮，支持 normal/large/small)
- pixel_input.py — PixelInput (内凹像素输入框)
- pixel_dialog.py — ConfirmDialog (通用确认弹窗)
- collapsible_group.py — CollapsibleGroup (折叠分组)
- mascot_bubble.py — MascotBubble (角色对话气泡)
- pixel_checkbox.py — PixelCheckbox (4×4 像素勾选框)
- pixel_stepper.py — PixelStepper (步进器)

**像素资源 (app/ui/assets/):**
- loader.py — SpriteLoader(load_sprite/load_frame), IconLoader(get_icon), preload_all()
- sprites/ — 5 个角色 sprite sheet PNG
- icons/ — 16 个功能图标 PNG

**后端服务（直接调用，无需关心内部实现）:**
[根据页面列出相关的 Service 接口签名]

**测试工具:**
- app/tests/conftest.py — clock/bus/temp_db fixtures + reset_globals (autouse)
- app/utils/clock.py — SimulatedClock（测试中控制时间）

### 当前项目目录结构
[完整的目录树快照]

## 要求

1. 按照任务清单逐项实现（见 doc/ui-design/tasks/[对应文件]）
2. 实现顺序：组件 → 页面组装 → 动画（如有）→ 测试
3. 所有颜色/间距/字体引用 UI-01 的 tokens，禁止硬编码色值
4. 所有按钮使用 PixelButton，所有输入使用 PixelInput，所有弹窗使用 ConfirmDialog 或像素边框样式
5. 数据获取通过已有的 Service 类，组件通过构造函数注入 Service 实例
6. 所有时间获取必须用 get_clock().now()，禁止直接调用 datetime.now()
7. 像素风格严格遵守：2px 边框、无圆角、8px 网格对齐、纯黑 2px 偏移阴影
8. 角色出场场景严格匹配 UI 设计文档第 5 章

## 交付标准

任务完成后返回以下信息：
- 新增/修改的文件列表
- pytest 运行结果（必须全部通过）
- mypy 检查结果（必须零错误）
- ruff 检查结果（必须零错误）
- 剩余未完成的子任务（如有，需说明原因）
```

---

## 5. 质量门禁

### 必须通过的三道检查

```bash
# 1. 单元测试（UI 测试使用 Kivy headless）
pytest app/ -v

# 2. 类型检查
mypy --strict app/

# 3. 代码规范
ruff check app/
```

**三者全部通过才视为完成。任一失败必须修复。**

### UI 测试规范

```python
# 所有 UI 测试必须设置 headless 后端
from kivy.config import Config
Config.set('graphics', 'backend', 'offscreen')

# 使用 SimulatedClock 控制时间
from app.utils.clock import SimulatedClock, set_clock

def test_ui_something():
    clock = SimulatedClock()
    clock.set_date_and_time("2026-06-01", "08:55")
    set_clock(clock)
    # ... UI 交互测试 ...
```

### 测试覆盖率要求

| 层级 | 要求 |
|------|------|
| UI 组件 | 每个组件的公开方法至少一个测试（按钮点击/输入变化/状态切换） |
| 页面 | 关键交互路径（用户操作 → Service 调用 → UI 更新）覆盖 |
| 动画 | 帧序列正确性、回调触发验证 |
| 导航 | Tab 切换/页面路由正确性 |

---

## 6. UI 编码规范

### 像素风格约束（全项目统一）

```
边框:    2px 粗边框，无圆角（border_radius=0）
阴影:    纯黑 #000000，x=2px y=2px，不透明不模糊
间距:    所有 padding/margin 对齐 8px 网格
按钮:    凸起=亮面(top+left) 暗面(bottom+right); 按下=明暗互换(凹陷)
输入框:  内凹=暗面(top+left) 亮面(bottom+right)
字体:    像素字体（Press Start 2P / Silkscreen），正文 14px，标题 18px
角色:    16×16 或 32×32 像素网格，nearest-neighbor 放大至 64×64 dp
图标:    16×16 像素网格，nearest-neighbor 放大至 32×32 dp
```

### 组件注入模式

```python
# 组件通过构造函数接收 Service 实例，便于测试时 mock
class CheckinScreen(ScrollView):
    def __init__(self, checkin_service: CheckinService, **kwargs):
        super().__init__(**kwargs)
        self._svc = checkin_service

# 测试时注入 mock
def test_checkin_flow():
    mock_svc = Mock(spec=CheckinService)
    mock_svc.check_in.return_value = CheckinResult(...)
    screen = CheckinScreen(checkin_service=mock_svc)
```

### 颜色引用规则

```python
# ✅ 正确：从 tokens 引用
from app.ui.tokens import COLORS, SEMANTIC_COLORS
button_bg = COLORS.PRIMARY_YELLOW
status_bg = SEMANTIC_COLORS["late"]["block"]

# ❌ 错误：硬编码色值
button_bg = "#FFE030"
```

---

## 7. 已有后端接口速查

UI 组件直接调用以下 Service 公开方法（已全部实现并测试通过）：

### CheckinService
```python
svc.check_in(date: str, period: str) -> CheckinResult
svc.check_out(date: str, period: str) -> CheckinResult
svc.get_leave_options(date: str, current_time: str) -> list[str]  # ["morning", "afternoon", "all_day"]
svc.apply_leave(date: str, scope: str) -> None
svc.get_today_status(date: str) -> DayStatus  # 含三个 PeriodStatus
```

### HistoryService
```python
svc.get_week_view(week_start: str) -> list[DaySummary]
svc.get_month_view(year: int, month: int) -> list[CalendarCell]
svc.get_year_view(year: int) -> list[MonthSummary]
```

### BetService
```python
svc.create_task(week_start: str, task_desc: str, target_qty: int) -> BetTask
svc.complete_task(task_id: int) -> None
svc.delete_task(task_id: int) -> None
svc.set_week_config(week_start: str, base_reward: int, extra_reward: int, penalty: int) -> None
svc.settle_week(week_start: str) -> WeeklySettlementResult
svc.get_week_summary(week_start: str) -> WeekSummary
```

### SettingsService
```python
svc.get(key: str) -> object
svc.set(key: str, value: object) -> None
svc.batch_set(items: dict[str, object]) -> None
svc.get_all() -> dict[str, object]
svc.is_first_launch() -> bool
svc.complete_onboarding() -> None
svc.get_work_days() -> list[int]  # [0,1,2,3,4] = Mon-Fri
```

### SyncService
```python
svc.backup_full() -> dict
svc.restore_full(data: dict) -> bool
svc.connect() -> bool
svc.disconnect() -> None
```

### BoyfriendPromiseService
```python
svc.set_promise(date: str, reward_desc: str, reward_qty: int) -> None
svc.check_fulfill(date: str, total_work_hours: float) -> bool
```

### MotivationService
```python
svc.get_current_streak() -> int
svc.update_streak(date: str) -> None
```

### ReportService
```python
svc.generate_and_save(date: str) -> str  # 返回图片路径
svc.collect_data(date: str) -> ReportData
```

### ShootingService
```python
svc.set_shooting_day(date: str) -> None
svc.cancel_shooting_day(date: str) -> bool
svc.submit_reflection(date: str, answers: dict) -> None
```

---

## 8. 文件组织（UI 新增部分）

```
app/
├── main.py                          # ← 重写：集成导航+引导+主题
├── ui/                              # ← 新建目录
│   ├── tokens.py                    # 设计常量
│   ├── utils.py                     # 像素边框/网格工具函数
│   ├── fonts.py                     # 像素字体加载
│   ├── navigation.py                # BottomTabBar + AppScreenManager
│   ├── components/
│   │   ├── pixel_button.py
│   │   ├── pixel_input.py
│   │   ├── pixel_dialog.py
│   │   ├── collapsible_group.py
│   │   ├── mascot_bubble.py
│   │   ├── pixel_checkbox.py
│   │   ├── pixel_stepper.py
│   │   ├── period_card.py           # UI-03
│   │   ├── status_box.py            # UI-03
│   │   ├── task_inline_list.py      # UI-03
│   │   ├── promise_input.py         # UI-03
│   │   ├── day_card.py              # UI-04
│   │   ├── calendar_cell.py         # UI-04
│   │   ├── month_card.py            # UI-04
│   │   ├── history_tabs.py          # UI-04
│   │   ├── week_summary_header.py   # UI-05
│   │   ├── bet_task_item.py         # UI-05
│   │   ├── add_task_dialog.py       # UI-05
│   │   ├── bet_config_section.py    # UI-05
│   │   ├── settlement_dialog.py     # UI-05
│   │   ├── time_picker_row.py       # UI-06
│   │   ├── amount_picker_row.py     # UI-06
│   │   ├── pixel_time_picker.py     # UI-06
│   │   ├── pixel_number_dialog.py   # UI-06
│   │   └── report_preview.py        # UI-07
│   ├── screens/
│   │   ├── checkin_screen.py        # UI-03
│   │   ├── history_screen.py        # UI-04
│   │   ├── bet_screen.py            # UI-05
│   │   ├── settings_screen.py       # UI-06
│   │   └── onboarding_screen.py     # UI-07
│   ├── animations/
│   │   ├── core.py                  # FrameAnimator/SpritePlayer/过渡动画
│   │   └── checkin_animation.py     # 打卡成功动画序列
│   └── assets/
│       ├── fonts/                   # .ttf 像素字体文件
│       ├── sprites/                 # 5 个角色 sprite sheet PNG
│       ├── icons/                   # 16 个功能图标 + 4 个 Tab 图标
│       └── loader.py               # 资源预加载器
└── tests/
    └── ui/                          # ← 新建目录
        ├── __init__.py
        ├── test_tokens.py
        ├── test_base_components.py
        ├── test_assets.py
        ├── test_checkin_screen.py
        ├── test_history_screen.py
        ├── test_bet_screen.py
        ├── test_settings_screen.py
        ├── test_onboarding.py
        ├── test_navigation.py
        ├── test_animation.py
        └── test_app_entry.py
```

> 注：原有 `app/screens/` 和 `app/components/` 下的占位文件在全局整合阶段清理。

---

## 9. 进度追踪

你维护两个进度维度：

- **`doc/tasks/progress.md`**：模块级别的 checkbox，完成后打勾
- **`doc/ui-design/tasks/ui-XX-*.md`**：子任务级别 checkbox，完成后打勾

**每个阶段完成后，你必须：**
1. 运行 pytest + mypy + ruff 自检
2. 更新 `progress.md` 勾选对应模块
3. 更新对应任务文件勾选所有子任务
4. 汇报当前进度

---

## 10. 开始执行

现在以主控 Agent 的身份开始：

**第一步：阅读 `doc/ui-design.md` 确认你已理解 UI 设计全貌。**

**第二步：执行阶段 1 — 设计令牌 + 基础组件。** 完成后运行 pytest + mypy + ruff 自检，全部通过后汇报结果。

**第三步：执行阶段 2 — 像素资源。** 完成后自检并汇报。

**第四步：执行阶段 3 — 4 个页面并行。** 同时派发 4 个子 Agent，各自完成后验证并汇总。

**第五步：执行阶段 4 — 引导流程 + 全局整合。** 完成后最终自检并汇报。

进度文件位置：
- 总体进度：`doc/tasks/progress.md`
- UI 模块详情：`doc/ui-design/tasks/ui-01-design-foundation.md` ~ `ui-07-integration.md`
