# Wave 2 Phase 2 — 根因修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 基于 Phase 1 诊断 log 定位的 4 个真根因, 批量修复 UI 阻塞 bug。

**Architecture:** 3 个 batch 独立执行:
- **Batch A**: 14 处同 pattern `size=(w, h) → (bw, h)` 批量修 + 防退化 grep 测试
- **Batch B**: 2 处事件链路 stub (`_on_report` / `_on_day_click`) 补完整实现
- **Batch C**: `navigation.py` TabButton 内嵌 BoxLayout 绑 size/pos 防 4 tab 重叠

**Tech Stack:** Kivy 2.3.1, Python 3.12, pytest (offscreen backend), mypy --strict, ruff

---

## 诊断依据

Phase 1 实测 log `doc/wave2-traces/session-2026-06-06-2230.txt` 揭示:

| 原 bug | 真根因 | 备注 |
|---|---|---|
| B1 添加任务点不开 | ✅ Wave 1 + Task 5 已修 | log line 106-114 完整链路工作 |
| B2 战报弹不出 | `checkin_screen.py:604-612` `_on_report` 只调 `generate_and_save`, 不创建 ReportPreview | Batch B |
| B3 历史 day cell 无反应 | `history_screen.py:468-470` `_on_day_click` 只 `print(...)` 是 stub | Batch B |
| B4 对赌页排版乱 | 推测 Batch A 后部分自然解决, 否则单独 plan | 留观 |
| B5 nav 4 tab 重叠 | `navigation.py:62-65` TabButton 内嵌 BoxLayout 没绑 size/pos, 4 个 BoxLayout 全在 (0,0) | Batch C |
| B6 弹窗右侧淡黄方块 | **14 处同 pattern** `Rectangle(pos=(x + w - bw, y), size=(w, h))` 应为 `(bw, h)` | Batch A |
| B7 开发面板乱 | 推测 Batch A 后自然解决 | 留观 |
| B8 输入框 IME | ✅ 已工作 | log line 109-112 中英文输入正常 |

---

## 文件结构

### Batch A 同 pattern size bug 批量修 (14 处)

| 文件 | 行 | 类型 |
|---|---|---|
| `app/ui/utils.py` | 78 | `_build_inset_border` 共用函数 |
| `app/ui/components/add_task_dialog.py` | 218 | dialog card 边框 |
| `app/ui/components/bet_config_section.py` | 156 | section 边框 |
| `app/ui/components/collapsible_group.py` | 213 | group 边框 |
| `app/ui/components/period_card.py` | 410 | period card |
| `app/ui/components/pixel_dialog.py` | 186 | confirm dialog |
| `app/ui/components/pixel_number_dialog.py` | 190 | number dialog (B6) |
| `app/ui/components/pixel_time_picker.py` | 275 | time picker |
| `app/ui/components/promise_input.py` | 218 | 男友承诺 |
| `app/ui/components/settlement_dialog.py` | 272 | 结算 |
| `app/ui/components/status_box.py` | 203 | 状态盒 |
| `app/ui/components/task_inline_list.py` | 155 | 任务清单 |
| `app/ui/screens/onboarding_screen.py` | 114 | 引导页 |
| `app/ui/screens/settings_screen.py` | 645 | 设置页 dev_panel |

### Batch B 事件链路修复 (2 处)

| 文件 | 行 | 改动 |
|---|---|---|
| `app/ui/screens/checkin_screen.py` | 604-612 | `_on_report`: 调用 service 后创建 + open `ReportPreview` |
| `app/ui/screens/history_screen.py` | 468-470 | `_on_day_click`: 实例化 `ReportPreview` 用当日数据 + open |

### Batch C nav 重叠修复

| 文件 | 行 | 改动 |
|---|---|---|
| `app/ui/navigation.py` | 62-65 | TabButton.__init__: `self.bind(size=layout.setter("size"), pos=layout.setter("pos"))` |

### 新增测试

| 路径 | 用途 |
|---|---|
| `app/tests/ui/test_pattern_size_bug.py` | grep 全 codebase 防 `size=(w, h)` 同 pattern bug 退化 |
| `app/tests/ui/test_report_dispatch.py` | B2 + B3 事件链路验证 — 点击触发 ReportPreview.open |
| `app/tests/ui/test_navigation.py` (修改) | B5 — TabButton 内嵌 BoxLayout size 跟随 TabButton |

