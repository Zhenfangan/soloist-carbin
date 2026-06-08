# ReportPreview 版面重设计 Sub-Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) for tracking. TDD: 写失败测试 → 实现 → 跑通 → 视觉验证 → commit.

**Goal:** 重新设计 `app/ui/components/report_preview.py:196-354` 战报内容版面 — 在不改语义内容的前提下，建立清晰视觉层次、修复 Rams "Aesthetic/Understandable/Honest" 三项问题，使用户能在 3 秒内抓取"净额/工时/承诺"三个关键信号。

**Architecture:** 内容区从"扁平 Label 列表"升级为"卡片网格 + 显著 KPI"结构 — 顶部一行 3 个 KPI 块 (净额/工时/承诺) → 下方分区卡片 (打卡详情、完成任务)。所有间距、颜色、字号一律从 `app/ui/tokens.py` 取值，禁止字面量。

**Tech Stack:** Kivy 2.3.1 + pytest，复用现有 `tokens.py` 常量，复用 `_COLOR_PENALTY/REWARD/OVERTIME/PROMISE_BG` 模块级常量 (line 36-39)，不引入新依赖。

**前置约定:**
- 执行前 `git status` 干净
- 视觉验证：`SOLOIST_DEBUG=1 PYTHONIOENCODING=utf-8 python -m app.main > debug.log 2>&1 &`
- 触发路径：CheckinScreen → "结束今日并查看战报" → 观察 ReportPreview
- 每步独立 commit；若布局回归立即 `git revert`

---

## 现状审计 (Current State, 5 个具体问题)

| # | 问题 | 文件:行 | Rams 原则 |
|---|------|---------|-----------|
| A | 全部 body Label 同字号同高 (14pt/24px)，section 标题仅 `bold=True` 区分；扫读时所有行视觉权重相同 | `report_preview.py:226-234, 239-265, 270-288, 333-342` 与 `_section_title:359-370` | Aesthetic / Understandable |
| B | "罚款/奖励/净额"用左对齐文本 + `"  "` 缩进伪装层级；数字不右对齐，无法瞬间对比金额；"净额"作为最重要 KPI 未被强调 | `:239-265` | Useful / Understandable |
| C | spacer 高度在 4/8 之间随意切换 (`:219,237,268,292,345`)，缺少基于 `GRID_UNIT=8` 的节奏，视觉上"散乱" | `:219,237,268,292,345` + `_spacer:373-375` | Aesthetic |
| D | Label 全部没设 `text_size`，长任务名 (`:334-342`) 与长承诺描述 (`:319-326`) 不会自动换行，会被静默截断 | `:226-234, 319-326, 333-342` | Honest / Thorough |
| E | ScrollView 高度用魔法数字 `panel.height*0.9 - 48 - 80` (`:109`)，title 位置 `pos_hint={"x":0,"y":0.92}` (`:97`) 硬编码；将来标题加副标题会错位 | `:97, 109` | Long-lasting |

**额外观察 (低优先级，不在本计划但留档)：**
- 空 `periods` (`:222`)、空 `completed_tasks` (`:330`) 无"暂无"提示；
- 男友承诺黄色背景孤立 — 整个版面其余色块为零，与"卡片化"目标可统一。

---

## 提议设计 (Proposed Design)

### 信息层级 (自上而下)

```
┌─────────────────────────────────────────┐
│           {日期}  {办公日/拍摄日}           │  ← Title 18pt bold  brown
├─────────────────────────────────────────┤
│  ┌─净额─┐  ┌─工时─┐  ┌─承诺─┐               │  ← KPI 行 (高 64px)
│  │ +30  │  │ 7.5h │  │  ✓   │               │     数字 22pt bold
│  │ 净额 │  │ 工作 │  │ 兑现 │               │     标签 10pt gray
│  └──────┘  └──────┘  └──────┘               │     bg=PROMISE_BG (承诺色)
├─────────────────────────────────────────┤
│  打卡详情                                  │  ← Section 14pt bold + 下划色块
│   上午   09:02 ~ 12:00   正常              │     body 14pt 左对齐
│   下午   13:30 ~ 18:05   正常              │     时间右对齐(等宽视觉)
│   晚上   --   --   未打卡                  │
├─────────────────────────────────────────┤
│  完成任务                                  │
│   ✓ 写战报模块                              │
│   ✓ 修 5 个 UI bug                          │
├─────────────────────────────────────────┤
│       继续加油!                            │  ← 鼓励语 10pt gray 居中
└─────────────────────────────────────────┘
```

### Spacing 规则 (token 化)

| 用途 | 值 | 来源 |
|------|----|------|
| 区块之间 | `GRID_UNIT * 2 = 16` | tokens.py:78 |
| 区块内行间 | `GRID_UNIT = 8` | tokens.py:78 |
| 卡片内 padding | `CARD_PADDING = 16` (横) / `GRID_UNIT = 8` (纵) | tokens.py:81 |
| 标题下方 spacer | `GRID_UNIT * 2 = 16` | tokens.py:78 |

