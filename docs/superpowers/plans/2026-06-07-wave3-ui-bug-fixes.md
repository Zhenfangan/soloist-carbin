# Wave 3 UI Bug Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 2026-06-07 手动 UI 测试发现的 12 个 bug — 覆盖 Wave 3 原修复遗漏 + 新发现的渲染、刷新、布局问题。

**Architecture:** 按严重度分 4 个 Phase 顺序执行 — P0 阻断 → P1 严重 → P2 体验 → P3 优化。每个 task 独立可测、可回滚，遵循 TDD 流程：失败测试 → 实现 → 通过测试 → 手动视觉验证 → commit。

**Tech Stack:** Python 3.12 + Kivy 2.3.1 + pytest + ruff + mypy。所有视觉验证用 `SOLOIST_DEBUG=1 python -m app.main`，日志写入 `debug.log`。

**前置约定:**
- 执行前确认 `git status` 干净
- 每次手动验证前杀掉旧进程：`taskkill //F //IM python.exe` (Windows)
- 启动命令：`SOLOIST_DEBUG=1 PYTHONIOENCODING=utf-8 PYTHONUNBUFFERED=1 python -m app.main > debug.log 2>&1 &`
- 验证日志：`grep "EVT\|ERROR" debug.log`

---

## Phase P0 — 阻断性修复 (必须先做)

### Task 1: 修复 PixelInput 文字渲染失败

**根因:** `pixel_input.py:82-103` 的 `_redraw` 把整面 `CARD_WHITE` 矩形画在 `canvas.before`，并且 `__init__` 设了 `background_normal=""` + `background_color=(0,0,0,0)`。TextInput 内部 cursor/text layout 依赖 background 的存在做坐标计算，置空后文字渲染管线损坏。

**Files:**
- Modify: `app/ui/components/pixel_input.py:35-103`
- Test: `app/tests/ui/test_pixel_input_render.py` (新建)

- [ ] **Step 1.1: 写失败测试 — 验证背景透明且 canvas.before 不画整面填充矩形**

新建 `app/tests/ui/test_pixel_input_render.py`:

```python
"""PixelInput 渲染回归测试 — 防止 _redraw 覆盖 TextInput 文字层。"""

from __future__ import annotations

import pytest
from kivy.graphics import Rectangle

from app.ui.components.pixel_input import PixelInput
from app.ui.tokens import CARD_WHITE


@pytest.fixture
def pi() -> PixelInput:
    p = PixelInput(hint_text="测试 hint")
    p.size = (200, 40)
    p.pos = (0, 0)
    p._redraw()
    return p


def test_canvas_before_has_no_full_fill_rect(pi: PixelInput) -> None:
    """canvas.before 不应该画一个覆盖整面的填充矩形(那会盖住 TextInput 文字)。"""
    full_fills = [
        c for c in pi.canvas.before.children
        if isinstance(c, Rectangle)
        and c.size == (200, 40)
        and c.pos == (0, 0)
    ]
    assert len(full_fills) == 0, (
        f"canvas.before 仍有 {len(full_fills)} 个整面填充矩形, "
        "会覆盖 TextInput 文字层"
    )


def test_text_property_reflects_input(pi: PixelInput) -> None:
    """输入文本应该正确写入 .text 与 .value。"""
    pi.text = "hello"
    assert pi.text == "hello"
    assert pi.value == "hello"


def test_hint_text_is_set(pi: PixelInput) -> None:
    """hint_text 应该正确赋值给 TextInput 的 hint_text。"""
    assert pi.hint_text == "测试 hint"
```

- [ ] **Step 1.2: 运行测试验证失败**

```bash
pytest app/tests/ui/test_pixel_input_render.py::test_canvas_before_has_no_full_fill_rect -v
```

Expected: FAIL with assertion about `仍有 1 个整面填充矩形`

- [ ] **Step 1.3: 修 `pixel_input.py` — `_redraw` 只画边框、不画整面背景**

修改 `app/ui/components/pixel_input.py:35-103`:

