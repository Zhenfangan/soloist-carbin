# UI-05 — 对赌页

> 职责：每周对赌任务管理界面，含任务 CRUD、进度跟踪、周结算
> 依赖：UI-01（设计令牌 + 基础组件）

---

## 本周总结浮层

- [ ] **5.1** 创建 `app/ui/components/week_summary_header.py`：`WeekSummaryHeader` 类 — 始终可见的顶部浮层，2px 边框卡片，显示："已完成 N  超额 M"（薄荷绿）、"预计奖励: +N"（明黄色）、"完成率: XX%"（进度百分比），数据通过 `BetService` 实时计算
- [ ] **5.2** 在 `week_summary_header.py`：数值变化时触发微动画 — 数字跳动（快速增减至目标值，300ms），奖励金额用明黄色加粗

## 任务列表

- [ ] **5.3** 创建 `app/ui/components/bet_task_item.py`：`BetTaskItem` 类 — 单条对赌任务行，2px 边框卡片，内容：任务描述 + 目标数量（"×5"）+ 当前进度（"2/5"）+ `PixelCheckbox` 勾选
- [ ] **5.4** 在 `bet_task_item.py`：进度增量按钮 — 数量旁 [+1] 小方块按钮（32×32），点击进度+1，达到目标自动标记完成
- [ ] **5.5** 在 `bet_task_item.py`：右滑完成整条任务 — 向右滑动 Gesture → 整条划掉（删除线 + 灰色）+ 旺仔(🐶)从侧边滑入摇尾巴，动画 400ms
- [ ] **5.6** 在 `bet_task_item.py`：左滑删除 — 向左滑动 Gesture → 露出红色删除按钮，点击确认删除

## 任务管理

- [ ] **5.7** 创建 `app/ui/components/add_task_dialog.py`：`AddTaskDialog` 类 — 像素弹窗，包含任务描述 `PixelInput` + 目标数量 `PixelStepper` + 确认/取消按钮，调用 `BetService.create_task()`
- [ ] **5.8** 在 `add_task_dialog.py`：输入验证 — 任务描述非空（最少 1 字）、目标数量 ≥1（步进器下限 1）

## 赏罚设置区

- [ ] **5.9** 创建 `app/ui/components/bet_config_section.py`：`BetConfigSection` — 可折叠区域（`CollapsibleGroup`），折叠态显示"本周赏罚设置 ▶"，展开态显示：完成奖励金额、超额单任务奖励、未完成惩罚金额，每项旁有编辑按钮
- [ ] **5.10** 在 `bet_config_section.py`：编辑按钮点击 → 弹出数字输入弹窗（`PixelInput` + 数字键盘限制），调用 `BetService.set_week_config()`

## 周结算

- [ ] **5.11** 在 `bet_task_item.py` 所在页面：底部 "周结算" 大按钮 — 周日可用（明黄色），其他时间灰色 + 提示"周日结算"，点击弹出 `SettlementDialog`
- [ ] **5.12** 创建 `app/ui/components/settlement_dialog.py`：`SettlementDialog` 类 — 像素弹窗，展示：完成 N/M / 超额 N、奖励 +N + 超额 = +Total、惩罚 -N、净额 +N，取消 + 确认结算两个按钮
- [ ] **5.13** 在 `settlement_dialog.py`：确认后调用 `BetService.settle_week()` → 团团(🐼)抱星星动画（4 帧冒出→抱星→转1→转2，每帧 375ms，总 1500ms）

## 页面组装

- [ ] **5.14** 创建 `app/ui/screens/bet_screen.py`：`BetScreen` 主容器 — `ScrollView` 垂直布局：`WeekSummaryHeader` → 任务列表（`BetTaskItem` 循环）→ "+ 添加任务"入口 → `BetConfigSection`（折叠）→ "周结算"按钮

## 测试

- [ ] **5.15** 编写 `app/tests/ui/test_bet_screen.py`：添加任务→列表渲染、勾选进度→计数更新、右滑完成→旺仔动画触发、左滑删除→任务移除
- [ ] **5.16** 在 `test_bet_screen.py`：周结算按钮状态（周日可用/其他灰掉）、弹窗金额计算正确、确认结算→数据写入