---

## Task 列表

- **Task A**: Batch A — 14 处 size bug 批量修 + 防退化测试
- **Task B1**: Batch B 子任务 — `_on_report` 补 ReportPreview
- **Task B2**: Batch B 子任务 — `_on_day_click` 补 ReportPreview
- **Task C**: Batch C — TabButton 内嵌 BoxLayout 绑 size/pos
- **Task D**: andy 复测 + 拍最终截图

---

### Task A: 14 处 size=(w, h) → (bw, h) 批量修

**Files:**
- Modify (14 个): `app/ui/utils.py:78`, `app/ui/components/add_task_dialog.py:218`, `bet_config_section.py:156`, `collapsible_group.py:213`, `period_card.py:410`, `pixel_dialog.py:186`, `pixel_number_dialog.py:190`, `pixel_time_picker.py:275`, `promise_input.py:218`, `settlement_dialog.py:272`, `status_box.py:203`, `task_inline_list.py:155`, `app/ui/screens/onboarding_screen.py:114`, `app/ui/screens/settings_screen.py:645`
- Create test: `app/tests/ui/test_pattern_size_bug.py`

- [ ] **Step 1: 写防退化的 grep 测试 (会先失败因为现在有 14 处违规)**

Create `app/tests/ui/test_pattern_size_bug.py`:

```python
"""防 size=(w, h) 同 pattern bug 退化的全 codebase grep 测试。

每一个 Rectangle(pos=(x + w - bw, y), size=...) 在凸起暗面 right / 凹陷亮面 right
位置都应该是 size=(bw, h), 不能是 size=(w, h) (会画一个全宽矩形覆盖出去)。

历史上 wave 1 + Task 5 漏掉了 14 处, Phase 2 Batch A 一次修干净。
"""

from __future__ import annotations

import re
from pathlib import Path


# 项目根 — 测试运行时 PWD 是项目根
PROJECT_ROOT = Path(__file__).resolve().parents[3]
UI_DIR = PROJECT_ROOT / "app" / "ui"

# 匹配 Rectangle(pos=(x + w - bw, y), size=(w, h)) — 没有 bw 的 w
BAD_PATTERN = re.compile(
    r"Rectangle\(\s*pos=\(x\s*\+\s*w\s*-\s*bw,\s*y\),\s*size=\(w,\s*h\)\s*\)"
)


def test_no_w_h_size_in_right_edge_rectangle() -> None:
    """全 app/ui/ 下没有 Rectangle(pos=(x+w-bw, y), size=(w, h)) — 必须是 size=(bw, h)。"""
    violations: list[str] = []
    for path in UI_DIR.rglob("*.py"):
        content = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(content.splitlines(), start=1):
            if BAD_PATTERN.search(line):
                violations.append(f"{path.relative_to(PROJECT_ROOT)}:{lineno}: {line.strip()}")

    assert violations == [], (
        "发现同 pattern size=(w, h) bug, 应为 (bw, h):\n  " + "\n  ".join(violations)
    )
```

- [ ] **Step 2: 跑测试确认 FAIL (会列出 14 处违规)**

```powershell
python -m pytest app/tests/ui/test_pattern_size_bug.py -v
```

Expected: FAIL, 输出含 14 个 file:line 列表。

- [ ] **Step 3: 批量替换 14 处**

逐个修改文件, 把 `size=(w, h)` 改为 `size=(bw, h)`。**只改本 plan 指定的 14 行**, 其他行不动。

由于 14 个文件每个只改 1 行, 且行号已经精确定位, 可用 Edit 工具逐个修。

每个文件改动模板:

```
旧: Rectangle(pos=(x + w - bw, y), size=(w, h))
新: Rectangle(pos=(x + w - bw, y), size=(bw, h))
```

完整文件列表 (Step 1 表格):

1. `app/ui/utils.py:78`
2. `app/ui/components/add_task_dialog.py:218`
3. `app/ui/components/bet_config_section.py:156`
4. `app/ui/components/collapsible_group.py:213`
5. `app/ui/components/period_card.py:410`
6. `app/ui/components/pixel_dialog.py:186`
7. `app/ui/components/pixel_number_dialog.py:190`
8. `app/ui/components/pixel_time_picker.py:275`
9. `app/ui/components/promise_input.py:218`
10. `app/ui/components/settlement_dialog.py:272`
11. `app/ui/components/status_box.py:203`
12. `app/ui/components/task_inline_list.py:155`
13. `app/ui/screens/onboarding_screen.py:114`
14. `app/ui/screens/settings_screen.py:645`

