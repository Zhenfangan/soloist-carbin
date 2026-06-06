# Wave 2 Phase 1 — 诊断脚手架 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 wave 2 修复策略 (诊断驱动) 实现诊断工具, 让 andy 实测后能从 log 看清 8 个 UI bug 的根因, 为 Phase 2 批量修复提供数据基础。

**Architecture:** 新建 `app/ui/debug/` 模块, 包含 `event_logger.py` (装饰 PixelButton / ModalView / TextInput 关键方法记事件流) 和 `layout_tracer.py` (递归打印 widget 树 pos/size)。两个工具都 gated by env var `SOLOIST_DEBUG=1`, release 默认关闭。`main.py` 启动时检测 env var 调用 `install_event_logger()`, `dev_panel` 加一个按钮触发 `trace_layout(App.root)`。

**Tech Stack:** Kivy 2.3.1, Python 3.12, pytest (offscreen backend), mypy --strict, ruff

---

## 文件结构

### 新增

| 路径 | 职责 |
|---|---|
| `app/ui/debug/__init__.py` | 空文件, namespace marker |
| `app/ui/debug/event_logger.py` | `install_event_logger()` — monkey-patch PixelButton/ModalView/TextInput 关键方法, gated by env var |
| `app/ui/debug/layout_tracer.py` | `trace_layout(widget, label)` → str — 递归打印 widget 树 |
| `app/tests/ui/debug/__init__.py` | 空文件 |
| `app/tests/ui/debug/test_event_logger.py` | 单元测试 — install 幂等、env var gate |
| `app/tests/ui/debug/test_layout_tracer.py` | 单元测试 — 输出格式 + 递归 |
| `doc/wave2-traces/` | (gitignored) andy 实测收集的 log 文件 |

### 修改

| 路径 | 改动 |
|---|---|
| `app/main.py` | 启动时 `if os.environ.get("SOLOIST_DEBUG") == "1": install_event_logger()` |
| dev_panel 所在位置 (查清在哪) | 加 "Dump widget tree" 按钮调 `trace_layout(App.get_running_app().root)` |

---

## Task 列表

- **Task 1**: `event_logger.py` — 事件日志装饰器
- **Task 2**: `layout_tracer.py` — widget 树打印工具
- **Task 3**: `main.py` + dev_panel 集成 + 启动开关
- **Task 4**: andy 实测收集 log (非代码任务, controller 协调)

---

### Task 1: event_logger.py — 事件日志装饰器

**Files:**
- Create: `app/ui/debug/__init__.py`
- Create: `app/ui/debug/event_logger.py`
- Create: `app/tests/ui/debug/__init__.py`
- Create: `app/tests/ui/debug/test_event_logger.py`

#### Step 1: 创建 namespace `__init__.py` 文件

写空文件即可:

```bash
# 两个 init 文件都是空的
```

文件路径:
- `app/ui/debug/__init__.py`
- `app/tests/ui/debug/__init__.py`

- [ ] **Step 2: 写失败的测试 `test_event_logger.py`**

