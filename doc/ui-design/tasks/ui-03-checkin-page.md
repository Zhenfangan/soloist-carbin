# UI-03 — 打卡主界面

> 职责：打卡页全部 UI 组件与交互流程，含时段卡片、状态框、任务清单、男友承诺、请假
> 依赖：UI-01（设计令牌 + 基础组件）、UI-02（角色 sprite）

---

## 时段卡片组件

- [ ] **3.1** 创建 `app/ui/components/period_card.py`：`PeriodCard` 类 — 单个时段卡片，三种状态：`collapsed`（小条，显示时段名+时间）、`expanded`（大卡片，含签到/签退按钮+请假入口）、`completed`（收起为状态条，显示 ✅ + 摘要）
- [ ] **3.2** 在 `period_card.py`：实现卡片展开/收起动画，300ms ease-in-out，像素阶梯式（每 8px 一步），展开时下一卡片下推
- [ ] **3.3** 在 `period_card.py`：时段头部行 — 像素时段图标（☀️ 上午 / ☀️ 下午 / 🌙 晚上）+ 时段名称 + 时间范围文字
- [ ] **3.4** 在 `period_card.py`：展开态 — 大号 `PixelButton`（签到/签退，64px 高，明黄色），根据当前状态切换文字和颜色（签到=明黄、签退=薄荷绿）
- [ ] **3.5** 在 `period_card.py`：展开态底部 — "请假"小字入口，根据窗口期显示/隐藏/灰色，点击弹出请假选项弹窗

## 状态显示框组件

- [ ] **3.6** 创建 `app/ui/components/status_box.py`：`StatusBox` 类 — 页面中部状态显示框，列出当日三个时段的实时状态
- [ ] **3.7** 在 `status_box.py`：每条状态行 — "上午：{状态文案}"，状态文案映射：正常=正常签到/签退时间、迟到=珊瑚粉色迟到标签、早退=暖橙色早退标签、旷工=西瓜红旷工标签、请假=薰衣草色已请假、拍摄=暖橙色拍摄中📸、工作中=灰色工作中...、等待=灰色等待签到...、非工作日=休息日🐼
- [ ] **3.8** 在 `status_box.py`：状态行背景色块使用功能语义色（UI-01 定义的色块色+边框色），2px 边框 + 2px 纯黑阴影

## 任务清单组件

- [ ] **3.9** 创建 `app/ui/components/task_inline_list.py`：`TaskInlineList` 类 — 嵌入打卡页的今日任务清单，最多显示 5 条
- [ ] **3.10** 在 `task_inline_list.py`：每条任务行 — `PixelCheckbox` + 任务文案，已完成项划线 + 薄荷绿色，底部"+ 添加任务"入口（触发快速添加弹窗）

## 男友承诺区

- [ ] **3.11** 创建 `app/ui/components/promise_input.py`：`PromiseInput` 类 — 弹窗样式（像素边框），包含 🐻 兜兜图标 + "设定今日奖励"标题 + 奖励描述 `PixelInput` + 数量 `PixelStepper` + 确定/跳过两个 `PixelButton`
- [ ] **3.12** 在 `promise_input.py`：确定后关闭弹窗，页面底部显示承诺卡片 — 兜兜图标 + "如果今天工作满 X 小时，奖励：[描述] × N"，旺仔(🐶)出现在旁边

## 打卡流程编排

- [ ] **3.13** 创建 `app/ui/screens/checkin_screen.py`：`CheckinScreen` 主容器 — `ScrollView` 垂直布局，自上而下：日期头 → 连续天数 → 三时段 `PeriodCard` 垂直排列 → `StatusBox` → `TaskInlineList` → 承诺区（打卡后显示）→ 战报入口按钮
- [ ] **3.14** 在 `checkin_screen.py`：日期头部 — "< 2026年6月1日 周一 >" 格式，像素字体
- [ ] **3.15** 在 `checkin_screen.py`：连续出勤天数行 — "已连续正常出勤 N 天"，薄荷绿色小字
- [ ] **3.16** 在 `checkin_screen.py`：签到按钮回调 — 调用 `CheckinService.check_in()` → 成功后触发打卡动画（按钮缩小→勾号→兜兜弹入比✌️→缩回→时段卡片收起→下一时段展开），总时长 ~2 秒
- [ ] **3.17** 在 `checkin_screen.py`：签退按钮回调 — 调用 `CheckinService.check_out()` → 自动检测当日是否所有时段完成 → 显示"结束今日并查看战报"大按钮（薄荷绿）
- [ ] **3.18** 在 `checkin_screen.py`：请假按钮回调 — 弹窗显示可选范围（morning/afternoon/all_day），根据 `get_leave_options()` 返回的可用范围启用/禁用选项
- [ ] **3.19** 在 `checkin_screen.py`：战报按钮回调 — 打开全屏 `ReportPreview` 弹层（见 UI-06 战报弹层）

## 打卡成功动画

- [ ] **3.20** 创建 `app/ui/animations/checkin_animation.py`：`checkin_success_sequence()` — 4 阶段动画：① 按钮缩小+变为勾号（150ms）→ ② 兜兜从右下角弹入（300ms spring）→ ③ 兜兜左右摇摆 2 次（1000ms）→ ④ 兜兜缩回右下角（200ms ease-out），总时长 ~2 秒
- [ ] **3.21** 在 `checkin_animation.py`：动画完成后自动收起当前时段卡片、展开下一时段卡片

## 测试

- [ ] **3.22** 编写 `app/tests/ui/test_checkin_screen.py`：模拟签到按钮点击→状态更新、模拟签退→战报入口出现、模拟请假弹窗→范围限制
- [ ] **3.23** 在 `test_checkin_screen.py`：验证 PeriodCard 三状态切换、StatusBox 文案映射正确