- [ ] **Step 4: 跑测试确认 PASS**

```powershell
python -m pytest app/tests/ui/test_pattern_size_bug.py -v
```

Expected: 1 passed.

- [ ] **Step 5: 跑全套确认无回归**

```powershell
python -m pytest app/tests/ -v --tb=short --ignore=app/tests/ui/test_assets.py
```

Baseline 当前 HEAD `aa5dce2` 后: 24 failed / 358 passed. Phase 2 Task A 加 1 个测试 → 24 failed / 359 passed.

如果某个 UI 测试因为 right border 变细了而 fail (e.g. test 检查矩形数量但断言尺寸), 这是修对后需要调整的, 改测试断言匹配 `(bw, h)`。

- [ ] **Step 6: Commit**

```powershell
git add app/ui/ app/tests/ui/test_pattern_size_bug.py
```

HEREDOC commit message:
```
fix(ui): 批量修 14 处同 pattern Rectangle size=(w,h) → (bw,h)

wave 2 phase 2 batch A. wave 1 + Task 5 之前只修了 3 处
(pixel_input/stepper/button), 但 grep 范围太窄。Phase 1 诊断 log
确认 B6 (PixelNumberDialog 右侧淡黄方块) 是这个同 pattern, 全
codebase 扫出 14 处需要修。

修复点:
- utils.py:78 (_build_inset_border 共用函数)
- add_task_dialog/bet_config_section/collapsible_group
- period_card/pixel_dialog/pixel_number_dialog
- pixel_time_picker/promise_input/settlement_dialog
- status_box/task_inline_list
- onboarding_screen/settings_screen

新增 test_pattern_size_bug.py 用 grep regex 防退化。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
```

---

### Task B1: `_on_report` 补 ReportPreview

**Files:**
- Modify: `app/ui/screens/checkin_screen.py:604-612`
- Create test: `app/tests/ui/test_report_dispatch.py`

- [ ] **Step 1: 写失败测试**

Create `app/tests/ui/test_report_dispatch.py`:

```python
"""B2 + B3 事件链路验证 — CheckinScreen / HistoryScreen 点击触发 ReportPreview.open。"""

from __future__ import annotations

from unittest import mock


class TestCheckinScreenReportDispatch:
    """B2: 点 '结束今日并查看战报' 应实例化 + open ReportPreview。"""

    def test_on_report_opens_report_preview(self) -> None:
        from app.ui.screens.checkin_screen import CheckinScreen

        fake_report_service = mock.MagicMock()
        fake_report_service.generate_and_save.return_value = "/tmp/report.png"

        screen = CheckinScreen(report_service=fake_report_service)
        screen._date_str = "2026-06-06"

        with mock.patch(
            "app.ui.screens.checkin_screen.ReportPreview"
        ) as mock_preview_cls:
            screen._on_report()

        mock_preview_cls.assert_called_once()
        instance = mock_preview_cls.return_value
        instance.open.assert_called_once()
```

- [ ] **Step 2: 跑测试确认 FAIL**

```powershell
python -m pytest app/tests/ui/test_report_dispatch.py::TestCheckinScreenReportDispatch -v
```

Expected: FAIL — 因为目前 `_on_report` 没有 import 或调用 ReportPreview。

- [ ] **Step 3: 修改 `app/ui/screens/checkin_screen.py`**

首先在 imports 中确保 ReportPreview 已导入:

```python
from app.ui.components.report_preview import ReportPreview
```

(grep 一下 checkin_screen.py 现有 import, 如果已经有则不重复加)

然后修改 `_on_report` (当前在 line 604-612):

```python
def _on_report(self) -> None:
    """战报按钮回调 — 生成战报图 + 弹 ReportPreview 全屏预览。"""
    if not self._report_service:
        return

    try:
        image_path = self._report_service.generate_and_save(self._date_str)
    except Exception as e:
        Logger.error(f"CheckinScreen: 生成战报失败 {e}")
        return

    preview = ReportPreview(
        image_path=str(image_path) if image_path else "",
        date_str=self._date_str,
        on_save=None,
        on_settle=None,
    )
    preview.open()
```