```python
"""event_logger 单元测试 — 验证 env var gate + 幂等 install。"""

from __future__ import annotations

import os
from unittest import mock

import pytest


class TestInstallEventLogger:
    """验证 install_event_logger 的开关 + 幂等行为。"""

    def setup_method(self) -> None:
        """每个测试前 reset _INSTALLED 状态。"""
        from app.ui.debug import event_logger
        event_logger._INSTALLED = False

    def test_no_install_without_env_var(self) -> None:
        """SOLOIST_DEBUG != 1 时, install 不做任何事。"""
        from app.ui.debug.event_logger import install_event_logger

        with mock.patch.dict(os.environ, {"SOLOIST_DEBUG": "0"}, clear=False):
            installed = install_event_logger()

        assert installed is False, "未设置 SOLOIST_DEBUG=1 时不应安装"

    def test_install_with_env_var(self) -> None:
        """SOLOIST_DEBUG=1 时, install 成功返回 True。"""
        from app.ui.debug.event_logger import install_event_logger

        with mock.patch.dict(os.environ, {"SOLOIST_DEBUG": "1"}):
            installed = install_event_logger()

        assert installed is True, "设置 SOLOIST_DEBUG=1 时应安装成功"

    def test_install_is_idempotent(self) -> None:
        """重复调用 install 不重复装饰。"""
        from app.ui.debug.event_logger import install_event_logger

        with mock.patch.dict(os.environ, {"SOLOIST_DEBUG": "1"}):
            first = install_event_logger()
            second = install_event_logger()

        assert first is True
        assert second is False, "第二次 install 应返回 False (已安装)"

    def test_install_wraps_pixel_button_on_touch_down(self) -> None:
        """安装后 PixelButton.on_touch_down 被装饰。"""
        from app.ui.components.pixel_button import PixelButton
        from app.ui.debug.event_logger import install_event_logger

        original = PixelButton.on_touch_down

        with mock.patch.dict(os.environ, {"SOLOIST_DEBUG": "1"}):
            install_event_logger()

        assert PixelButton.on_touch_down is not original, (
            "PixelButton.on_touch_down 应被装饰替换"
        )

    def test_install_wraps_modal_view_open(self) -> None:
        """安装后 ModalView.open 被装饰。"""
        from kivy.uix.modalview import ModalView
        from app.ui.debug.event_logger import install_event_logger

        original = ModalView.open

        with mock.patch.dict(os.environ, {"SOLOIST_DEBUG": "1"}):
            install_event_logger()

        assert ModalView.open is not original, "ModalView.open 应被装饰替换"
```

- [ ] **Step 3: 跑测试确认失败**

```powershell
python -m pytest app/tests/ui/debug/test_event_logger.py -v
```

Expected: ImportError / ModuleNotFoundError for `app.ui.debug.event_logger`。

- [ ] **Step 4: 实现 `app/ui/debug/event_logger.py`**

```python
"""事件日志装饰器 — 装饰 PixelButton / ModalView / TextInput 关键方法。

启用方式: 设置环境变量 SOLOIST_DEBUG=1, app 启动时调 install_event_logger()。
默认 release 关闭, 无性能与日志噪音影响。

输出示例 (Kivy Logger.info):
    [EVT] PixelButton(text='+ 添加任务') touch_down at (210.0, 380.5) → hit
    [EVT] ModalView(AddTaskDialog).open() called
    [EVT] ModalView(AddTaskDialog) opened, pos=(20.0, 75.0), size=(380, 600)
    [EVT] TextInput focus=True, text=''
"""

from __future__ import annotations

import os
from typing import Any, Callable

from kivy.logger import Logger

_INSTALLED = False


def install_event_logger() -> bool:
    """全局安装事件日志拦截器。

    返回:
        True 表示安装成功 (env var SOLOIST_DEBUG=1 且首次调用)。
        False 表示未安装 (env var 未设或已经安装过)。
    """
    global _INSTALLED
    if _INSTALLED:
        return False
    if os.environ.get("SOLOIST_DEBUG", "0") != "1":
        return False

    _wrap_pixel_button()
    _wrap_modal_view()
    _wrap_text_input()

    _INSTALLED = True
    Logger.info("EventLogger: installed (PixelButton, ModalView, TextInput hooks active)")
    return True


def _wrap_pixel_button() -> None:
    """装饰 PixelButton.on_touch_down 记录 hit 事件。"""
    from app.ui.components.pixel_button import PixelButton

    original = PixelButton.on_touch_down

    def wrapped_on_touch_down(self: Any, touch: Any) -> bool:
        if not self.disabled and self.collide_point(*touch.pos):
            Logger.info(
                f"[EVT] PixelButton(text={self.text!r}) touch_down at {touch.pos} → hit"
            )
        return original(self, touch)

    PixelButton.on_touch_down = wrapped_on_touch_down  # type: ignore[method-assign]


def _wrap_modal_view() -> None:
    """装饰 ModalView.open / dismiss 记录显示/隐藏事件。"""
    from kivy.uix.modalview import ModalView

    original_open = ModalView.open

    def wrapped_open(self: Any, *args: Any, **kwargs: Any) -> Any:
        cls_name = type(self).__name__
        Logger.info(f"[EVT] ModalView({cls_name}).open() called")
        result = original_open(self, *args, **kwargs)
        parent_name = self.parent.__class__.__name__ if self.parent else "None"
        Logger.info(
            f"[EVT] ModalView({cls_name}) opened, "
            f"pos={self.pos}, size={self.size}, parent={parent_name}"
        )
        return result

    ModalView.open = wrapped_open  # type: ignore[method-assign]

    original_dismiss = ModalView.dismiss

    def wrapped_dismiss(self: Any, *args: Any, **kwargs: Any) -> Any:
        Logger.info(f"[EVT] ModalView({type(self).__name__}).dismiss() called")
        return original_dismiss(self, *args, **kwargs)

    ModalView.dismiss = wrapped_dismiss  # type: ignore[method-assign]


def _wrap_text_input() -> None:
    """装饰 TextInput.__init__ 添加 focus 变化监听。"""
    from kivy.uix.textinput import TextInput

    original_init = TextInput.__init__

    def wrapped_init(self: Any, *args: Any, **kwargs: Any) -> None:
        original_init(self, *args, **kwargs)
        self.fbind("focus", _on_text_input_focus)

    TextInput.__init__ = wrapped_init  # type: ignore[method-assign]


def _on_text_input_focus(instance: Any, value: bool) -> None:
    """TextInput focus 变化回调。"""
    Logger.info(f"[EVT] TextInput focus={value}, text={instance.text!r}")
```

