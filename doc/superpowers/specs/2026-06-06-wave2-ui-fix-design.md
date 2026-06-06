# Wave 2 — 系统化修核心 UI bug 设计方案

> 日期: 2026-06-06
> 作者: andy + Claude
> 状态: 待审查
> 策略: A — 诊断驱动 (先写诊断工具找根因, 再按类型批量修同类 bug)

---

## 1. 背景

Wave 1 完成后 (4 个 task: PixelInput / PixelStepper size, AddTaskDialog pos_hint, 字体清理) + Task 5 (PixelButton size), 总共修了 5 处同 pattern bug。andy 实测后报新症状:

- "对赌页排版依旧很乱"
- "主页添加任务点不了"
- "点击查看战报也不弹出"
- "历史页也看不了战报"

这些跨越多个层面 — 不只是 wave 1 那种 "size=(w,h)→(bw,h)" 的统一 pattern。继续单点 dispatch implementer 修 5 次会变补丁堆叠 (andy 明确警告: "不要头痛医头脚痛医脚, 想办法制定方案或者分模块, 不要写成屎山")。

## 2. Wave 1 / Task 5 反思

| 问题 | 根因 | 教训 |
|---|---|---|
| Task 5 推测 PixelButton:146 是"添加任务点不开"的根因 | 仅看截图推测, 没诊断 | 视觉症状 ≠ 根因。必须 trace 事件链路才能确认 |
| Wave 1 一开始只 grep 了 PixelInput / PixelStepper 的同 pattern, 漏了 PixelButton | grep 范围不够广 | 同 pattern bug 应 codebase 全扫, 不只是看过的文件 |
| 5 次 dispatch 同种 implementer 流程, 每次 review 同种事 | 同类 bug 没批量化 | 同类 bug 应一次 brainstorm 设计 + 一次 implementer 批量修 |

## 3. Wave 2 待解决 bug 清单

实测 + 截图分析得出 8 个待修问题, 按猜测分类:

| # | 症状 | 分类 | 优先级 | 阻塞用户主流程? |
|---|---|---|---|---|
| B1 | 主页 "+ 添加任务" 点不开 | 事件链路 | P0 | ✅ 阻塞 |
| B2 | "结束今日并查看战报" 点了不弹 | 事件链路 | P0 | ✅ 阻塞 |
| B3 | 历史页点 day cell 看不了战报 | 事件链路 / 数据 | P0 | ✅ 阻塞 |
| B4 | 对赌页排版乱 | Layout | P1 | 否 (功能可用但难看) |
| B5 | 底部 nav 只显示 1 个 tab | Layout | P1 | 半阻塞 (无法切页) |
| B6 | 弹窗确认/取消按钮溢出 (Task 5 修了仍存在?) | Layout | P1 | 否 |
| B7 | 开发面板 layout 错乱 | Layout | P2 | 否 |
| B8 | 输入框 focus / IME 中文输入 | Input | P2 | 否 (待 B1 修了才能测) |

**"猜测分类"和"P0"是初版假设, 阶段 1 诊断后可能调整。**

## 4. 策略 — 诊断驱动 (3 阶段)

### 4.1 阶段 1: 写诊断脚手架 (~1 天)

新建模块, 目的是让所有交互留下可追踪日志, 一次操作就能定位事件链路 / layout 异常。

#### 4.1.1 `app/ui/debug/event_logger.py` (新)

装饰 PixelButton 和所有 ModalView 的关键方法, 打印事件流。

```python
# 接口设计
def install_event_logger(enabled: bool = True) -> None:
    """全局开启事件日志, 装饰 PixelButton.on_touch_down / on_press,
    ModalView.open / dismiss, TextInput.focus 等。"""

# 输出示例 (Logger.info)
# [EVT] PixelButton(text="+ 添加任务") touch_down at (210, 380) → _is_pressed=True
# [EVT] PixelButton(text="+ 添加任务") dispatch on_press
# [EVT] _open_add_dialog called
# [EVT] AddTaskDialog __init__
# [EVT] AddTaskDialog.open() → ModalView.open()
# [EVT] ModalView.open: parent=<MainWindow>, size=(420, 750)
```

