# Wave 3 — UI 渲染 / 数据 flow / 回调实现 8 bug 修复

**日期**: 2026-06-07
**状态**: 设计中
**前置**: Wave 2 Phase 2 完成 (commit `8fe896d` / `a09ed6a` / `fb3554e`)
**后置**: wave-camera 设计 / 实施

## 1. 背景

Wave 2 Phase 2 修复了 14 处 size pattern bug + 战报弹窗回调 + 底部导航 bind, andy 实测验收时新发现 8 个剩余/新增 UI 问题:

| # | 描述 | 来源 |
|---|---|---|
| **B4** | 对赌页 WeekSummaryHeader 顶部字体重叠 + 上半空白 | wave 2 phase 1 提出, phase 2 部分改善 |
| **B6** | 拍摄日奖励 PixelNumberDialog 输入文字隐形 (text 属性已写入, 视觉不可见) | wave 2 phase 1 提出, phase 2 验收新发现 |
| **B7** | 设置页 dev_panel JSON 数据 Label 溢出/排版乱 | wave 2 phase 1 提出 |
| **B9** | 战报弹窗 ReportPreview 空白 (Windows 阶段无 PNG, image_path 为空) | wave 2 phase 2 Task B 留的接口缺口 |
| **B10** | 打卡页签到一个 period 后, 3 个 PeriodCard 卡片都显示签退按钮 | phase 2 验收截图新发现 |
| **B11** | 点完签退后, PeriodCard 卡片显示空白 (实际是 collapsed 时间范围, 未切到 completed 摘要) | 同上 |
| **B12** | StatusBox 第 4 卡片晚上行 "正常签到 旷工/夜:41 / 签退 16:12:42" 字体重合 + 状态自相矛盾 | 同上 |
| **B13** | 打卡页 "+ 添加任务" 按钮点不开 (`_on_task_add` 是空 stub) | wave 1 提出, 一直未修 |

Wave 2 验收已通过的: B1/B2 战报弹窗, B5 底部 nav 重叠。

## 2. 总体策略

延续 Wave 2 Phase 2 的 **batch fix by task** 模式:

- 单一 spec, 8 task 拆解, 每 task 一个 commit (E+F 合并)
- Subagent-driven impl: implementer → spec compliance reviewer → code quality reviewer
- 每 task 配单元测试, 跑全套确认无回归 (基线 24 failed / 359 passed)
- 不引入新框架/抽象, 只修触碰的文件 + 必要的接口扩展

## 3. Task 拆分

### Task A — B4 WeekSummaryHeader 字体重叠 + 上半空白

**触碰文件**: `app/ui/components/week_summary_header.py`

**根因**:
1. `_reposition_labels` 中 `_reward_label.size = (w*0.6, 24)` 上界 x=268, 与 `_rate_label.pos.x = w*0.5 = 210` 在 [210, 268] 水平重叠
2. `_rate_label.pos.y = h*0.2` 与 `_reward_label.pos.y = h*0.15` 垂直只差 4.8px, 文字渲染溢出叠加
3. height = 96 但 3 个 Label 都集中在 y < 0.55 区域, 上半 [0.55, 1.0] 留白

**修复**:
- `height` 从 96 → 72
- 重排 3 个 label 的相对位置:
  - `_completed_label.pos.y = h * 0.7` (顶部, 左侧 60%)
  - `_rate_label.pos.x = w * 0.65`, `pos.y = h * 0.3` (右侧 35%, 中部)
  - `_reward_label.pos.y = h * 0.1` (底部, 左侧 55% — 不再越线)
- `_reward_label.size = (w*0.55, 24)` (上界 x=181 < `_rate_label.x` 273)

**测试**:
- `test_week_summary_header.py::test_no_horizontal_overlap`: 实例化, set width=420, 校验 `_reward_label.x + _reward_label.width <= _rate_label.x`
- `test_week_summary_header.py::test_height_reduced_to_72`: 校验 `height == 72`

---

### Task B — B6 PixelInput 文字隐形

**触碰文件**: `app/ui/components/pixel_input.py`