- [ ] **Step 5: 跑测试确认通过**

```powershell
python -m pytest app/tests/ui/debug/test_event_logger.py -v
```

Expected: 5 passed。

- [ ] **Step 6: 跑全套确认无回归**

```powershell
python -m pytest app/tests/ -v --tb=short 2>&1 | Select-String -Pattern "passed|failed|error" | Select-Object -Last 10
```

Expected: 与 `git log -1 --format=%H f8ee93e` 时基线测试结果对齐 (52 passed / 2 pre-existing failed in TestCollapsibleGroup emoji)。无新增失败。

如果有新增失败, **不要绕过**, 检查是否 monkey-patch 污染了其它测试 — 必须修。

- [ ] **Step 7: Commit**

```powershell
git add app/ui/debug/__init__.py app/ui/debug/event_logger.py app/tests/ui/debug/__init__.py app/tests/ui/debug/test_event_logger.py
git commit -m "feat(debug): event_logger 装饰 PixelButton/ModalView/TextInput 记录事件流

wave 2 phase 1 - 诊断驱动修复策略的事件追踪工具.
env var SOLOIST_DEBUG=1 启用, release 默认关.
幂等: 重复 install 不重复装饰.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 2: layout_tracer.py — widget 树打印工具

**Files:**
- Create: `app/ui/debug/layout_tracer.py`
- Create: `app/tests/ui/debug/test_layout_tracer.py`

- [ ] **Step 1: 写失败的测试 `test_layout_tracer.py`**

```python
"""layout_tracer 单元测试 — 验证输出格式 + 递归。"""

from __future__ import annotations

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button