```python
class PixelInput(TextInput):
    def __init__(
        self,
        hint_text: str = "",
        value: str = "",
        password: bool = False,
        on_change: Callable[[str], Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(text=value, password=password, **kwargs)
        self.hint_text = hint_text
        self._on_change_cb = on_change

        # 关键修复: 不再把 background_normal/active 置空、background_color 置透明
        # 改成让 TextInput 用纯色背景, PixelInput 只在 canvas.before 画边框
        self.background_normal = ""  # 不要图片背景
        self.background_active = ""
        self.background_color = self._to_rgba(CARD_WHITE)  # 用纯色做背景
        self.foreground_color = self._to_rgba(TEXT_BROWN)
        self.hint_text_color = self._to_rgba(TEXT_GRAY)
        self.cursor_color = self._to_rgba(TEXT_BROWN)
        self.font_size = FONT_SIZE_BODY
        self.padding = [CARD_PADDING // 2, CARD_PADDING // 2, CARD_PADDING // 2, CARD_PADDING // 2]
        self.multiline = False

        self._border_light = CARD_WHITE
        self._border_dark = COLORS["CARD_SHADOW"]

        self.bind(text=self._on_text_change)
        self.bind(pos=self._redraw, size=self._redraw)

    def _redraw(self, *args: Any) -> None:
        """只画 2px 内凹边框, 不画整面背景(避免盖住 TextInput 文字层)。"""
        self.canvas.before.clear()
        x, y = self.pos
        w, h = self.size
        bw = BORDER_WIDTH

        with self.canvas.before:
            # 暗面 top
            Color(*self._to_rgba(self._border_dark))
            Rectangle(pos=(x, y + h - bw), size=(w, bw))
            # 暗面 left
            Rectangle(pos=(x, y), size=(bw, h))
            # 亮面 bottom
            Color(*self._to_rgba(self._border_light))
            Rectangle(pos=(x, y), size=(w, bw))
            # 亮面 right
            Rectangle(pos=(x + w - bw, y), size=(bw, h))
```

- [ ] **Step 1.4: 运行测试验证通过**

```bash
pytest app/tests/ui/test_pixel_input_render.py -v
```

Expected: all 3 tests PASS

- [ ] **Step 1.5: 手动视觉验证**

```bash
taskkill //F //IM python.exe 2>&1 | head -3
rm -f debug.log
SOLOIST_DEBUG=1 PYTHONIOENCODING=utf-8 PYTHONUNBUFFERED=1 python -m app.main > debug.log 2>&1 &
```

操作: 打卡页 → 点 "+ 添加任务" → 在输入框输入"测试"

验证标准:
- 输入框能看到 hint "例如: 写 3 篇文章"（输入前）
- 输入"测试"后能看到棕色"测试"文字
- 光标颜色正常

如果仍然不可见, 回滚此 task, 改为在 `background_color` 用 `(1,1,1,1)` 纯白 RGBA 直接传 + 检查是否 fonts.py 替换 Roboto 后 TextInput hint_text 也跟着失效

- [ ] **Step 1.6: 跑现有 PixelInput 测试套件确保无回归**

```bash
pytest app/tests/ui/ -k "pixel_input" -v
```

Expected: 所有原有 PixelInput 测试 PASS（如有失败说明改动破坏了内边距/边框等其他特性）

- [ ] **Step 1.7: Commit**

```bash
git add app/ui/components/pixel_input.py app/tests/ui/test_pixel_input_render.py
git commit -m "fix(ui): PixelInput 文字渲染失败 — _redraw 不再画整面白底覆盖文字层"
```

---

### Task 2: AddTaskDialog 添加后 TaskInlineList 不刷新

**根因:** `checkin_screen.py:611-622` 的 `_handle_task_add` 只调 `bet_service.create_task()` 存数据库，没刷新 `self._task_list`。任务进库后 UI 不感知。

**Files:**
- Modify: `app/ui/screens/checkin_screen.py:611-622, 249-280` (_load_data)
- Test: `app/tests/ui/test_checkin_task_refresh.py` (新建)

- [ ] **Step 2.1: 读现有 `_load_data` 看任务加载路径**

```bash
grep -n "_task_list\|set_tasks\|_load_data" app/ui/screens/checkin_screen.py | head -20
```

记录: `_task_list.set_tasks(...)` 在何处调用。

- [ ] **Step 2.2: 写失败测试**

新建 `app/tests/ui/test_checkin_task_refresh.py`:

```python
"""验证 CheckinScreen._handle_task_add 添加后刷新 TaskInlineList。"""

from __future__ import annotations

from unittest.mock import MagicMock

from app.ui.screens.checkin_screen import CheckinScreen


def test_handle_task_add_refreshes_task_list() -> None:
    """添加任务后 _task_list.set_tasks 应被调用。"""
    bet_svc = MagicMock()
    bet_svc.get_week_tasks.return_value = [
        {"id": 1, "desc": "新任务", "done": False, "current_qty": 0, "target_qty": 1}
    ]
    bet_svc.create_task = MagicMock()

    screen = CheckinScreen(bet_service=bet_svc)
    screen._date_str = "2026-06-07"
    screen._task_list = MagicMock()

    screen._handle_task_add("新任务", 1)

    bet_svc.create_task.assert_called_once()
    screen._task_list.set_tasks.assert_called_once()
```

- [ ] **Step 2.3: 运行测试验证失败**

```bash
pytest app/tests/ui/test_checkin_task_refresh.py -v
```

Expected: FAIL — `set_tasks` 没被调用

- [ ] **Step 2.4: 修 `_handle_task_add` 加刷新**

修改 `app/ui/screens/checkin_screen.py:611-622`:

```python
def _handle_task_add(self, desc: str, qty: int) -> None:
    """添加任务确认回调 — 调 bet_service 创建任务 + 刷新列表。"""
    if not self._bet_service:
        Logger.warning("CheckinScreen: bet_service 未注入, 任务仅本地显示")
        return
    try:
        from datetime import datetime, timedelta
        dt = datetime.strptime(self._date_str, "%Y-%m-%d")
        week_start = (dt - timedelta(days=dt.weekday())).strftime("%Y-%m-%d")
        self._bet_service.create_task(week_start, desc, qty)
        # 修复: 添加后立即刷新 UI 列表
        tasks = self._bet_service.get_week_tasks(week_start)
        self._task_list.set_tasks([
            {"id": t.id, "desc": t.desc, "done": getattr(t, "done", False)}
            for t in tasks
        ])
    except Exception as e:
        Logger.error(f"CheckinScreen: 添加任务失败 {e}")
```

注意: `tasks` 字段映射需要根据 `BetService.get_week_tasks` 返回类型调整。先确认它返回 `list[BetTask]` 对象还是 `list[dict]`。

- [ ] **Step 2.5: 运行测试验证通过**

```bash
pytest app/tests/ui/test_checkin_task_refresh.py -v
```

Expected: PASS

- [ ] **Step 2.6: 手动验证 (依赖 Task 1 修复)**

启动 app → 打卡页 → "+ 添加任务" → 输入"测试任务" + 数量 2 → 确认

验证: 弹窗关闭后, 打卡页"今日任务"区域立刻出现"测试任务"行

- [ ] **Step 2.7: Commit**

```bash
git add app/ui/screens/checkin_screen.py app/tests/ui/test_checkin_task_refresh.py
git commit -m "fix(ui): CheckinScreen 添加任务后立即刷新 TaskInlineList"
```

---

### Task 3: BetScreen 5 空白卡片回归验证 + 排查

**根因假设:** 截图2 显示对赌页 5 个 BetTaskItem 卡片有边框但文字不显示。若 BetTaskItem 内部用 PixelInput 显示任务名, Task 1 修复后应自然恢复。否则另查 BetTaskItem 渲染。

**Files:**
- Investigate: `app/ui/components/bet_task_item.py`
- Test: `app/tests/ui/test_bet_task_item_render.py` (条件新建)

- [ ] **Step 3.1: 检查 BetTaskItem 是否用 PixelInput**

```bash
grep -n "PixelInput\|TextInput\|Label\|font_name" app/ui/components/bet_task_item.py | head -20
```

如果发现 `PixelInput`, 跳到 Step 3.4 直接手动回归。
如果没有, 继续 Step 3.2 深查。

- [ ] **Step 3.2: 读 BetTaskItem 完整实现**

```bash
wc -l app/ui/components/bet_task_item.py
```

读全文, 找出文字 widget (Label / TextInput) 是否被 canvas.before 覆盖。

- [ ] **Step 3.3: 如发现根因 — 写测试 + 修复**

参考 Task 1 的模式: 写"canvas.before 不画整面填充"测试 → 验证失败 → 修 canvas.before → 验证通过。

- [ ] **Step 3.4: 手动视觉验证 — 切到对赌页**

启动 app → 底部"对赌" tab → 看是否有任务卡片