**根因**:
`pixel_input.py:55` `self.padding = [CARD_PADDING // 2, CARD_PADDING // 2]` 给 2 元素列表, Kivy TextInput.padding 期望 `[left, top, right, bottom]` 4 元素. 短列表行为未定义, 实测导致 text 渲染区被 clip — text 数据写入正常 (log 显示 `text='2'`), 但视觉不可见.

**修复**:
- 改成 `self.padding = [CARD_PADDING // 2, CARD_PADDING // 2, CARD_PADDING // 2, CARD_PADDING // 2]`
- 或等价: `self.padding = [CARD_PADDING // 2] * 4`

**测试**:
- `test_pixel_input.py::test_padding_is_4_element_list`: 实例化 PixelInput, 校验 `len(input.padding) == 4` 且所有元素相等

---

### Task C — B7 dev_panel JSON Label 溢出

**触碰文件**: `app/ui/screens/settings_screen.py`

**根因**:
`_show_dev_panel` 内 `data_label` (line 579-589) 配置:
- `size_hint=(1, None)` 但**没设 height**, 默认 100
- `text_size=(None, None)` 表示 text 不受 size 约束, 自由溢出
- JSON content 行数可能 > 100/font_size, 视觉溢出卡片边界

**修复**:
- 用 ScrollView 包装 `data_label`
- `data_label.text_size = (card.width * 0.9, None)` 让 text 按宽度换行, 高度按 texture 算
- `data_label.bind(texture_size=lambda _, ts: setattr(data_label, 'size', ts))` 让 Label 高度跟实际文本
- ScrollView pos_hint/size_hint 跟原 data_label 位置一致, 内部可滚

**测试**:
- 设置页 dev_panel 测试已存在 (`test_settings_screen.py`), 加 `test_dev_panel_data_label_uses_scrollview`: 触发 _show_dev_panel, 查找 data_label 的 parent 是 ScrollView

---

### Task D — B9 ReportPreview 用 Kivy widget 渲染 ReportData

**触碰文件**:
- `app/ui/components/report_preview.py` (扩 API)
- `app/ui/screens/checkin_screen.py` (调用方传 report_data)
- `app/ui/screens/history_screen.py` (同上)

**根因**:
Wave 2 Phase 2 Task B 修复 `_on_report` / `_on_day_click` 时, `ReportPreview(image_path="")` 留了空 — PNG 在 Android 端生成, Windows 阶段 ScrollView 是空的, 用户看到 "标题 + 两按钮 + 大片白板".

**修复**:
- `ReportPreview.__init__` 加新参数 `report_data: ReportData | None = None`
- 当 `report_data is not None` 时, 在 ScrollView 内部 add 一个 vertical BoxLayout 渲染:
  - **日期行**: Label(`{date} {📸 拍摄日 | 💼 办公日}`)
  - **打卡详情**: 每个 period 一行: `{上午|下午|晚上} {checkin_time}~{checkout_time} {status_label}` (颜色按 status)
  - **奖惩汇总**: 罚款/奖励/净额, 3 行 Label, 罚款红 / 奖励绿
  - **工作时长**: 总计/加班
  - **男友承诺** (if exists): 黄色背景, 显示 reward_desc + qty + 是否兑现
  - **完成的任务列表** (if exists): 每个任务一行
  - **鼓励语**: 居中, 灰色
- `image_path` 参数保留 (Android 阶段 PNG); 当两者都给时优先 report_data (Windows + Android 都用 Kivy 渲染)
- 当两者都不给时, 显示 placeholder Label "战报数据加载中..."

调用方:
- `checkin_screen.py::_on_report`:
  ```python
  data = self._report_service.collect_data(self._date_str)
  preview = ReportPreview(report_data=data, date_str=self._date_str, ...)
  ```
- `history_screen.py::_on_day_click`: 同样改成 `collect_data(day_summary.date)`

**测试**:
- `test_report_preview.py::test_render_with_report_data`: 构造 mock ReportData, 实例化 ReportPreview, 校验 ScrollView 内有 vertical BoxLayout 且含日期/period/罚款 Label

---

### Task E — B10 + B11 PeriodCard 数据 flow 修复 (合并)