class TestTraceLayout:
    """验证 trace_layout 返回字符串包含 widget 关键信息。"""

    def test_trace_single_widget_includes_class_pos_size(self) -> None:
        """单 widget 输出含类名、pos、size。"""
        from app.ui.debug.layout_tracer import trace_layout

        btn = Button(text="Hi")
        btn.size = (100, 48)
        btn.pos = (10, 20)

        output = trace_layout(btn)

        assert "Button" in output
        assert "pos=(10" in output or "pos=(10.0" in output
        assert "size=(100" in output or "size=(100.0" in output

    def test_trace_includes_size_hint_pos_hint(self) -> None:
        """输出含 size_hint 和 pos_hint。"""
        from app.ui.debug.layout_tracer import trace_layout

        btn = Button(text="Hi", size_hint=(None, None), pos_hint={"center_x": 0.5})

        output = trace_layout(btn)

        assert "size_hint" in output
        assert "pos_hint" in output

    def test_trace_recurses_into_children(self) -> None:
        """容器输出含其子 widget 的 trace。"""
        from app.ui.debug.layout_tracer import trace_layout

        layout = BoxLayout(orientation="vertical")
        child_a = Button(text="A")
        child_b = Button(text="B")
        layout.add_widget(child_a)
        layout.add_widget(child_b)

        output = trace_layout(layout)

        assert "BoxLayout" in output
        assert "Button" in output
        # 至少两个 Button 实例 (text A 和 B)
        assert output.count("Button") >= 2

    def test_trace_uses_indentation_for_depth(self) -> None:
        """嵌套 widget 使用缩进区分层级。"""
        from app.ui.debug.layout_tracer import trace_layout

        outer = BoxLayout()
        inner = BoxLayout()
        leaf = Button(text="leaf")
        inner.add_widget(leaf)
        outer.add_widget(inner)

        output = trace_layout(outer)
        lines = output.split("\n")

        # 找到 leaf 那一行
        leaf_lines = [line for line in lines if "leaf" in line]
        assert len(leaf_lines) >= 1
        # leaf 应缩进多于 outer (出现至少 2 层缩进, 每层用 2 个空格)
        assert leaf_lines[0].startswith("    "), (
            f"leaf 应缩进至少 4 空格, got: {leaf_lines[0]!r}"
        )

    def test_trace_accepts_label_parameter(self) -> None:
        """label 参数输出在头部。"""
        from app.ui.debug.layout_tracer import trace_layout

        btn = Button(text="x")
        output = trace_layout(btn, label="MyTrace")

        assert "MyTrace" in output
```

- [ ] **Step 2: 跑测试确认失败**

```powershell
python -m pytest app/tests/ui/debug/test_layout_tracer.py -v
```

Expected: ImportError for `app.ui.debug.layout_tracer`.

- [ ] **Step 3: 实现 `app/ui/debug/layout_tracer.py`**

```python
"""Widget 树打印工具 — 递归输出 widget 的 pos / size / size_hint / pos_hint。

用法:
    from kivy.app import App
    from app.ui.debug.layout_tracer import trace_layout

    root = App.get_running_app().root
    Logger.info(trace_layout(root, label="dev_panel dump"))

输出示例:
    [LAY] dev_panel dump
    [LAY] BoxLayout: pos=(0.0, 0.0) size=(420, 750) size_hint=(1, None) pos_hint={}
    [LAY]   WeekSummaryHeader: pos=(8.0, 670.0) size=(404, 60) size_hint=(1, None) pos_hint={}
    [LAY]     Label: pos=(20, 690) size=(384, 40) size_hint=(None, None) pos_hint={'center_x': 0.5}
"""

from __future__ import annotations

from typing import Any


def trace_layout(widget: Any, label: str = "") -> str:
    """递归打印 widget 树, 返回多行字符串。

    Args:
        widget: Kivy widget 根节点。
        label: 可选标签, 输出在头部。

    Returns:
        多行字符串, 每行 `[LAY]` 前缀, 含类名 / pos / size / size_hint / pos_hint。
        子 widget 缩进 2 空格 (按嵌套深度递增)。
    """
    lines: list[str] = []
    if label:
        lines.append(f"[LAY] {label}")
    _trace_recursive(widget, depth=0, lines=lines)
    return "\n".join(lines)


def _trace_recursive(widget: Any, depth: int, lines: list[str]) -> None:
    """内部递归。每个 widget 一行, children 缩进 +2 空格。"""
    indent = "  " * depth
    cls_name = type(widget).__name__
    pos = getattr(widget, "pos", None)
    size = getattr(widget, "size", None)
    size_hint = getattr(widget, "size_hint", None)
    pos_hint = getattr(widget, "pos_hint", None)

    lines.append(
        f"[LAY] {indent}{cls_name}: pos={pos} size={size} "
        f"size_hint={size_hint} pos_hint={pos_hint}"
    )

    children = getattr(widget, "children", None)
    if children:
        # Kivy children 列表是逆序的 (后加的在前), 倒一下保持视觉顺序
        for child in reversed(children):
            _trace_recursive(child, depth + 1, lines)
