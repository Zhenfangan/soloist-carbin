# 前端 UI 修复 第一波 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 4 个 100% 确定的代码 bug + 删除 2 个未使用字体，为第二波复测提供干净基线。

**Architecture:** 每个 bug 一个 Task。TDD 流程：写回归测试断言新的正确行为 → 跑测试 FAIL → 改 1 行代码 → 跑测试 PASS → 跑整套 pytest 回归 → 单独提交。字体清理 Task 无测试，直接 git rm。

**Tech Stack:** Python 3.12 + Kivy 2.3.1 + pytest (offscreen) + mypy strict + ruff

**Spec:** [`doc/superpowers/specs/2026-06-05-frontend-ui-fix-design.md`](../specs/2026-06-05-frontend-ui-fix-design.md)

---

## Task 1: 修复 PixelInput._redraw 亮面 right 矩形 size bug

**Bug:** `pixel_input.py:103` 写成 `size=(w, h)`，应为 `(bw, h)`。导致亮面 right 边框画成 widget 等宽的白矩形，覆盖输入区右半。

**Files:**
- Modify: `app/ui/components/pixel_input.py:103` (一行)
- Test: `app/tests/ui/test_visual.py` (新增一个方法)

---

- [ ] **Step 1: 在 `test_visual.py` 的 `TestComponentBackgrounds` 类内添加回归测试**

打开 `app/tests/ui/test_visual.py`，在 `test_pixel_input_has_background` 方法**之后**添加：

```python
    def test_pixel_input_right_border_is_thin(self) -> None:
        """亮面 right 矩形宽度应为 BORDER_WIDTH (2)，不是整个 widget 宽度。"""
        from kivy.graphics import Rectangle
        from app.ui.tokens import BORDER_WIDTH

        inp = PixelInput()
        inp.size = (200, 40)
        inp.pos = (10, 20)
        inp._redraw()

        rects = [c for c in inp.canvas.before.children if isinstance(c, Rectangle)]
        # 5 个矩形: 背景 + 暗面 top + 暗面 left + 亮面 bottom + 亮面 right
        assert len(rects) == 5, f"expected 5 rectangles, got {len(rects)}"

        right_border = rects[-1]  # _redraw 顺序最后画亮面 right
        assert right_border.size[0] == BORDER_WIDTH, (
            f"right border width should be {BORDER_WIDTH}, got {right_border.size[0]}"
        )
        assert right_border.size[1] == 40, (
            f"right border height should be 40, got {right_border.size[1]}"
        )
```

- [ ] **Step 2: 跑测试验证 FAIL**

```powershell
pytest app/tests/ui/test_visual.py::TestComponentBackgrounds::test_pixel_input_right_border_is_thin -v
```

期望: FAIL，message 类似 `right border width should be 2, got 200`

- [ ] **Step 3: 修改 `app/ui/components/pixel_input.py:103`**

`old_string`:
```python
            # 亮面 right
            Rectangle(pos=(x + w - bw, y), size=(w, h))
```

`new_string`:
```python
            # 亮面 right
            Rectangle(pos=(x + w - bw, y), size=(bw, h))
```

- [ ] **Step 4: 跑测试验证 PASS**

```powershell
pytest app/tests/ui/test_visual.py::TestComponentBackgrounds::test_pixel_input_right_border_is_thin -v
```

期望: PASS

- [ ] **Step 5: 跑整套 UI 测试 + 类型/lint 检查无回归**

```powershell
pytest app/tests/ui/ -v
mypy --strict app/ui/components/pixel_input.py
ruff check app/ui/components/pixel_input.py
```

三者全过。

- [ ] **Step 6: 提交**

```powershell
git add app/ui/components/pixel_input.py app/tests/ui/test_visual.py
git commit -m "fix(ui): PixelInput 亮面 right 矩形 size 从 (w,h) 改为 (bw,h)"
```

---

## Task 2: 修复 PixelStepper._redraw 同样的 right size bug

**Bug:** `pixel_stepper.py:151` 同样的 copy-paste bug。导致 stepper 右半被白矩形覆盖，[+] 按钮看不见。

**Files:**
- Modify: `app/ui/components/pixel_stepper.py:151` (一行)
- Test: `app/tests/ui/test_visual.py`

---

- [ ] **Step 1: 添加回归测试**

在 `app/tests/ui/test_visual.py` 的 `TestComponentBackgrounds` 类内加：