注: `generate_and_save` 返回值需要确认是 path 还是 None。如果 return None / 不返回, 调用 service 后从一个 known 位置读取 (查 report_service.py)。如果 service signature 不同, 修测试为 mock service.return_value 匹配实际签名。

- [ ] **Step 4: 跑测试确认 PASS**

```powershell
python -m pytest app/tests/ui/test_report_dispatch.py::TestCheckinScreenReportDispatch -v
```

Expected: 1 passed.

- [ ] **Step 5: 全套确认无回归**

```powershell
python -m pytest app/tests/ -v --tb=short --ignore=app/tests/ui/test_assets.py
```

Expected: 24 failed / 360 passed (+1 from Task A 359, +1 from this task).

- [ ] **Step 6: Commit**

```powershell
git add app/ui/screens/checkin_screen.py app/tests/ui/test_report_dispatch.py
```

HEREDOC:
```
fix(checkin): _on_report 补创建 + open ReportPreview (B2 战报弹不出)

phase 1 log 诊断: line 115 点 '结束今日并查看战报' → 仅调 generate_and_save
没有任何 ModalView 开。CheckinScreen._on_report 原实现是 stub。
现在 service 生成图后实例化 ReportPreview(image_path, date_str) 并 open()。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
```

---

### Task B2: `_on_day_click` 补 ReportPreview

**Files:**
- Modify: `app/ui/screens/history_screen.py:468-470`
- Modify: `app/tests/ui/test_report_dispatch.py` (新增 class TestHistoryScreenReportDispatch)

- [ ] **Step 1: 在 `app/tests/ui/test_report_dispatch.py` 加测试**

加 (在 TestCheckinScreenReportDispatch 之后):

```python
class TestHistoryScreenReportDispatch:
    """B3: 点 history day cell 应实例化 + open ReportPreview。"""

    def test_on_day_click_opens_report_preview(self) -> None:
        from app.models.history import DayCard as DayCardModel
        from app.ui.screens.history_screen import HistoryScreen

        # mock 一个 service
        fake_history_service = mock.MagicMock()
        screen = HistoryScreen(history_service=fake_history_service)

        # 构造一个最简的 DayCardModel
        day_summary = DayCardModel(
            date="2026-06-06",
            present_count=1,
            late_count=0,
            absent_count=0,
            total_hours=8.0,
            reward=50,
        )

        with mock.patch(
            "app.ui.screens.history_screen.ReportPreview"
        ) as mock_preview_cls:
            screen._on_day_click(day_summary)

        mock_preview_cls.assert_called_once()
        instance = mock_preview_cls.return_value
        instance.open.assert_called_once()
```

注: `DayCardModel` 构造参数需查 `app/models/history.py`。如果与上述不符, 改成实际签名 (本 plan 的目的是验证 `_on_day_click` 调用 ReportPreview, 数据细节不重要)。

- [ ] **Step 2: 跑测试确认 FAIL**

```powershell
python -m pytest app/tests/ui/test_report_dispatch.py::TestHistoryScreenReportDispatch -v
```

Expected: FAIL — `_on_day_click` 当前只 print, 没 ReportPreview 调用。

- [ ] **Step 3: 修改 `app/ui/screens/history_screen.py`**

加 import (如果还没有):
```python
from app.ui.components.report_preview import ReportPreview
```

修改 `_on_day_click` (line 468-470):

```python
def _on_day_click(self, day_summary: DayCardModel) -> None:
    """DayCard 点击 — 打开当日战报全屏预览。"""
    if not self._service:
        Logger.warning(f"HistoryScreen: history_service is None, cannot show report for {day_summary.date}")
        return

    try:
        image_path = self._service.get_report_path(day_summary.date)
    except Exception as e:
        Logger.error(f"HistoryScreen: 获取战报路径失败 {day_summary.date}: {e}")
        return

    preview = ReportPreview(
        image_path=str(image_path) if image_path else "",
        date_str=day_summary.date,
        on_save=None,
        on_settle=None,
    )
    preview.open()
```

注: `history_service.get_report_path` 的实际方法名未确认。Implementer 应 grep `report_path|get_report` 在 history_service.py 找正确方法。若不存在则: 直接用 `image_path=""` open ReportPreview (空图但弹窗弹出), 加 Logger.warning 提示。

- [ ] **Step 4: 跑测试 PASS**