```

- [ ] **Step 4: 跑测试确认通过**

```powershell
python -m pytest app/tests/ui/debug/test_layout_tracer.py -v
```

Expected: 5 passed.

- [ ] **Step 5: 跑全套确认无回归**

```powershell
python -m pytest app/tests/ -v --tb=short 2>&1 | Select-String -Pattern "passed|failed|error" | Select-Object -Last 10
```

Expected: 57 passed (52 baseline + 5 new) / 2 pre-existing failed.

- [ ] **Step 6: Commit**

```powershell
git add app/ui/debug/layout_tracer.py app/tests/ui/debug/test_layout_tracer.py
git commit -m "feat(debug): layout_tracer 递归打印 widget 树 pos/size/hints

wave 2 phase 1 - 用于诊断 layout 错乱问题.
输出每个 widget 的 pos/size/size_hint/pos_hint, 子节点缩进 2 空格.
配合 event_logger 在 dev_panel 触发 dump 用.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 3: main.py + dev_panel 集成

**Files:**
- Modify: `app/main.py` — 启动时检测 env var 调 install_event_logger
- Modify: dev_panel 所在文件 (Task 实施时 grep 查清) — 加 "Dump widget tree" 按钮
- Test: 新增 `app/tests/ui/debug/test_integration.py`

#### 子任务 3a: main.py 接入 install_event_logger

- [ ] **Step 1: 找到 main.py 的 App.build 或类似启动位置**

```powershell
# 实施前查清 — main.py 在哪个生命周期 hook 启动 UI
Get-Content app/main.py | Select-String -Pattern "build|on_start|run" -Context 2,2
```

记下 build 方法所在行号。

- [ ] **Step 2: 写失败的测试 `test_integration.py`**

```python
"""main 接入 + dev_panel 按钮集成测试。"""

from __future__ import annotations

import os
from unittest import mock


class TestMainAutoInstall:
    """启动时 env var 控制 install_event_logger 行为。"""

    def setup_method(self) -> None:
        from app.ui.debug import event_logger
        event_logger._INSTALLED = False

    def test_main_calls_install_when_debug_env_set(self) -> None:
        """SOLOIST_DEBUG=1 时, app 启动后 _INSTALLED 应为 True。"""
        from app.ui.debug import event_logger
        from app.main import _setup_debug_hooks  # 新增的辅助函数

        with mock.patch.dict(os.environ, {"SOLOIST_DEBUG": "1"}):
            _setup_debug_hooks()

        assert event_logger._INSTALLED is True

    def test_main_skips_install_when_debug_env_unset(self) -> None:
        """SOLOIST_DEBUG 未设时, _INSTALLED 应保持 False。"""
        from app.ui.debug import event_logger
        from app.main import _setup_debug_hooks

        with mock.patch.dict(os.environ, {"SOLOIST_DEBUG": "0"}, clear=False):
            _setup_debug_hooks()

        assert event_logger._INSTALLED is False
```

- [ ] **Step 3: 跑测试确认失败**

```powershell
python -m pytest app/tests/ui/debug/test_integration.py -v
```

Expected: ImportError on `_setup_debug_hooks`.

- [ ] **Step 4: 在 `app/main.py` 加 `_setup_debug_hooks` 并在 `build` 内调用**

把以下函数加到 `app/main.py` 文件顶部 import 之后、SoloistApp class 之前。如果文件结构不同, 加到 build 方法可访问的位置:

```python
def _setup_debug_hooks() -> None:
    """启动诊断 — 仅在 SOLOIST_DEBUG=1 时安装事件日志。

    必须在任何 UI 组件实例化之前调用 (否则装饰只对之后实例化的对象生效)。
    """
    from app.ui.debug.event_logger import install_event_logger
    install_event_logger()
```

然后在 `App.build()` 方法的**最开头** (super().build() 之前如果有, 或者类构造的第一行) 调用:

```python
class SoloistApp(App):
    def build(self) -> Widget:
        _setup_debug_hooks()  # 必须最先, 让后续 UI 实例化时已装饰
        # ... 原有 build 逻辑
```