验证标准:
- 若之前测试时添加过任务 (Task 2 修复后能正确添加) → 应看到任务描述、数量、进度条
- 若是从无任务开始 → 任务列表应为空, 不应有"5 个空白卡片"

如果仍然 5 空白卡片, dump widget tree 排查:

```bash
# 在 app 中: 设置 → 开发面板 → "Dump widget tree"
# 然后查看打出来的 widget 名字
```

- [ ] **Step 3.5: Commit (如有修改)**

```bash
git add app/ui/components/bet_task_item.py app/tests/ui/test_bet_task_item_render.py
git commit -m "fix(ui): BetTaskItem 文字渲染回归 (Task 1 关联)"
```

如无代码修改, 跳过此 step, 在 commit message 记录"验证后 Task 1 修复已覆盖"。

---

## Phase P1 — 严重 (P0 完成后)

### Task 4: PeriodCard "completed" 状态隐藏 _action_btn

**根因:** `period_card.py:316-325` 当 `_has_checked_out=True` 时, `_action_btn.text="[OK] 已签退"` + `disabled=True`, 但 button 没隐藏, 仍以 `size_mode="large"` + `PRIMARY_YELLOW` 黄底显示, 文字 disabled 灰色在黄底上几乎看不清。

**Files:**
- Modify: `app/ui/components/period_card.py:316-325, 250-280` (complete 方法)
- Test: `app/tests/ui/test_period_card_completed.py` (新建)

- [ ] **Step 4.1: 写失败测试**

新建 `app/tests/ui/test_period_card_completed.py`:

```python
"""PeriodCard completed 状态下隐藏 _action_btn 大黄块。"""

from __future__ import annotations

from app.ui.components.period_card import PeriodCard


def test_completed_state_hides_action_btn() -> None:
    """已签退后 _action_btn 应该 opacity=0 + disabled。"""
    card = PeriodCard(period_name="evening")
    card._has_checked_in = True
    card._has_checked_out = True
    card._card_state = "completed"
    card._refresh_action_btn()

    assert card._action_btn.opacity == 0, "已签退后按钮应该不可见"
    assert card._action_btn.disabled is True, "已签退后按钮应该 disabled"
```

- [ ] **Step 4.2: 运行测试验证失败**

```bash
pytest app/tests/ui/test_period_card_completed.py -v
```

Expected: FAIL — opacity 不为 0 (或方法 `_refresh_action_btn` 不存在)

- [ ] **Step 4.3: 修 `period_card.py` 把已签退状态的按钮隐藏**

修改 `app/ui/components/period_card.py` 在原 `_refresh_action_btn`（在 line 316 附近）方法中:

```python
def _refresh_action_btn(self) -> None:
    """根据当前状态更新 _action_btn 文字/颜色/可见性。"""
    if self._has_checked_in and not self._has_checked_out:
        self._action_btn.text = "签退"
        self._action_btn.set_color(DOPAMINE_COLORS["mint"]["light"])
        self._action_btn.disabled = False
        self._action_btn.opacity = 1
    elif self._has_checked_out:
        # 修复: 已签退后隐藏大黄块按钮, 状态由 _check_label 显示
        self._action_btn.text = ""
        self._action_btn.disabled = True
        self._action_btn.opacity = 0
        self._action_btn.size_hint_y = None
        self._action_btn.height = 0
    else:
        self._action_btn.text = "签到"
        self._action_btn.set_color(COLORS["PRIMARY_YELLOW"])
        self._action_btn.disabled = not self._is_current
        self._action_btn.opacity = 1
```

定位原方法的关键字: `self._action_btn.text = "签退"` 上下文。

- [ ] **Step 4.4: 运行测试验证通过**

```bash
pytest app/tests/ui/test_period_card_completed.py app/tests/ui/test_period_card.py -v
```

Expected: 新测试 PASS, 原 period_card 套件无回归

- [ ] **Step 4.5: 手动视觉验证**

启动 app → 打卡页

验证标准:
- 上午/下午绿框 PeriodCard 仍正常 (collapsed, 显示签到+签退时间 + 绿色 [OK])
- 晚上 PeriodCard 不再出现大黄块, 取而代之是简洁的 collapsed 状态显示

- [ ] **Step 4.6: Commit**

```bash
git add app/ui/components/period_card.py app/tests/ui/test_period_card_completed.py
git commit -m "fix(ui): PeriodCard 已签退后隐藏 _action_btn 大黄块"
```