#### 4.1.2 `app/ui/debug/layout_tracer.py` (新)

打印关键 widget 的 pos / size / size_hint / pos_hint, 帮诊断 layout 问题。

```python
def trace_layout(widget: Widget, label: str = "") -> None:
    """打印 widget 及其所有 children 的 pos/size/size_hint。"""

# 输出示例
# [LAY] BetScreen: pos=(0,0) size=(420,750) hint=(1,None)
# [LAY]   BoxLayout: pos=(0,?) size=(420,?) min_height=...
# [LAY]     WeekSummaryHeader: pos=... size=...
# ...
```

#### 4.1.3 在 main.py 集成 dev_panel "诊断" 按钮

dev_panel 加一个按钮 "Dump 当前 widget 树" → 调 `trace_layout(App.root)` 把整棵树打到 Logger。

#### 4.1.4 跑 app 让 andy 操作 + 收 log

andy 跑一遍主流程 (点添加任务, 点战报, 点切 tab, 等), 把 log 文件存到 `doc/wave2-traces/` 给我分析。

**阶段 1 验收**: andy 操作完, 我能从 log 看到每个 bug 的事件链路在哪一步断 / layout 数值在哪里异常。

### 4.2 阶段 2: 按 log 分类批量修 (~3 天)

#### 4.2.1 事件链路类 (B1 / B2 / B3)

如果 log 显示 PixelButton.on_press 触发了但 dialog.open() 没执行 → 修 callback bind 链
如果 PixelButton.on_press 没触发 → 修 PixelButton.on_touch_down
如果 dialog.open() 执行了但 modal 不显示 → 修 ModalView parent / size

**关键: 同类问题一次设计 1 个 fix, 而不是 B1 一个 dialog、B2 又一个 dialog 修 3 次。**

#### 4.2.2 Layout 类 (B4 / B5 / B6 / B7)

写一个轻量的 `LayoutContract` 模块, 但**不重写所有现有 dialog**:

```python
# app/ui/layout_contract.py (新, 轻量)
def ensure_dialog_card_fits(dialog: ModalView, max_width: int = 380) -> None:
    """检查 dialog 的 card width 不超 max_width, 且按钮组居中。"""

def ensure_button_group_fits(layout: BoxLayout, card_width: int) -> None:
    """检查按钮组 (2-3 个按钮) 总 width <= card_width - padding。"""

# 各 dialog 在 __init__ 末尾调 ensure_*
```

contract 是**断言型**, 失败抛出明确错误 → 测试可覆盖。

#### 4.2.3 Input 类 (B8)

B8 必须等 B1 (添加任务 dialog 能弹) 修完后才能验证。Phase 2 末尾测试。

如果 Kivy on Windows IME 真不工作, 应用 `Config.set('kivy', 'keyboard_mode', 'system')` 试一下。

### 4.3 阶段 3: 复测 + 批量 commit (~半天)

andy 重新跑全流程, 8 个 bug 全部确认修复, 一次性 commit (3-5 个 commit, 按分类拆)。

## 5. 文件改动清单

### 新增

| 路径 | 用途 |
|---|---|
| `app/ui/debug/__init__.py` | namespace |
| `app/ui/debug/event_logger.py` | 阶段 1 — 装饰事件方法记 log |
| `app/ui/debug/layout_tracer.py` | 阶段 1 — 打印 widget 树尺寸 |
| `app/ui/layout_contract.py` | 阶段 2 — Layout 断言契约 |
| `doc/wave2-traces/` | andy 收集的实测 log (gitignore) |
| `app/tests/ui/test_event_logger.py` | 阶段 1 工具测试 |
| `app/tests/ui/test_layout_contract.py` | 阶段 2 契约测试 |

### 修改