> 注意: 因为 event_logger 用 monkey-patch class method, 必须在 PixelButton/ModalView 实例化前装好。`build()` 第一行最稳。

- [ ] **Step 5: 跑测试确认通过**

```powershell
python -m pytest app/tests/ui/debug/test_integration.py -v
```

Expected: 2 passed.

#### 子任务 3b: dev_panel 加 Dump widget tree 按钮

- [ ] **Step 6: 找到 dev_panel 所在文件**

```powershell
# Grep dev_panel / DevPanel 找文件
```

用 Grep 工具搜 `dev_panel|DevPanel|开发面板` 在 `app/ui/` 下。

- [ ] **Step 7: 在 dev_panel 加按钮 (代码片段)**

找到 dev_panel 容器 add_widget 调用群末尾, 添加:

```python
# Dump widget tree 按钮 (诊断用)
dump_btn = PixelButton(
    text="Dump widget tree",
    color=COLORS["CARD_SHADOW"],  # 暗色, 表示工具非主功能
    size_mode="small",
    size_hint_y=None,
)
dump_btn.bind(on_press=lambda _: self._on_dump_widget_tree())
panel_layout.add_widget(dump_btn)  # panel_layout = dev_panel 的容器变量名
```

然后在同 class 加方法:

```python
def _on_dump_widget_tree(self) -> None:
    """Dump 当前 widget 树到 Kivy Logger。"""
    from kivy.app import App
    from kivy.logger import Logger
    from app.ui.debug.layout_tracer import trace_layout

    root = App.get_running_app().root
    if root is None:
        Logger.info("[LAY] root is None, nothing to dump")
        return
    Logger.info(trace_layout(root, label="dev_panel dump"))
```

- [ ] **Step 8: 跑全套确认无回归**

```powershell
python -m pytest app/tests/ -v --tb=short 2>&1 | Select-String -Pattern "passed|failed|error" | Select-Object -Last 10
```

Expected: 59 passed (上一个 commit 后 57 + 2 新) / 2 pre-existing failed.

- [ ] **Step 9: Commit**

```powershell
git add app/main.py app/tests/ui/debug/test_integration.py
# 加 dev_panel 文件 (Step 6 找到的)
git commit -m "feat(debug): main.py 启动接入 event_logger, dev_panel 加 Dump 按钮

wave 2 phase 1 整合 - SOLOIST_DEBUG=1 启动 app 时自动装事件日志,
dev_panel 'Dump widget tree' 按钮触发 layout_tracer 把树打到 Kivy log.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 4: andy 实测收集 log (controller 协调, 非 implementer 任务)

> 这一步**不能由 implementer subagent 自己完成** — 需要 controller (Claude) + andy 协作。

**Files:**
- Create: `doc/wave2-traces/README.md` — 记录怎么收集 log
- Output: `doc/wave2-traces/session-YYYY-MM-DD-HHMM.txt` — andy 操作时的 log

- [ ] **Step 1: Controller 写 `doc/wave2-traces/README.md`**

```markdown
# Wave 2 诊断 log 收集说明

## 收集方法

1. 关闭运行中的 app
2. 在 PowerShell 设置环境变量并启动:
   ```powershell
   $env:SOLOIST_DEBUG = "1"
   python -m app.main 2>&1 | Tee-Object -FilePath "doc\wave2-traces\session-2026-06-06-1700.txt"
   ```
3. 按下述场景操作, log 自动写文件:

### 必走场景 (覆盖 8 个 bug)

| 场景 | 操作 |
|---|---|
| B1 添加任务 | 切到对赌页 → 点 "+ 添加任务" → (无论弹不弹) 关掉对话框 / 等 3 秒 |
| B2 战报弹出 | 切到打卡页 → 完成今日所有打卡 (或用 dev_panel 跳到能点状态) → 点 "结束今日并查看战报" |
| B3 历史看战报 | 切到历史页 → 点任意有打卡记录的日期 |
| B4 对赌页排版 | 切到对赌页 → 点 dev_panel "Dump widget tree" 按钮 |
| B5 底部 nav | 在主界面 → 点 dev_panel "Dump widget tree" |
| B6 弹窗按钮溢出 | 设置页 → 点任意金额项 (拍摄日奖励等) → 弹窗内点 dev_panel dump (如果可达) |
| B7 开发面板 | 进入 dev_panel 时 dump widget tree |
| B8 输入框 IME | 在添加任务对话框 (如果能弹) 内点输入框, 试中文输入 |