```powershell
python -m pytest app/tests/ui/test_report_dispatch.py -v
```

Expected: 2 passed.

- [ ] **Step 5: 全套**

```powershell
python -m pytest app/tests/ -v --tb=short --ignore=app/tests/ui/test_assets.py
```

Expected: 24 failed / 361 passed.

- [ ] **Step 6: Commit**

```powershell
git add app/ui/screens/history_screen.py app/tests/ui/test_report_dispatch.py
```

HEREDOC:
```
fix(history): _on_day_click 补 ReportPreview 调用 (B3 历史点 day 无反应)

phase 1 log 诊断: andy 点历史页 day cell, 0 个 PixelButton hit / 0 个
ModalView open event — 说明 day cell 点击触发了 _on_day_click 但实现
只是 print() stub。现在从 history_service 取 report path 并 open
ReportPreview。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
```

---

### Task C: TabButton 内嵌 BoxLayout 绑 size/pos

**Files:**
- Modify: `app/ui/navigation.py:62-65`
- Create test: `app/tests/ui/test_navigation_layout.py`

- [ ] **Step 1: 写失败测试**

Create `app/tests/ui/test_navigation_layout.py`:

```python
"""B5 TabButton 内嵌 BoxLayout 跟随 TabButton size 测试。"""

from __future__ import annotations


class TestTabButtonInnerLayout:
    """B5: TabButton 内嵌 BoxLayout 应跟随 TabButton size, 不能停在 (100,100)。"""

    def test_inner_layout_size_follows_button(self) -> None:
        from app.ui.navigation import TabButton

        btn = TabButton(icon_name="tab_checkin", text="打卡")
        btn.size = (105, 56)
        btn.pos = (0, 0)

        # 找内嵌 BoxLayout (TabButton 是 Button, children 是 [layout])
        from kivy.uix.boxlayout import BoxLayout
        inner = next(c for c in btn.children if isinstance(c, BoxLayout))

        # 触发 layout 更新 (Kivy 自动调度但测试时手动 trigger)
        btn.trigger_action()  # 或直接读 inner.size
        # 实际测试时: 用 Clock.tick 让 layout 系统调度一次
        from kivy.clock import Clock
        Clock.tick()

        assert inner.size == [105, 56] or tuple(inner.size) == (105, 56), (
            f"TabButton 内嵌 BoxLayout size 应为 (105, 56), got {inner.size}"
        )
```

注: Kivy 在测试环境下不会自动渲染, layout 调度依赖 Clock。如果 `Clock.tick()` 不起效, 测试改为直接断言 binding 已注册: `assert btn.proxy_ref in inner.fast_bind.__self__.bindings.get('size', [])` (或类似 introspect)。或最稳: 测试触发 btn.dispatch('on_size', btn, btn.size) 看 inner.size 是否同步。

实施时如发现 size_hint=(1,1) 也能让 Kivy Button 调度 BoxLayout, 测试需要重写。但根据 Phase 1 log dump 实测 BoxLayout 始终 size=(100, 100), 当前实现确实没绑, 所以测试一定会 fail。

- [ ] **Step 2: 跑测试 FAIL**

```powershell
python -m pytest app/tests/ui/test_navigation_layout.py -v
```

Expected: FAIL.

- [ ] **Step 3: 修改 `app/ui/navigation.py:62-65`**

当前:
```python
layout = BoxLayout(orientation="vertical")
layout.add_widget(self._icon)
layout.add_widget(self._tab_label)
self.add_widget(layout)
```

改为:
```python
layout = BoxLayout(orientation="vertical")
layout.add_widget(self._icon)
layout.add_widget(self._tab_label)
self.add_widget(layout)
# 关键: TabButton 是 Button (不是 Layout), 不会自动调度内嵌 BoxLayout 的 size/pos
# 必须显式绑定否则 BoxLayout 会停在默认 (0, 0) size=(100, 100), 4 个 tab 重叠
self.bind(size=layout.setter("size"), pos=layout.setter("pos"))
# 初始同步一次
layout.size = self.size
layout.pos = self.pos
```

- [ ] **Step 4: 跑测试 PASS**

```powershell
python -m pytest app/tests/ui/test_navigation_layout.py -v
```

Expected: 1 passed.

- [ ] **Step 5: 全套**