| 路径 | 改动 |
|---|---|
| `app/main.py` 或 dev_panel | 接入 install_event_logger + dump 按钮 |
| 每个 ModalView 子类 (add_task_dialog / pixel_dialog / pixel_number_dialog / settlement_dialog / report_preview / 等) | 阶段 2 末尾调 `ensure_dialog_card_fits` |
| `app/ui/components/bottom_tab_bar.py` (推测) | 修 B5 nav 显示问题 |
| `app/ui/screens/checkin_screen.py` | 修 B2 战报按钮链路 |
| `app/ui/screens/bet_screen.py` | 修 B1 添加任务按钮链路 + B4 layout |
| `app/ui/screens/history_screen.py` (推测) | 修 B3 history day click → report |

**确切修改文件清单**需阶段 1 诊断 log 后才能定。

## 6. 验收标准

| # | 验收 |
|---|---|
| 1 | 8 个 bug 全部修复, andy 实测确认 |
| 2 | 事件链路日志工具 (event_logger.py) 可以 enable/disable, dev 环境默认 enable, release 默认 disable |
| 3 | LayoutContract 模块对所有 ModalView 子类生效, 测试覆盖 (至少 6 个 dialog 的 contract 测试) |
| 4 | 全套 pytest 通过 (除已知 pre-existing 失败外, 无新增失败) |
| 5 | 主流程 E2E: 添加任务 → 完成 → 查看战报 → 历史看战报, 不卡顿不闪退 |

## 7. 不在本 spec 范围

- 后端 (BetService / CheckinService / ReportService 等) 的功能改动 — 只动 UI 层
- 新功能 (打卡相机自拍 = wave-camera 单独 spec, mascot = wave 3 单独 spec)
- 字体方向调整
- 颜色 / 视觉风格重设计

## 8. Open Questions — 留给 andy 审查时回答

1. **诊断工具是临时 (修完删除) 还是永久 (留在 codebase)?**
   建议: **永久, 但 gated by env var/config**。`SOLOIST_DEBUG=1` 时启用, 默认 release 关闭。这样以后再有交互 bug 不用重写工具。

2. **doc/wave2-traces/ 要不要纳入 git?**
   建议: 加入 .gitignore。log 可能含照片名/时间戳等隐私信息, 不入库。

3. **阶段 1 跑诊断时, 是否要 andy 用真实数据 (你自己的 morning_start/end) 还是 mock 数据?**
   建议: 真实数据, 这样 layout 计算与 bug 复现更真实。

4. **wave-camera 引入的 Camera/PhotoStrip 是否在 wave 2 LayoutContract 范围里?**
   建议: 不在。LayoutContract 只针对当前已有的 dialog/layout; wave-camera 实施时另外按 contract 写。

## 9. 排期内位置

| Wave | 内容 | 状态 |
|---|---|---|
| **Wave 2** (本 spec) | 8 个核心 UI bug 系统化修复 | **进行中** (待 spec 审查 → plan) |
| Wave-camera | 打卡自拍照片功能 | spec 已定 (`2026-06-06-checkin-camera-design.md`), 等 wave 2 完成 |
| Wave 3 | mascot 集成 | 未 brainstorm |

---

## 10. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 诊断 log 看不出根因, 阶段 1 白做 | 退路: 改用 Kivy Inspector (运行时按 F12 看 widget 树), 或加 print 到 _open_add_dialog 等关键函数 |
| LayoutContract 太抽象, 改动面大失控 | 保持 contract 只做断言, 不做布局重写。失败抛错让 dev 看, 不替 dev 决策 |
| 阶段 2 修 B1-B3 (事件链路) 发现根因不是 Wave 1 / Task 5 的 size bug | 接受。诊断驱动的目的就是不预判, 真出现就承认 wave 1 没解决全部问题, 在 wave 2 修干净 |
| B8 IME on Windows Kivy 是已知 limitation 修不了 | 加配置 keyboard_mode='system' 尝试; 不行就只在 Android 测; spec 标 "wave 2 在 Windows 桌面阶段无法完整验收 B8" |