### 提交

把生成的 .txt 文件提交给 controller (Claude), 我会基于 log 写 Phase 2 plan。
```

- [ ] **Step 2: Controller 告诉 andy 开始实测**

Controller 提示 andy:

> "Phase 1 工具就绪。请按 `doc/wave2-traces/README.md` 收集 log:
>
> 1. 关掉运行的 app (如有)
> 2. PowerShell: `$env:SOLOIST_DEBUG = "1"`, 然后启动 + tee 到文件
> 3. 按 README 8 个场景操作
> 4. 把 .txt 路径告诉我"

- [ ] **Step 3: andy 完成实测**

andy 操作 + 提交 log 文件路径。

- [ ] **Step 4: Controller 读 log, 分析 8 个 bug 的根因, 写 Phase 2 plan**

新文件 `doc/superpowers/plans/2026-06-06-wave2-phase2-fixes.md`, 按 log 划分 batch:
- Batch A: 事件链路类 (如果 log 显示 PixelButton.on_press 触发但 dialog.open 没执行 → batch fix callback 链)
- Batch B: Layout 类 (按 trace_layout 输出, 找出 width/height 异常的 widget)
- Batch C: Input 类 (如果 dialog 修完, focus log 显示 TextInput 没 focus → IME 问题)

Phase 2 plan 是 controller 阶段 1 完成后单独写, **不在本 plan 内**。

---

## Self-Review (已完成)

### 1. Spec 覆盖检查

Wave 2 spec (`doc/superpowers/specs/2026-06-06-wave2-ui-fix-design.md`) 第 4 节策略:

| Spec 要求 | 本 plan 覆盖 |
|---|---|
| 4.1.1 event_logger.py 装饰 PixelButton/ModalView/TextInput | ✅ Task 1 完整覆盖 |
| 4.1.2 layout_tracer.py 打印 widget 树 | ✅ Task 2 完整覆盖 |
| 4.1.3 main.py 集成 + dev_panel Dump 按钮 | ✅ Task 3 a + b |
| 4.1.4 andy 实测 + log 提交 | ✅ Task 4 controller 协调 |
| Phase 1 验收: 阶段 1 完后能定位每个 bug 根因 | ✅ Task 4 Step 4 controller 基于 log 写 Phase 2 plan |
| Open Q1 永久保留 gated by env var | ✅ Task 1 install_event_logger 检查 SOLOIST_DEBUG |
| Open Q2 wave2-traces 不入 git | ✅ 已 commit f8ee93e 加 gitignore |
| Open Q3 真实数据诊断 | ✅ Task 4 README 让 andy 用自己的 app 数据 |

Phase 2 / Phase 3 不在本 plan, spec 第 4.2 / 4.3 节明确说要看 log 后再设计, 符合诊断驱动原则。

### 2. Placeholder 扫描

- "Task 3 Step 6: 找到 dev_panel 所在文件" — 写明了 grep 命令, 不是 placeholder
- "Phase 2 plan 是 controller 阶段 1 完成后单独写" — 明确说明, 不是 TODO
- 无 TBD / fill-in-details / similar-to-Task-N

### 3. 类型/命名一致性

- `install_event_logger() -> bool` 在 Task 1 + Task 3 一致
- `trace_layout(widget, label="") -> str` 在 Task 2 + Task 3 一致
- `_INSTALLED` 全局 flag 在 Task 1 测试 + Task 3 测试一致 reset
- `SOLOIST_DEBUG` env var 名称三处一致

---

## 执行说明

Plan 写完后 controller 应:

1. Commit plan
2. 用 superpowers:subagent-driven-development 派遣 implementer 跑 Task 1 → 2 → 3
3. Task 4 由 controller 直接协调 andy