---

### Task 5: StatusBox "晚上" 行文字重叠

**根因:** `status_box.py:78-99` row 内 `label_w width=50` + `status_w shorten=True` 但因为 `status_w` 的 `text_size` 在 `width` bind 里设置成 `(w.width, 28)`, 28 高度太小 + shorten 没正确生效, 导致"正常签到 16:12:41 / 签退 12:42" 后半段视觉重叠。

**Files:**
- Modify: `app/ui/components/status_box.py:71-103`
- Test: `app/tests/ui/test_status_box_overflow.py` (修改已存在的)

- [ ] **Step 5.1: 写失败测试**

修改/补充 `app/tests/ui/test_status_box_overflow.py`:

```python
def test_long_status_text_does_not_overflow_row() -> None:
    """长状态文字应该被 shorten 截断, 不溢出 status_w 边界。"""
    box = StatusBox()
    box.size = (380, 130)
    box.do_layout()

    status_w = box._status_widgets["evening"]
    status_w.text = "正常签到 16:12:41 / 签退 12:42 / 拍摄完成"

    # 触发 text_size 计算
    status_w.width = 280
    status_w.texture_update()

    # 验证: 文字被 shorten 后 texture 宽度不超过 status_w.width
    assert status_w.texture_size[0] <= 280, (
        f"文字 texture 宽 {status_w.texture_size[0]} > status_w 宽 280, 未被 shorten"
    )
```

- [ ] **Step 5.2: 运行测试验证失败**

```bash
pytest app/tests/ui/test_status_box_overflow.py::test_long_status_text_does_not_overflow_row -v
```

- [ ] **Step 5.3: 修 `status_box.py` 调整 shorten 配置**

修改 `app/ui/components/status_box.py:88-100`:

```python
status_w = Label(
    text="等待签到...",
    font_size=FONT_SIZE_BODY,
    color=self._to_rgba(TEXT_GRAY),
    size_hint=(1, None),
    height=28,
    halign="left",
    valign="middle",
    shorten=True,
    shorten_from="right",
    text_size=(None, 28),  # 初始即设, 不依赖 bind
)
# 关键修复: 用 width + size 同时 bind, 保证 text_size 跟 width 同步
def _bind_text_size(w: Any, _: Any) -> None:
    w.text_size = (max(w.width - 4, 1), 28)

status_w.bind(width=_bind_text_size)
```

将原本 lambda bind 替换成显式 `_bind_text_size` 函数, 并加 `max(w.width - 4, 1)` 留 4px 缓冲。

- [ ] **Step 5.4: 运行测试验证通过**

```bash
pytest app/tests/ui/test_status_box_overflow.py -v
```

Expected: PASS

- [ ] **Step 5.5: 手动视觉验证**

启动 app → 打卡页

验证标准:
- StatusBox 三行 (上午/下午/晚上) 文字不重叠
- 长文字 (如"正常签到 16:12:41 / 签退 12:42") 被 "..." 截断

- [ ] **Step 5.6: Commit**

```bash
git add app/ui/components/status_box.py app/tests/ui/test_status_box_overflow.py
git commit -m "fix(ui): StatusBox status_w shorten 配置修复, 长文字不再溢出"
```

---

### Task 6: 历史页时段顺序错乱

**根因:** 截图 1 显示历史页卡片"下午:正常 下午:未打卡 上午:正常" — 时段顺序乱 (重复"下午"且把"上午"排到末尾)。需排查 DayCard 内部 sort 顺序或 HistoryService 返回数据顺序。

**Files:**
- Investigate: `app/ui/components/day_card.py`, `app/services/history_service.py`
- Modify: 根据排查结果决定
- Test: `app/tests/ui/test_day_card_period_order.py` (新建)

- [ ] **Step 6.1: 检查 HistoryService 返回数据顺序**

```bash
grep -n "morning\|afternoon\|evening\|period" app/services/history_service.py | head -20
```

记录 service 返回的 periods 顺序是否固定为 morning → afternoon → evening。

- [ ] **Step 6.2: 检查 DayCard 渲染时段的逻辑**

```bash
grep -n "periods\|morning\|afternoon\|evening\|sort" app/ui/components/day_card.py | head -20
```

- [ ] **Step 6.3: 写失败测试**

新建 `app/tests/ui/test_day_card_period_order.py`:

```python
"""DayCard 时段渲染顺序回归测试 — 必须 上午 → 下午 → 晚上。"""

from __future__ import annotations

from app.models.history import DayCard as DayCardModel, PeriodSummary
from app.ui.components.day_card import DayCard


def test_day_card_renders_periods_in_morning_afternoon_evening_order() -> None:
    """无论输入数据顺序如何, 渲染必须按 上午→下午→晚上。"""
    # 故意打乱顺序
    model = DayCardModel(
        date="2026-06-04",
        weekday="周四",
        periods=[
            PeriodSummary(period="evening", status="normal", time="20:00"),
            PeriodSummary(period="morning", status="normal", time="09:00"),
            PeriodSummary(period="afternoon", status="late", time="14:30"),
        ],
        reward=0,
        penalty=0,
    )
    card = DayCard(card=model)

    # 检查渲染顺序
    period_labels = [w.text for w in card._period_widgets]
    assert period_labels[0].startswith("上午"), f"第一项应是上午, 实际: {period_labels[0]}"
    assert period_labels[1].startswith("下午"), f"第二项应是下午, 实际: {period_labels[1]}"
    assert period_labels[2].startswith("晚上"), f"第三项应是晚上, 实际: {period_labels[2]}"
```

注意: `_period_widgets` 属性名根据 DayCard 实际实现调整。

- [ ] **Step 6.4: 运行测试验证失败**

```bash
pytest app/tests/ui/test_day_card_period_order.py -v
```

- [ ] **Step 6.5: 修 DayCard 渲染前 sort periods**

在 DayCard 渲染时段的方法 (通常叫 `_build_periods` 或类似) 开头加:

```python
PERIOD_ORDER = {"morning": 0, "afternoon": 1, "evening": 2, "night": 2}

def _build_periods(self, periods: list[PeriodSummary]) -> None:
    # 强制按时段固定顺序排序, 不依赖输入数据
    sorted_periods = sorted(periods, key=lambda p: PERIOD_ORDER.get(p.period, 99))
    for p in sorted_periods:
        # ... 原渲染逻辑
        pass
```

- [ ] **Step 6.6: 运行测试验证通过**

```bash
pytest app/tests/ui/test_day_card_period_order.py -v
```

- [ ] **Step 6.7: 手动验证**

启动 app → 底部"历史" tab → 看 6月4日、5日、6日卡片

验证: 三个时段顺序统一为"上午 / 下午 / 晚上"

- [ ] **Step 6.8: Commit**

```bash
git add app/ui/components/day_card.py app/tests/ui/test_day_card_period_order.py
git commit -m "fix(ui): DayCard 时段渲染固定 morning→afternoon→evening 顺序"
```

---

## Phase P2 — 体验问题 (P1 完成后)

### Task 7: 历史页底部"本周合计"被遮挡

**根因:** 截图 1 显示 "本周合计: -200.0" 横在 navtab 上方但被一个黄色装饰条挡住。需检查 HistoryScreen footer 的 z-order 和 padding。

**Files:**
- Modify: `app/ui/screens/history_screen.py` (footer 位置)
- Test: 手动验证为主

- [ ] **Step 7.1: 找 footer 渲染代码**

```bash
grep -n "本周合计\|total\|footer\|summary" app/ui/screens/history_screen.py
```

- [ ] **Step 7.2: 修 footer**

可能需要:
- 把 footer 移到 ScrollView 外, 放在主 BoxLayout 的最底层
- 或者给 footer 加 padding-bottom 避开 navtab

具体修改取决于现有结构, 此 task 在执行时根据代码现状决定。

- [ ] **Step 7.3: 手动验证**

启动 app → 历史 → 滚到最底

验证: "本周合计: -200.0" 完整可见, 不被遮挡

- [ ] **Step 7.4: Commit**

```bash
git add app/ui/screens/history_screen.py
git commit -m "fix(ui): 历史页底部本周合计 z-order/padding 修复"
```

---

### Task 8: 历史页 周/月/年 tab 选中态缺失

**根因:** 截图 1 顶部三个 tab 视觉上没区分当前选中态。

**Files:**
- Modify: `app/ui/components/history_tabs.py`
- Test: `app/tests/ui/test_history_tabs_selection.py` (新建或修改)

- [ ] **Step 8.1: 读 HistoryTabs 实现**

```bash
wc -l app/ui/components/history_tabs.py
```