**触碰文件**: `app/ui/screens/checkin_screen.py` (可能配合 `app/ui/components/period_card.py`)

**根因**:
- B10 "签到后所有卡片显示签退按钮" 不可信 — 看 `period_card.py:316-325` action_btn 文字仅取决于 self.has_checked_in/out, 不会跨实例污染. 实际 andy 看到的可能是: 一个 period 签到后, 其他 period 卡片**没刷新数据**, 仍显示初始 "签到" 但视觉异常.
- B11 "签退后卡片空白" 根因: andy 截图显示 3 个 PeriodCard 都是 height=48 (collapsed), 显示 "09:00-12:00" 时间范围而非 "正常 09:00 / 签退 12:00" 摘要. 说明 PeriodCard 状态没切到 "completed".
- 共同根因可能: `CheckinScreen` 在 checkin/checkout 服务调用后, 没调 `PeriodCard.set_status_from_period(period_status)` 把最新数据 push 给所有 3 个卡片.

**修复**:
- 在 `CheckinScreen` 的 `_on_checkin` / `_on_checkout` 回调里, 完成 service 调用后:
  ```python
  day_status = self._checkin_service.get_day_status(self._date_str)
  for period_name, card in self._period_cards.items():
      ps = next((p for p in day_status.periods if p.period == period_name), None)
      card.set_status_from_period(ps)
  self._status_box.update_status(day_status)
  ```
- implementer 需先 read `checkin_screen.py` 的现有 refresh 逻辑 (`refresh()` / `_load_data()` 方法), 把 checkin/checkout 后 refresh 接入

**测试**:
- `test_checkin_screen.py::test_checkout_refreshes_period_cards`: mock service.checkout + service.get_day_status, 触发 _on_checkout, assert 3 个 PeriodCard 的 has_checked_in/has_checked_out 跟 mock 数据一致

---

### Task F — (合并到 E)

无独立 task. B11 与 B10 同根因, 在 Task E 一起修.

---

### Task G — B12 StatusBox 字体重合 + 状态矛盾

**触碰文件**: `app/ui/components/status_box.py`

**根因**:
- `status_w` (line 87-94) `size_hint=(1, 1)` 在 row 内 fill, 但 row height=24, 且**没设 `text_size`** → Label 默认按文本自然渲染, 长文本溢出 24px 高度边界, 视觉上"挤压"到下一行
- andy 截图 "正常签到 旷工/夜:41 / 签退 16:12:42" 看起来是: 真实文本应该是 `"正常签到 16:12:41 / 签退 16:12:42"`, 但**上一次 status update** 时 text 是 `"旷工(下午)"`. Kivy Label.text 重设应该完全替换, 但如果 Label 用 markup/multiline 且 row 高度不足, 上一帧 cache 可能与新帧重叠 (Kivy texture 缓存 artifact, 视觉残留)
- "夜" 字异常 — `PERIOD_LABELS_MAP["evening"] = "晚上"`, 不应出现 "夜". 也可能是字体渲染缺字 fallback (晚字下半部分被 clip 成"夜"形态)

**修复**:
- row height 24 → 28 (给 text 渲染留余量)
- status_w 加 `text_size=(self.width, 28)` (在 _redraw 或 bind size 里设, 因为 width 初始未知)
- status_w 加 `shorten=True, shorten_from='right'` (防止文本过长溢出时显示省略号而不是叠加)
- 或更稳健: `status_w.size_hint=(1, None); status_w.height=28; status_w.bind(width=lambda _, w: setattr(status_w, 'text_size', (w, 28)))`

**测试**:
- `test_status_box.py::test_status_w_has_text_size_set`: 实例化 StatusBox, set width, assert `status_w.text_size[0] > 0`

---

### Task H — B13 添加任务打不开 (实现 _on_task_add)

**触碰文件**: `app/ui/screens/checkin_screen.py`

**根因**:
`checkin_screen.py:598-600` `_on_task_add` 是空 stub `pass # 后续实现`.