```python
    def test_pixel_stepper_right_border_is_thin(self) -> None:
        """亮面 right 矩形宽度应为 BORDER_WIDTH。"""
        from kivy.graphics import Rectangle
        from app.ui.tokens import BORDER_WIDTH

        stepper = PixelStepper(value=1)
        stepper.size = (140, 32)
        stepper.pos = (0, 0)
        stepper._redraw()

        rects = [c for c in stepper.canvas.before.children if isinstance(c, Rectangle)]
        assert len(rects) == 5, f"expected 5 rectangles, got {len(rects)}"

        right_border = rects[-1]
        assert right_border.size[0] == BORDER_WIDTH, (
            f"right border width should be {BORDER_WIDTH}, got {right_border.size[0]}"
        )
        assert right_border.size[1] == 32, (
            f"right border height should be 32, got {right_border.size[1]}"
        )
```

- [ ] **Step 2: 跑测试验证 FAIL**

```powershell
pytest app/tests/ui/test_visual.py::TestComponentBackgrounds::test_pixel_stepper_right_border_is_thin -v
```

期望: FAIL，message 类似 `right border width should be 2, got 140`

- [ ] **Step 3: 修改 `app/ui/components/pixel_stepper.py:151`**

`old_string`:
```python
            Color(*self._to_rgba("#FFFFFF"))
            Rectangle(pos=(x, y), size=(w, bw))
            Rectangle(pos=(x + w - bw, y), size=(w, h))
```

`new_string`:
```python
            Color(*self._to_rgba("#FFFFFF"))
            Rectangle(pos=(x, y), size=(w, bw))
            Rectangle(pos=(x + w - bw, y), size=(bw, h))
```

- [ ] **Step 4: 跑测试验证 PASS**

```powershell
pytest app/tests/ui/test_visual.py::TestComponentBackgrounds::test_pixel_stepper_right_border_is_thin -v
```

期望: PASS

- [ ] **Step 5: 跑整套 UI 测试无回归**

```powershell
pytest app/tests/ui/ -v
mypy --strict app/ui/components/pixel_stepper.py
ruff check app/ui/components/pixel_stepper.py
```

- [ ] **Step 6: 提交**

```powershell
git add app/ui/components/pixel_stepper.py app/tests/ui/test_visual.py
git commit -m "fix(ui): PixelStepper 亮面 right 矩形 size 从 (w,h) 改为 (bw,h)"
```

---

## Task 3: 修复 AddTaskDialog input 的 pos_hint 错位

**Bug:** `add_task_dialog.py:117` 用 `pos_hint={"x": 0.5, "y": 0.58}`，意味着 input 左边在 card 50% 位置，而 input 宽 288，超出 card (320) 右边 128px。应改为 `center_x`。

**Files:**
- Modify: `app/ui/components/add_task_dialog.py:117` (一行)
- Test: `app/tests/ui/test_base_components.py`（如已有 AddTaskDialog 测试就加进去，否则新建一个测试类）

---

- [ ] **Step 0: 检查是否已有 AddTaskDialog 测试**

```powershell
pytest app/tests/ui/test_base_components.py -v --collect-only 2>&1 | grep -i AddTaskDialog
```

如果没有任何 AddTaskDialog 测试输出，下一步新建测试类；否则在已有类内加。

- [ ] **Step 1: 添加回归测试到 `app/tests/ui/test_base_components.py`**

在文件末尾追加（如果没有 AddTaskDialog 测试类）：

```python
class TestAddTaskDialogLayout:
    """AddTaskDialog 内部 widget 布局正确性。"""

    def test_desc_input_uses_center_x_not_x(self) -> None:
        """输入框 pos_hint 必须用 center_x，否则会溢出 card。"""
        from app.ui.components.add_task_dialog import AddTaskDialog

        dialog = AddTaskDialog()
        pos_hint = dialog._desc_input.pos_hint

        assert "center_x" in pos_hint, (
            f"_desc_input.pos_hint should have center_x key, got {pos_hint}"
        )
        assert pos_hint["center_x"] == 0.5, (
            f"_desc_input.pos_hint['center_x'] should be 0.5, got {pos_hint['center_x']}"
        )
        assert "x" not in pos_hint, (
            f"_desc_input.pos_hint should NOT have 'x' key (would offset, not center), got {pos_hint}"
        )
```

如果文件顶部还没有 `from __future__ import annotations`，先加上。

- [ ] **Step 2: 跑测试验证 FAIL**

```powershell
pytest app/tests/ui/test_base_components.py::TestAddTaskDialogLayout::test_desc_input_uses_center_x_not_x -v
```

期望: FAIL，message 类似 `_desc_input.pos_hint should have center_x key, got {'x': 0.5, 'y': 0.58}`

- [ ] **Step 3: 修改 `app/ui/components/add_task_dialog.py:117`**