- [ ] **Step 8.2: 写失败测试 — 选中 tab 应有视觉标记 (如下划线/底色)**

```python
def test_active_tab_has_visual_indicator() -> None:
    """当前选中 tab 应该有 active 视觉(canvas instruction)。"""
    tabs = HistoryTabs(on_tab_change=lambda i: None)
    tabs.set_active(0)  # 切到周

    week_tab = tabs._tab_widgets[0]
    # 验证 canvas 里有 active indicator (例如下划线 Rectangle)
    has_indicator = any(
        c.__class__.__name__ == "Rectangle"
        and hasattr(week_tab, "_active_indicator")
        for c in week_tab.canvas.after.children
    )
    assert has_indicator, "active tab 应有视觉指示器"
```

- [ ] **Step 8.3: 实现 active 状态视觉**

在 HistoryTabs 的 `set_active(index)` 方法里给当前 tab 加底色或下划线 Rectangle, 切换时清掉非 active 的。

- [ ] **Step 8.4: 手动验证 — 切 tab 看视觉变化**

- [ ] **Step 8.5: Commit**

```bash
git add app/ui/components/history_tabs.py app/tests/ui/test_history_tabs_selection.py
git commit -m "fix(ui): HistoryTabs 加 active tab 视觉指示器"
```

---

### Task 9: 对赌页底部 cream 区残留 "0/"

**根因:** 截图 2 底部"周结算"按钮下方有一段 cream 色背景区域 + 飘着 "0/" 文字。需排查 BetScreen 末尾是否有未隐藏的 widget 或 padding 异常。

**Files:**
- Investigate: `app/ui/screens/bet_screen.py:125-149` (周结算 + settle_hint 之后)

- [ ] **Step 9.1: 读 BetScreen 末尾**

```bash
sed -n '140,200p' app/ui/screens/bet_screen.py | head -60
```

- [ ] **Step 9.2: 定位 "0/" 文字来源**

```bash
grep -rn "f\"{.*}/\\|f'{.*}/" app/ui/components/ app/ui/screens/ | head -10
```

可能是 "0/N" 格式的进度文字, 其某个 widget 没被加进容器但 canvas 残留。

- [ ] **Step 9.3: 修 — 隐藏多余 widget 或调整 BetScreen padding**

具体修改根据排查结果。

- [ ] **Step 9.4: 手动验证**

启动 app → 对赌 tab → 滚到最底

验证: "周结算" 按钮下方只有结算提示文字 + 留白, 无 cream 区残留

- [ ] **Step 9.5: Commit**

```bash
git add app/ui/screens/bet_screen.py
git commit -m "fix(ui): BetScreen 底部 cream 区残留 0/ 文字清理"
```

---

### Task 10: AddTaskDialog 全屏尺寸优化

**根因:** 日志显示 ModalView `size=[420, 750]` 全屏。代码内 card 本身是 320x280 居中, 但 ModalView 全屏导致点击 card 外部直接 dismiss。需确认设计意图。

**Files:**
- Modify: `app/ui/components/add_task_dialog.py:42-60`
- Test: 手动确认

- [ ] **Step 10.1: 与设计意图对照**

确认 AddTaskDialog 是否应该:
- A. 全屏遮罩 + 居中小卡片 (当前行为, OK)
- B. 半屏 popup 风格

如果 A: 此 task 无需修改, 仅记录"已确认设计如此"。

如果 B: 修 ModalView size_hint 改成 (None, None) + size=(card_w, card_h)。

- [ ] **Step 10.2: 视情况修改或 close 此 task**

- [ ] **Step 10.3: Commit (如有修改)**

---

## Phase P3 — 优化 (可延后)

### Task 11: ReportPreview 版面设计优化

**Files:**
- Modify: `app/ui/components/report_preview.py`

- [ ] **Step 11.1: 跑 design-is skill 做 Rams 原则审计**

```
# 在 Claude Code 中:
/design-is
```

针对 ReportPreview 截图做设计审计, 输出 redesign /make-plan prompt。

- [ ] **Step 11.2: 根据 design-is 输出生成子 plan, 再独立执行**

此 task 输出一个 sub-plan, 不在本 plan 内直接实现细节。

---

### Task 12: CheckinScreen streak_label 空白行优化

**根因:** `checkin_screen.py:109-118` `_streak_label` 默认 height=20, 数据为空时空占 20px。