**修复**:
- 实现 `_on_task_add`:
  ```python
  def _on_task_add(self) -> None:
      """添加任务回调 — 弹出 AddTaskDialog."""
      from app.ui.components.add_task_dialog import AddTaskDialog
      dlg = AddTaskDialog(
          on_confirm=lambda desc, qty: self._handle_task_add(desc, qty),
      )
      dlg.open()

  def _handle_task_add(self, desc: str, qty: int) -> None:
      """添加任务确认回调 — 调 service + 刷新 task list."""
      if not self._task_service:  # 或者 self._bet_service.add_task
          Logger.warning("CheckinScreen: task_service 未注入")
          return
      try:
          self._task_service.add_task(self._date_str, desc, qty)
          self.refresh()  # 刷新 task list
      except Exception as e:
          Logger.error(f"CheckinScreen: 添加任务失败 {e}")
  ```
- AddTaskDialog 的回调签名 (`on_confirm`) 需要先 verify, implementer 读 `app/ui/components/add_task_dialog.py` 确认 (可能是 `(desc: str, reward_qty: int)` 或单参数)
- task service 注入: CheckinScreen 已有 `_bet_service` 或 `_checkin_service`, 决定用哪个; 也可以让 main.py 注入新的 task_service

**测试**:
- `test_checkin_screen.py::test_on_task_add_opens_dialog`: 触发 `_on_task_add`, 校验有 AddTaskDialog 实例 open()

---

## 4. Plan 提交序列

7 个 commit, 按依赖顺序:

1. **Task B (B6 PixelInput padding)** — 无依赖, 最小改动, 先跑通确认 commit pattern OK
2. **Task A (B4 WeekSummaryHeader)** — 无依赖
3. **Task C (B7 dev_panel)** — 无依赖
4. **Task G (B12 StatusBox)** — 无依赖
5. **Task E (B10+B11 数据 flow)** — 改 CheckinScreen, 依赖 Task G (避免 merge 冲突, G 改 status_box.py, E 改 checkin_screen.py 但要 read status_box update_status 调用)
6. **Task D (B9 ReportPreview)** — 改 3 文件, 跨越多组件, 不依赖 E
7. **Task H (B13 添加任务)** — 改 checkin_screen.py, 依赖 E (避免与 E 在同文件 merge 冲突)

E 和 H 都改 checkin_screen.py — 建议串行 (E 先 commit, H 在 E 基础上修改).

## 5. 风险 / Open question

- **OQ1**: B12 "夜" 字异常如果是字体 fallback 问题 (而非渲染溢出), text_size 修复无效. implementer 在修后仍出现 "夜" 字时, 需检查 `apply_global_font()` 是否注册了完整中文字体.
- **OQ2**: Task H 的 task service 注入 — 是用现有 `_bet_service` 还是新建 `TaskService`? implementer 读现有代码后判断.
- **OQ3**: Task D 渲染的 BoxLayout 高度计算 — `ReportData` 字段动态 (periods 数 / 任务数变化), Layout 高度需 dynamic. 用 `minimum_height` binding 处理.

## 6. 验收标准

andy 重测 checklist (8 场景):

| Bug | 操作 | 期望 |
|---|---|---|
| B4 | 进对赌页 | 顶部 header 不留白, 文字不重叠 |
| B6 | 设置页 → 拍摄日奖励 → 输入数字 | 输入时文字立即可见 |
| B7 | 设置页 → 7 次版本号 → dev_panel | JSON 数据 ScrollView 可滚动, 不溢出 |
| B9 | 打卡页 → 结束今日并查看战报 | 弹窗显示完整战报内容 (日期/打卡/奖惩/工时/鼓励) |
| B10 | 上午签到 + 签退 | 下午/晚上 卡仍是 "签到" 按钮 (不是 "签退"), 自身卡显示已签退状态 |
| B11 | 签退后 | PeriodCard 显示 ✅ 摘要 (`正常 09:00 / 签退 12:00`) |
| B12 | 签退多个 period 后 | StatusBox 第 4 卡片每行单一 status, 无文字重叠/矛盾 |
| B13 | 打卡页底部 "+ 添加任务" | 弹出 AddTaskDialog |

无回归 — 24 failed / 359 passed (含本 spec 新增 6-8 个测试).