`old_string`:
```python
        self._desc_input = PixelInput(
            hint_text="例如: 写 3 篇文章",
            size_hint=(None, None),
            size=(card_w - CARD_PADDING * 2, 40),
            pos_hint={"x": 0.5, "y": 0.58},
        )
```

`new_string`:
```python
        self._desc_input = PixelInput(
            hint_text="例如: 写 3 篇文章",
            size_hint=(None, None),
            size=(card_w - CARD_PADDING * 2, 40),
            pos_hint={"center_x": 0.5, "y": 0.58},
        )
```

- [ ] **Step 4: 跑测试验证 PASS**

```powershell
pytest app/tests/ui/test_base_components.py::TestAddTaskDialogLayout::test_desc_input_uses_center_x_not_x -v
```

期望: PASS

- [ ] **Step 5: 跑整套 UI 测试 + 类型/lint 无回归**

```powershell
pytest app/tests/ui/ -v
mypy --strict app/ui/components/add_task_dialog.py
ruff check app/ui/components/add_task_dialog.py
```

- [ ] **Step 6: 提交**

```powershell
git add app/ui/components/add_task_dialog.py app/tests/ui/test_base_components.py
git commit -m "fix(ui): AddTaskDialog input pos_hint 从 x=0.5 改为 center_x=0.5 防止溢出 card"
```

---

## Task 4: 删除未使用的中文像素字体

**Bug:** `app/ui/assets/fonts/FZXS15.ttf` 和 `方正像素15.ttf` 是 andy 之前考虑替换字体时加入的，最终决定保留 SmileySans，所以这两个文件未被引用。

**Files:**
- Delete: `app/ui/assets/fonts/FZXS15.ttf`
- Delete: `app/ui/assets/fonts/方正像素15.ttf`

---

- [ ] **Step 1: 二次确认两文件没有任何代码引用**

```powershell
Get-ChildItem -Recurse -Include *.py -Exclude __pycache__ | Select-String -Pattern "FZXS15|方正像素"
```

期望: 无输出（没有任何 Python 代码引用这两个字体名）。

如果有匹配，停止并向 andy 报告（说明可能误判，需要重新决策）。

- [ ] **Step 2: 删除两个文件**

```powershell
Remove-Item "app/ui/assets/fonts/FZXS15.ttf"
Remove-Item "app/ui/assets/fonts/方正像素15.ttf"
```

- [ ] **Step 3: 跑整套测试 + 字体加载冒烟无回归**

```powershell
pytest app/tests/ui/ -v
python -c "from app.ui.fonts import apply_global_font; apply_global_font(); print('OK')"
```

字体加载冒烟期望: 打印 `OK`，没有异常。

- [ ] **Step 4: 提交**

```powershell
git add -u app/ui/assets/fonts/
git commit -m "chore(ui): 删除未使用的中文像素字体 FZXS15/方正像素15"
```

> 注：`git add -u` 只 stage 已被跟踪文件的删除/修改，不会带入未跟踪文件。如果 git 之前没跟踪过这两个字体（即截图前还未提交它们），需要单独检查：

```powershell
git status app/ui/assets/fonts/
```

如果显示 `Untracked` 而非 `Deleted`，说明文件从未被 git 跟踪，那只需在文件系统删除即可（无需 commit）。

---

## 整体验收（在 4 个 Task 全部完成后做）

- [ ] **Verification 1: 全套测试 + 类型 + lint**

```powershell
pytest app/ -v
mypy --strict app/
ruff check app/
```

三者全过。

- [ ] **Verification 2: 启动 app 让 andy 实测复测**

```powershell
python -m app.main
```

andy 操作：
1. 4 个 Tab 各切一遍
2. 打开"添加任务"弹窗，看输入框是否在 card 内部（不溢出）
3. 试着在输入框点击，看光标是否出现、能否打字
4. 打开"拍摄日奖励"弹窗，看输入框 + 按钮位置
5. 截 3-5 张新图保存到 `doc/ui-design/testphoto/`

- [ ] **Verification 3: 基于新截图生成第二波修复 spec**

针对第二波剩余 bug（#5 底部导航栏、#6 弹窗按钮溢出、#7 输入法）：
- 重新走 brainstorming → spec → plan 流程
- 用第一波后的实测截图作为根因排查输入
- 写到 `doc/superpowers/specs/YYYY-MM-DD-frontend-ui-fix-wave2-design.md`

---

## 不在本计划范围

- 第二波 3 个 bug（#5/#6/#7）—— 需要第一波复测后再制定
- 任何 UI 视觉风格变更
- 任何新功能 / 后端改动