```powershell
python -m pytest app/tests/ -v --tb=short --ignore=app/tests/ui/test_assets.py
```

Expected: 24 failed / 362 passed.

注: 如果某个现有 navigation 测试 (在 `test_navigation.py`) 因为这个改动断言 TabButton 子 widget size, 可能需要更新。

- [ ] **Step 6: Commit**

```powershell
git add app/ui/navigation.py app/tests/ui/test_navigation_layout.py
```

HEREDOC:
```
fix(navigation): TabButton 内嵌 BoxLayout 绑 size/pos (B5 4 tab 重叠)

phase 1 log dump 证实: 4 个 TabButton pos 正确 (0,0)(105,0)(210,0)(315,0)
size 都 (105, 56), 但内嵌 BoxLayout 全是 pos=(0,0) size=(100,100) —
Button 不是 Layout 不会调度 children, BoxLayout 默认值不变,
4 个 BoxLayout 都画在 window (0, 0) → 视觉重叠成 1 个 tab。
现在 self.bind(size=layout.setter("size"), pos=layout.setter("pos"))。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
```

---

### Task D: andy 复测 + 截图

> 这一步**不能由 implementer subagent 自己完成** — 需要 controller (Claude) 协调 andy。

**输出**:
- 新的截图保存到 `doc/ui-design/testphoto/ScreenShot_2026-06-06-final-*.png`
- 复测结论: 8 个 bug 解决情况记录

- [ ] **Step 1: Controller 通知 andy 复测**

> "Phase 2 4 个 task 完成 (Batch A 14 处 size + Batch B 2 处事件链路 + Batch C nav layout)。请重启 app (不需要 SOLOIST_DEBUG=1), 复测:
>
> 1. 底部 nav 现在是 4 个 tab 吗?
> 2. 打卡页 + 添加任务 / 取消, 都正常吗?
> 3. 打卡页 → 结束今日并查看战报 → 是否弹出预览?
> 4. 历史页 → 点 day cell → 是否弹出战报?
> 5. 对赌页排版还乱吗?
> 6. 设置页 → 拍摄日奖励 → PixelNumberDialog 右侧还有淡黄方块吗?
> 7. 开发面板布局正常了吗?
>
> 截 5-8 张图保存到 `doc/ui-design/testphoto/`, 告诉我每个 bug 状态。"

- [ ] **Step 2: 根据复测结果决定**

| 结果 | 行动 |
|---|---|
| 8/8 解决 | Wave 2 完结, 进入 wave-camera (打卡自拍 spec 已定) |
| B4 / B7 仍有 — 但已知 (Batch A 没解决全) | 单独 Phase 3 plan 处理 |
| 出现新 bug | 单独 Phase 3 plan, 写新 spec |

---

## Self-Review (已完成)

### 1. Spec 覆盖检查

Wave 2 spec (`doc/superpowers/specs/2026-06-06-wave2-ui-fix-design.md`) 第 4.2 节策略:

| Spec 要求 | 本 plan 覆盖 |
|---|---|
| 4.2.1 事件链路类批量修 | ✅ Batch B (Task B1 + B2) — _on_report + _on_day_click 同时修 |
| 4.2.2 Layout 类批量修 | ✅ Batch A (14 处 size) + Batch C (nav 绑 size) |
| 4.2.3 Input 类 | ⏭️ 已工作 (Phase 1 log 证实), 无需 |
| Phase 3 验收 | ✅ Task D — andy 复测 + 截图 |

### 2. Placeholder 扫描

- Task B1/B2 中说"`generate_and_save` 返回值需要确认" / "`get_report_path` 实际方法名未确认" — implementer 应 grep 确认, 不是 placeholder
- 无 TBD / TODO / 不明确指令

### 3. 类型/命名一致性

- `ReportPreview(image_path, date_str, on_save, on_settle)` 在 Task B1 + Task B2 一致
- `Logger` 在两个 Task 中使用方式一致
- 测试 class 命名 `TestCheckinScreenReportDispatch` / `TestHistoryScreenReportDispatch` 一致

---

## 执行说明

Controller 按 subagent-driven-development:
1. Commit plan
2. Dispatch implementer Task A → spec review → code quality review
3. Dispatch implementer Task B1 → 两道 review
4. Dispatch implementer Task B2 → 两道 review
5. Dispatch implementer Task C → 两道 review
6. Task D 由 controller 协调 andy