**Files:**
- Modify: `app/ui/screens/checkin_screen.py:109-118`

- [ ] **Step 12.1: 改 streak_label 默认 height=0**

修改 `app/ui/screens/checkin_screen.py:109-118`:

```python
self._streak_label = Label(
    text="",
    font_size=FONT_SIZE_SMALL,
    color=self._to_rgba(DOPAMINE_COLORS["mint"]["light"]),
    size_hint=(1, None),
    height=0,  # 修复: 空数据时不占高度
    halign="center",
    valign="middle",
)
self._container.add_widget(self._streak_label)
```

并在 `_load_data` 设置 text 时同步调整 height:

```python
# 在 _load_data 设置 _streak_label.text 的位置后:
self._streak_label.height = 20 if self._streak_label.text else 0
```

- [ ] **Step 12.2: 手动验证**

启动 app → 打卡页

验证: 没有连续出勤天数时, 日期下方紧接 morning PeriodCard, 无空白行

- [ ] **Step 12.3: Commit**

```bash
git add app/ui/screens/checkin_screen.py
git commit -m "fix(ui): CheckinScreen streak_label 空数据时不占高度"
```

---

## Plan 完成后

### 最终回归测试

- [ ] 跑全套 UI 测试

```bash
pytest app/tests/ui/ -v
```

Expected: 所有测试 PASS (或仅遗留与本 plan 无关的失败)

- [ ] 跑 mypy + ruff

```bash
mypy app/
ruff check app/
```

- [ ] 手动巡检 5 个页面

按顺序检查:
1. 打卡页 — 三时段卡 + StatusBox + TaskInlineList
2. 历史页 — 周/月/年 tab + 时段顺序 + 本周合计
3. 对赌页 — WeekSummaryHeader + 任务卡 + 周结算
4. 设置页 — 各 setting row
5. 弹窗 — AddTaskDialog + ReportPreview + SettlementDialog

每页截图存 `doc/ui-design/testreport/2026-06-07-post-fix/`

- [ ] 创建合并 commit / PR

```bash
git log --oneline | head -15
git push origin HEAD
```

---

## 风险与回滚

- **Task 1 (PixelInput)** 改动影响所有 PixelInput 实例。如果发现别处 PixelInput 视觉异常, 先 `git revert` Task 1, 改为只在 AddTaskDialog 内 PixelInput 加特殊处理
- **Task 4 (PeriodCard)** 隐藏 _action_btn 后, 需确认"已签退"状态的视觉补偿 (如 _check_label 是否足够清晰)
- **Task 6 (时段顺序)** 修改后, 若历史页有月/年视图也展示时段, 需确保同步修复

---

## 自检 (writing-plans 要求)

### 1. Spec coverage 检查
原 15 个任务对应 plan task:
- #1 B4 WeekSummaryHeader — 测试已确认无重叠, 无需修
- #2 B6 PixelInput — Task 1
- #3 B9 ReportPreview — Task 11
- #4 B10+B11 refresh — Task 2 间接覆盖 (CheckinScreen 刷新)
- #5 B12 StatusBox — Task 5
- #6 B13 AddTaskDialog 弹出 — Task 1+2 覆盖 (弹出已 OK, 内部 input + 刷新已覆盖)
- #7 晚上 PeriodCard — Task 4
- #8 历史页时段顺序 — Task 6
- #9 历史页本周合计 — Task 7
- #10 历史页 tab 选中态 — Task 8
- #11 对赌页 5 空白卡片 — Task 3
- #12 对赌页底部残留 — Task 9
- #13 AddTaskDialog 尺寸 — Task 10
- #14 添加任务不刷新 — Task 2
- #15 ReportPreview 版面 — Task 11
- streak_label 空白行 — Task 12

全部覆盖 ✓

### 2. Placeholder 扫描
- Task 3 Step 3.3 "如发现根因" — 这是条件分支, 非 placeholder ✓
- Task 7-9 部分 step 描述"根据排查结果决定" — 因为根因尚未确定, 标记为"investigate 类任务", 执行时由 engineer 现场判断, 这是有意为之 ✓
- 无 "TODO / TBD" 字样 ✓

### 3. Type consistency
- PixelInput / TextInput / PeriodCard / StatusBox / DayCard 等命名跨 task 一致 ✓
- 文件路径全部用绝对 / 相对路径一致 ✓