### 颜色规则

| 元素 | Token | 旧值 |
|------|-------|------|
| Title 文字 | `TEXT_BROWN` (#3A3028) | 保持 |
| KPI 数字-净额正 | `_COLOR_REWARD` (#27ae60) | 新增 |
| KPI 数字-净额负 | `_COLOR_PENALTY` (#e74c3c) | 新增 |
| KPI 数字-工时 | `_COLOR_OVERTIME` (#e67e22) when >=8h 否则 `TEXT_BROWN` | 新增 |
| KPI 卡片 bg | `CARD_WHITE` (#FFFFFF) | tokens.py:18 |
| 承诺 KPI bg (高亮) | `_COLOR_PROMISE_BG` (#FFF8E0) | 已存在 |
| Section 标题底色条 (4px 高) | `PRIMARY_YELLOW` (#FFE030) | tokens.py:15 |
| Body 文字 | `TEXT_BROWN` | 保持 |
| 鼓励语 | `TEXT_GRAY` | 保持 |

### 字号规则

| 用途 | Token | 大小 |
|------|-------|------|
| 顶部日期标题 | `FONT_SIZE_TITLE` | 18 |
| KPI 数字 | `FONT_SIZE_TITLE + 4 = 22` (硬常量,声明 `_FONT_KPI`) | 新增 |
| KPI 标签 | `FONT_SIZE_SMALL` | 10 |
| Section 标题 | `FONT_SIZE_BODY` bold | 14 |
| Body 行 | `FONT_SIZE_BODY` | 14 |
| 鼓励语 | `FONT_SIZE_SMALL` | 10 |

---

## 任务分解 (4 个 Task，TDD)

### Task R1: 抽取 KPI 卡片工厂 + 单测

**根因:** 现 `_build_report_content` 把所有 Label 平铺直叙；要做 KPI 行，必须先有可复用的"小卡片"构造器。

**Files:**
- Modify: `app/ui/components/report_preview.py:196-355`
- Test: `app/tests/ui/test_report_preview_kpi.py` (新建)

- [ ] **Step R1.1: 写失败测试**

```python
# app/tests/ui/test_report_preview_kpi.py
"""ReportPreview KPI 卡片回归测试。"""
from __future__ import annotations
from app.ui.components.report_preview import ReportPreview, _to_rgba
from app.ui.tokens import CARD_WHITE, FONT_SIZE_SMALL


def test_kpi_card_has_white_bg_and_two_labels():
    card = ReportPreview._kpi_card(value="+30", label="净额", value_color="#27ae60")
    assert card.height == 64
    # 应有 value(大字) + label(小字) 两个 Label
    labels = [c for c in card.children if c.__class__.__name__ == "Label"]
    assert len(labels) == 2
    big, small = (labels[0], labels[1]) if labels[0].font_size > labels[1].font_size else (labels[1], labels[0])
    assert big.text == "+30"
    assert small.text == "净额"
    assert small.font_size == FONT_SIZE_SMALL


def test_kpi_card_promise_uses_yellow_bg():
    card = ReportPreview._kpi_card(value="✓", label="承诺", value_color="#3A3028", highlight=True)
    # canvas.before 应有 #FFF8E0 矩形
    from kivy.graphics import Color
    colors = [c for c in card.canvas.before.children if isinstance(c, Color)]
    assert any(abs(c.r - 1.0) < 0.01 and abs(c.g - 0.97) < 0.05 for c in colors), \
        "承诺 KPI 应使用 _COLOR_PROMISE_BG (#FFF8E0)"
```

- [ ] **Step R1.2: 实现 `_kpi_card` 静态方法** (在 `_section_title` 旁边)

```python
@staticmethod
def _kpi_card(value: str, label: str, value_color: str, highlight: bool = False) -> BoxLayout:
    """单个 KPI 块：上面大字数值，下面小字标签。"""
    box = BoxLayout(orientation="vertical", size_hint=(1, None), height=64,
                    padding=[GRID_UNIT, GRID_UNIT // 2])
    bg_color = _COLOR_PROMISE_BG if highlight else CARD_WHITE
    with box.canvas.before:
        Color(*_to_rgba(bg_color))
        Rectangle(pos=box.pos, size=box.size)
    box.bind(pos=lambda w, _: ReportPreview._redraw_bg(w, bg_color),
             size=lambda w, _: ReportPreview._redraw_bg(w, bg_color))
    box.add_widget(Label(text=value, font_size=22, bold=True,
                         color=_to_rgba(value_color), size_hint_y=0.66,
                         halign="center", valign="middle"))
    box.add_widget(Label(text=label, font_size=FONT_SIZE_SMALL,
                         color=_to_rgba(TEXT_GRAY), size_hint_y=0.34,
                         halign="center", valign="middle"))
    return box

@staticmethod
def _redraw_bg(widget: Any, hex_color: str) -> None:
    widget.canvas.before.clear()
    with widget.canvas.before:
        Color(*_to_rgba(hex_color))
        Rectangle(pos=widget.pos, size=widget.size)
```

需在 import 区加 `CARD_WHITE`。

- [ ] **Step R1.3: 跑测试通过 → commit** `feat(ui): ReportPreview Task R1 — 抽取 _kpi_card 工厂`

---

### Task R2: 顶部 KPI 行替代奖惩汇总+工作时长两个区块

**根因:** Audit 问题 B — 奖惩汇总(`:239-265`)与工作时长(`:269-288`)占了 5 行扁平 Label；改成 3 列 KPI 一行即可呈现，腾出 ~120px 视觉空间。

**Files:**
- Modify: `app/ui/components/report_preview.py:236-301`
- Test: `app/tests/ui/test_report_preview_layout.py` (新建)

- [ ] **Step R2.1: 写失败测试**

```python
def test_report_content_renders_kpi_row_at_top():
    from app.models.report import ReportData, PromiseDetail
    data = ReportData(date="2026-06-08", total_work_hours=7.5, reward_total=50,
                      penalty_total=20, net_amount=30,
                      promise=PromiseDetail(reward_desc="奶茶", fulfilled=True))
    rp = ReportPreview(report_data=data)
    # _content_box 第二个 widget 应是 KPI 行 BoxLayout(横向)
    kids = list(rp._content_box.children)[::-1]  # Kivy 子列表是反序
    # kids[0]=日期title, kids[1]=spacer, kids[2]=KPI 行
    assert kids[2].orientation == "horizontal"
    assert len(kids[2].children) == 3  # 净额/工时/承诺


def test_net_amount_color_follows_sign():
    from app.models.report import ReportData
    data_pos = ReportData(date="x", net_amount=10)
    rp_pos = ReportPreview(report_data=data_pos)
    # 找到第一个 KPI 卡里的大字 label
    # ...assert color == _COLOR_REWARD rgba
```

- [ ] **Step R2.2: 替换 `_build_report_content` 中 line 236-288 段**

把"奖惩汇总" + "工作时长"两整段删除，改为:

```python
# ── KPI 行 (净额 / 工时 / 承诺) ──
_add(self._spacer(GRID_UNIT * 2))
kpi_row = BoxLayout(orientation="horizontal", size_hint=(1, None),
                    height=64, spacing=GRID_UNIT)

net_color = _COLOR_REWARD if data.net_amount >= 0 else _COLOR_PENALTY
kpi_row.add_widget(self._kpi_card(
    value=f"{data.net_amount:+.0f}", label="净额", value_color=net_color))

hours_color = _COLOR_OVERTIME if data.total_work_hours >= 8 else TEXT_BROWN
kpi_row.add_widget(self._kpi_card(
    value=f"{data.total_work_hours:.1f}h", label="工时", value_color=hours_color))

if data.promise:
    promise_value = "✓" if data.promise.fulfilled else "✗"
    promise_color = _COLOR_REWARD if data.promise.fulfilled else _COLOR_PENALTY
    kpi_row.add_widget(self._kpi_card(
        value=promise_value, label="承诺", value_color=promise_color, highlight=True))
else:
    kpi_row.add_widget(self._kpi_card(value="-", label="无承诺", value_color=TEXT_GRAY))

_add(kpi_row)
```

旧的"满 8 小时鼓励" Label (`:291-301`) 删除 — 已由 KPI 工时橙色表达。

- [ ] **Step R2.3: 同步删除 `:303-327` 承诺独立色块** — KPI 已覆盖该信息。

- [ ] **Step R2.4: 测试通过 + 视觉验证 + commit** `feat(ui): ReportPreview Task R2 — 顶部三 KPI 行替代扁平奖惩/工时清单`

---

### Task R3: 节奏化间距 + Section 黄色横条

**根因:** Audit 问题 A、C — `_section_title` 仅靠 `bold` 不够显眼，spacer 高度随意。

**Files:**
- Modify: `app/ui/components/report_preview.py:219-237, 268, 292, 332, 345, 359-375`

- [ ] **Step R3.1: 改 `_section_title` 加左侧 4px 黄色色块**

```python
@staticmethod
def _section_title(text: str) -> BoxLayout:
    row = BoxLayout(orientation="horizontal", size_hint_y=None,
                    height=28, spacing=GRID_UNIT)
    bar = BoxLayout(size_hint=(None, 1), width=4)
    with bar.canvas.before:
        Color(*_to_rgba(PRIMARY_YELLOW))
        Rectangle(pos=bar.pos, size=bar.size)
    bar.bind(pos=lambda w, _: ReportPreview._redraw_bg(w, PRIMARY_YELLOW),
             size=lambda w, _: ReportPreview._redraw_bg(w, PRIMARY_YELLOW))
    row.add_widget(bar)
    row.add_widget(Label(text=text, font_size=FONT_SIZE_BODY, bold=True,
                         color=_to_rgba(TEXT_BROWN), halign="left", valign="middle"))
    return row
```

需 import `PRIMARY_YELLOW`。注意返回类型从 `Label` 变 `BoxLayout`，调用处不需要改。

- [ ] **Step R3.2: 统一 spacer 调用**

把所有 `self._spacer(4)` 替换为 `self._spacer(GRID_UNIT)`；所有 `self._spacer(8)` 替换为 `self._spacer(GRID_UNIT * 2)`。`_spacer` 签名保持，仅调用点替换。

- [ ] **Step R3.3: 写测试**

```python
def test_section_title_has_yellow_bar():
    row = ReportPreview._section_title("打卡详情")
    assert row.orientation == "horizontal"
    bar = row.children[-1]  # 第一个加入的子项 = children 末项
    assert bar.width == 4
```

- [ ] **Step R3.4: 通过 → commit** `feat(ui): ReportPreview Task R3 — section 黄色色条 + 节奏化 spacing`

---

### Task R4: 防截断 + 长内容兜底

**根因:** Audit 问题 D — Labels 无 `text_size`，长任务/长承诺会被切掉而无视觉提示。

**Files:**
- Modify: `app/ui/components/report_preview.py:226-234, 333-342, 346-354`

- [ ] **Step R4.1: 写失败测试**

```python
def test_long_task_name_does_not_silently_truncate():
    from app.models.report import ReportData
    long_task = "这是一个非常非常非常非常非常非常长的任务标题用于测试换行"
    data = ReportData(date="x", completed_tasks=[long_task])
    rp = ReportPreview(report_data=data)
    # 找到这个任务的 Label
    labels = []
    def walk(w):
        for c in w.children:
            if c.__class__.__name__ == "Label" and long_task in c.text:
                labels.append(c)
            walk(c)
    walk(rp._content_box)
    assert labels, "未找到长任务 Label"
    lab = labels[0]
    # 必须设置 text_size 以启用换行
    assert lab.text_size[0] is not None
    # height 应允许多行 (>= 24*2 = 48 当文本超长时)
```

- [ ] **Step R4.2: 给所有 body Label 加 `text_size` 绑定**

抽工厂 `_body_label(text, color, indent=0)`:

```python
@staticmethod
def _body_label(text: str, color: tuple, halign: str = "left") -> Label:
    lab = Label(text=text, font_size=FONT_SIZE_BODY, color=color,
                size_hint_y=None, halign=halign, valign="top",
                shorten=False)
    # 关键: 让 text_size 跟随宽度，触发自动换行；并据 texture_size 撑高
    def _on_width(w, val):
        w.text_size = (val - CARD_PADDING, None)
    def _on_texture(w, val):
        w.height = max(24, val[1])
    lab.bind(width=_on_width, texture_size=_on_texture)
    return lab
```

替换 `:226-234, 270-288 (剩余的)、333-342` 处 `Label(...)` 为 `self._body_label(...)`。

- [ ] **Step R4.3: 处理空 encouragement**

```python
if data.encouragement:
    _add(self._spacer(GRID_UNIT * 2))
    _add(Label(text=data.encouragement, font_size=FONT_SIZE_SMALL,
               color=gray, size_hint_y=None, height=32,
               halign="center", valign="middle"))
```

把 `:345-354` 包到 `if data.encouragement:` 内。

- [ ] **Step R4.4: 视觉验证 + commit** `feat(ui): ReportPreview Task R4 — text_size 防截断 + 空 encouragement 兜底`

---

## 验收清单 (Definition of Done)

- [ ] 4 个 Task 全部 commit，单测 `pytest app/tests/ui/test_report_preview*.py -v` 全绿
- [ ] `SOLOIST_DEBUG=1 python -m app.main` 手动点 "结束今日并查看战报" 截图：
  - [ ] 顶部 3 个 KPI 卡可见，承诺卡黄底
  - [ ] section 标题左侧有 4px 黄条
  - [ ] 长任务名自动换行不截断
  - [ ] 无承诺时 KPI 第三格显示"无承诺"灰字
- [ ] `mypy app/ui/components/report_preview.py` 0 error
- [ ] `ruff check app/ui/components/report_preview.py` 0 error
- [ ] `grep -nE '#[0-9a-fA-F]{6}' app/ui/components/report_preview.py` 仅出现在模块顶 `_COLOR_*` 常量声明区
