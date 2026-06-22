# 个性化激励语句 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让用户可在设置页增/删自己的激励语录，战报里的鼓励语将从用户语录里随机抽取，用户为空时回落到内置 5 句。

**Architecture:** 复用 `settings` 表 + 一个 JSON 数组字段，SettingsService 加 2 个 helper 封装编解码，ReportService 在已留扩展点 `_pick_encouragement` 内部读 settings_repo 切换池源，SettingsScreen 加第 6 个 CollapsibleGroup 直接管理。无 DB 迁移、无新 repository、无新 service。

**Tech Stack:** Python 3.11, Kivy（UI）, pytest（测试）, SQLite via `app.repositories.base.BaseRepo`, JSON via stdlib。

**关联设计文档：** `docs/superpowers/specs/2026-06-22-personalized-encouragements-design.md`

---

## 文件结构

| 路径 | 角色 | 操作 |
| --- | --- | --- |
| `app/services/settings_service.py` | 增 DEFAULTS key + 2 个 helper + `import json` | 修改 |
| `app/services/report_service.py` | 新增 `_read_user_encouragements`，改写 `_pick_encouragement`，加 `import json` | 修改 |
| `app/ui/screens/settings_screen.py` | 在 `__init__` 加第 6 个 CollapsibleGroup，新增 4 个方法 | 修改 |
| `app/tests/test_settings_service.py` | 新增 4 个单元测试 | 修改 |
| `app/tests/test_report_service.py` | 新增 2 个单元测试 | 修改 |

---

## Task 1: SettingsService — 加默认值 + JSON helper

**Files:**
- Modify: `app/services/settings_service.py`
- Test: `app/tests/test_settings_service.py`

- [ ] **Step 1.1: 写 4 个失败测试**

在 `app/tests/test_settings_service.py` 文件末尾 `TestSettingsService` 类内追加：

```python
    def test_user_encouragements_default_empty(self, svc: SettingsService) -> None:
        assert svc.get_user_encouragements() == []

    def test_user_encouragements_set_and_get_roundtrip(self, svc: SettingsService) -> None:
        svc.set_user_encouragements(["坚持就是胜利", "今天也要加油"])
        assert svc.get_user_encouragements() == ["坚持就是胜利", "今天也要加油"]

    def test_user_encouragements_handles_corrupted_json(
        self, svc: SettingsService, temp_db: str
    ) -> None:
        SettingsRepo(temp_db).set("encouragements_user", "not json {{")
        assert svc.get_user_encouragements() == []

    def test_user_encouragements_set_publishes_event(self, svc: SettingsService) -> None:
        events: list[dict[str, Any]] = []

        def handler(et: EventType, payload: dict[str, Any]) -> None:
            events.append(payload)

        get_event_bus().subscribe(EventType.SETTINGS_CHANGED, handler)
        svc.set_user_encouragements(["新语录"])
        assert len(events) == 1
        assert events[0]["key"] == "encouragements_user"
```

并在文件顶部已有 `from app.services.settings_service import SettingsService` 之外，确认 `SettingsRepo`、`EventType`、`get_event_bus`、`Any` 已被导入（它们已存在，无需新增）。

- [ ] **Step 1.2: 跑测试验证全部失败**

Run: `pytest app/tests/test_settings_service.py -v -k user_encouragements`

预期：4 个测试全部 FAIL，错误信息类似 `AttributeError: 'SettingsService' object has no attribute 'get_user_encouragements'`。

- [ ] **Step 1.3: 在 settings_service.py 顶部加 `import json` 和 `Logger`**

在 `app/services/settings_service.py` 第 3 行 `from __future__ import annotations` 的**下方**插入一行：

```python
import json
```

在第 5 行（即 `from app.repositories.settings_repo import SettingsRepo` 那行）**之前**插入：

```python
from kivy.logger import Logger
```

最终顶部 import 顺序：

```python
"""设置模块服务层"""

from __future__ import annotations

import json

from kivy.logger import Logger

from app.repositories.settings_repo import SettingsRepo
from app.services.event_bus import EventType, get_event_bus
```

理由：与项目内其他 service（report_service、motivation_service）保持一致，统一使用 Kivy Logger。`json` 是 stdlib，无需依赖管理。

- [ ] **Step 1.4: 在 DEFAULTS 中加新键**

在 `DEFAULTS` 字典末尾（即 `"ntfy_server"` 行下面）追加一行：

```python
        "encouragements_user": "[]",
```

完整修改后 DEFAULTS 末尾：

```python
        "ntfy_enabled": "0",
        "ntfy_topic": "",
        "ntfy_server": "https://ntfy.sh",
        "encouragements_user": "[]",
    }
```

- [ ] **Step 1.5: 在 SettingsService 类内加 `get_user_encouragements`**

在类内 `is_work_day` 方法下方追加：

```python
    def get_user_encouragements(self) -> list[str]:
        """读取用户自定义激励语录，JSON 解析失败或类型异常时返回空列表"""
        raw = self.get("encouragements_user")
        if not raw:
            return []
        try:
            items = json.loads(raw)
        except json.JSONDecodeError:
            Logger.warning(
                "SettingsService: encouragements_user JSON decode failed: %r", raw
            )
            return []
        if not isinstance(items, list):
            return []
        return [s for s in items if isinstance(s, str) and s.strip()]
```

- [ ] **Step 1.6: 加 `set_user_encouragements`**

紧接 `get_user_encouragements` 下方追加：

```python
    def set_user_encouragements(self, items: list[str]) -> None:
        """写入用户自定义激励语录，自动 JSON 编码并发布 SETTINGS_CHANGED 事件"""
        encoded = json.dumps(items, ensure_ascii=False)
        self.set("encouragements_user", encoded)
```

注意：复用 `self.set()` 自动 publish `SETTINGS_CHANGED`，payload `{"key": "encouragements_user", "value": encoded}`。

- [ ] **Step 1.7: 跑测试验证全部通过 + 跑全套 SettingsService 测试无回归**

Run: `pytest app/tests/test_settings_service.py -v`

预期：包括 4 个新增在内的全部测试 PASS（共约 16 个）。

- [ ] **Step 1.8: Commit**

```bash
git add app/services/settings_service.py app/tests/test_settings_service.py
git commit -m "feat(settings): 加用户自定义激励语录的 JSON 读写 helper"
```

---

## Task 2: ReportService — 接入用户语录池

**Files:**
- Modify: `app/services/report_service.py:249-252`
- Test: `app/tests/test_report_service.py`

- [ ] **Step 2.1: 写 2 个失败测试**

在 `app/tests/test_report_service.py` 文件末尾 `TestReportService` 类内追加：

```python
    def test_pick_encouragement_uses_user_list_when_present(self, temp_db: str) -> None:
        from app.repositories.settings_repo import SettingsRepo

        settings_repo = SettingsRepo(temp_db)
        settings_repo.set("encouragements_user", '["only one"]')
        svc = ReportService(
            CheckinRepo(temp_db),
            LedgerRepo(temp_db),
            ShootingRepo(temp_db),
            settings_repo,
        )
        for _ in range(100):
            assert svc._pick_encouragement("2026-06-01") == "only one"

    def test_pick_encouragement_falls_back_to_builtin_when_user_empty(
        self, temp_db: str
    ) -> None:
        from app.repositories.settings_repo import SettingsRepo
        from app.services.report_service import ENCOURAGEMENTS

        svc = ReportService(
            CheckinRepo(temp_db),
            LedgerRepo(temp_db),
            ShootingRepo(temp_db),
            SettingsRepo(temp_db),
        )
        results = {svc._pick_encouragement("2026-06-01") for _ in range(100)}
        assert results.issubset(set(ENCOURAGEMENTS))
        assert len(results) >= 1
```

- [ ] **Step 2.2: 跑测试验证全部失败**

Run: `pytest app/tests/test_report_service.py -v -k pick_encouragement`

预期：
- `test_pick_encouragement_uses_user_list_when_present` FAIL：因为当前 `_pick_encouragement` 直接返回 `random.choice(ENCOURAGEMENTS)`，永远不会等于 `"only one"`。
- `test_pick_encouragement_falls_back_to_builtin_when_user_empty` 可能 PASS（巧合通过），但因为代码尚未读 user list，这一通过是误打误撞。Step 2.5 重写后这两个测试都靠新逻辑通过。

- [ ] **Step 2.3: 加 `import json`**

在 `app/services/report_service.py` 第 5 行 `import random` 的**正下方**加一行：

```python
import json
```

**决定不引入 Logger**：`_read_user_encouragements` 的 JSON 解析失败属于数据损坏的边缘情况，静默兜底为空（让逻辑回落到内置 5 句）已是合理行为，且 SettingsService.get_user_encouragements 已经在 Logger.warning 这一层做过日志记录，无需在 ReportService 重复。

- [ ] **Step 2.4: 加 `_read_user_encouragements` 私有方法**

在 `_pick_encouragement` 方法**上方**插入：

```python
    def _read_user_encouragements(self) -> list[str]:
        """从 settings_repo 直接读 encouragements_user 并 JSON 解析；失败兜底为空"""
        if not self._settings_repo:
            return []
        raw = self._settings_repo.get("encouragements_user")
        if not raw:
            return []
        try:
            items = json.loads(raw)
        except json.JSONDecodeError:
            return []
        if not isinstance(items, list):
            return []
        return [s for s in items if isinstance(s, str) and s.strip()]
```

注意：不调 `SettingsService.get_user_encouragements`，避免新增依赖；直接复用已注入的 `_settings_repo`，行为与 SettingsService 版本一致。

- [ ] **Step 2.5: 改写 `_pick_encouragement`**

替换原有第 249-252 行：

```python
    def _pick_encouragement(self, date: str) -> str:  # noqa: ARG002
        # 扩展点：未来从用户自定义语录库（encouragement_repo）随机抽取，
        # 合并 ENCOURAGEMENTS 作兜底；此处签名保持稳定。
        return random.choice(ENCOURAGEMENTS)
```

为：

```python
    def _pick_encouragement(self, date: str) -> str:  # noqa: ARG002
        user_items = self._read_user_encouragements()
        pool = user_items if user_items else ENCOURAGEMENTS
        return random.choice(pool)
```

注释中的"扩展点"语义已实现，可去掉那两行注释。

- [ ] **Step 2.6: 跑测试验证全部通过 + 跑全套 ReportService 测试无回归**

Run: `pytest app/tests/test_report_service.py -v`

预期：包括 2 个新增在内的全部测试 PASS（约 8 个）。

附加：跑一遍 ReportPreview 渲染测试，确认 `data.encouragement` 仍然非空：

Run: `pytest app/tests/ui/test_report_preview_render.py -v`

预期：全部 PASS（这些测试自己提供 encouragement 字符串，不走 _pick_encouragement，但跑一遍确认无回归）。

- [ ] **Step 2.7: Commit**

```bash
git add app/services/report_service.py app/tests/test_report_service.py
git commit -m "feat(report): _pick_encouragement 优先用用户自定义语录，空时回落内置"
```

---

## Task 3: SettingsScreen — 折叠分组 + 增删交互

**Files:**
- Modify: `app/ui/screens/settings_screen.py`

UI 层无单元测试，依赖人工冒烟。本任务的所有改动只在该单文件内。

- [ ] **Step 3.1: 在 `__init__` 末尾注册第 6 个 CollapsibleGroup**

在 `app/ui/screens/settings_screen.py:149` 行 `content.add_widget(group5)` 之后、`scroll.add_widget(content)` 之前，插入：

```python
        # --- 6. 个性化激励语句组 ---
        enc_content = self._build_encouragement_group()
        group6 = CollapsibleGroup(
            title="个性化激励语句",
            content=enc_content,
            collapsed=True,
        )
        content.add_widget(group6)
```

- [ ] **Step 3.2: 实现 `_build_encouragement_group()` 方法**

在类内（建议放在 `_build_ntfy_group` 之后、`_on_ntfy_test` 之前位置不重要，找一处方法分组靠后的位置即可）追加：

```python
    # ------------------------------------------------------------------
    # 个性化激励语句组
    # ------------------------------------------------------------------

    def _build_encouragement_group(self) -> Widget:
        box = self._make_vbox()

        # 顶部输入行：输入框 + 添加按钮
        input_row = BoxLayout(
            orientation="horizontal",
            spacing=CARD_PADDING,
            padding=[CARD_PADDING, 4],
            size_hint=(1, None),
            height=48,
        )
        self._enc_input = PixelInput(
            hint_text="添加一条激励语句…",
            value="",
            password=False,
            size_hint=(1, 1),
        )
        input_row.add_widget(self._enc_input)

        add_btn = PixelButton(
            text="添加",
            size_mode="small",
            size_hint=(None, 1),
            width=70,
            color=MINT_GREEN,
        )
        add_btn.bind(on_press=lambda _b: self._on_encouragement_add())
        input_row.add_widget(add_btn)

        box.add_widget(input_row)

        # 列表容器（每次刷新清空再重建）
        self._enc_list_box = BoxLayout(
            orientation="vertical",
            size_hint=(1, None),
            spacing=2,
        )
        self._enc_list_box.bind(minimum_height=self._enc_list_box.setter("height"))
        box.add_widget(self._enc_list_box)

        self._refresh_encouragement_list()
        return box
```

注意：`MINT_GREEN` 已在文件顶部从 `DOPAMINE_COLORS["mint"]["light"]` 别名为该名（参见第 46 行），可直接使用。`PixelInput`、`PixelButton` 已被导入。

- [ ] **Step 3.3: 实现 `_refresh_encouragement_list()` 方法**

紧接 `_build_encouragement_group` 后追加：

```python
    def _refresh_encouragement_list(self) -> None:
        """重建列表 UI：先清空容器，再按当前数据重新生成行"""
        self._enc_list_box.clear_widgets()

        items: list[str] = []
        if self._settings_service:
            items = self._settings_service.get_user_encouragements()

        if not items:
            empty_lbl = Label(
                text="尚未添加，战报将随机使用内置 5 句",
                font_size=FONT_SIZE_SMALL,
                color=self._to_rgba(TEXT_GRAY),
                size_hint=(1, None),
                height=40,
                halign="center",
                valign="middle",
            )
            empty_lbl.bind(size=lambda lbl, _: setattr(lbl, "text_size", lbl.size))
            self._enc_list_box.add_widget(empty_lbl)
            return

        for idx, text in enumerate(items):
            row = BoxLayout(
                orientation="horizontal",
                spacing=CARD_PADDING,
                padding=[CARD_PADDING, 4],
                size_hint=(1, None),
                height=48,
            )
            lbl = Label(
                text=text,
                font_size=FONT_SIZE_BODY,
                color=self._to_rgba(TEXT_BROWN),
                size_hint=(1, 1),
                halign="left",
                valign="middle",
            )
            lbl.bind(size=lambda inst, _: setattr(inst, "text_size", (inst.width, None)))
            row.add_widget(lbl)

            del_btn = PixelButton(
                text="X",
                size_mode="small",
                size_hint=(None, 1),
                width=40,
                color=COLORS["CARD_SHADOW"],
            )
            del_btn.bind(on_press=lambda _b, i=idx: self._on_encouragement_delete(i))
            row.add_widget(del_btn)

            self._enc_list_box.add_widget(row)
```

- [ ] **Step 3.4: 实现 `_on_encouragement_add()` 方法**

紧接 `_refresh_encouragement_list` 后追加：

```python
    def _on_encouragement_add(self) -> None:
        """添加按钮：取输入框文本，校验后入库并刷新列表"""
        if not self._settings_service:
            self.show_toast("设置服务未初始化")
            return

        text = self._enc_input.text.strip()
        if not text:
            self.show_toast("请输入内容")
            return
        if len(text) > 100:
            self.show_toast("单条不能超过 100 字")
            return

        current = self._settings_service.get_user_encouragements()
        if text in current:
            self.show_toast("已存在相同语录")
            return

        try:
            self._settings_service.set_user_encouragements(current + [text])
        except Exception as e:  # noqa: BLE001
            Logger.error(f"SettingsScreen: 添加激励语录失败 {e}")
            self.show_toast("保存失败，请重试")
            return

        self._enc_input.text = ""
        self._refresh_encouragement_list()
```

- [ ] **Step 3.5: 实现 `_on_encouragement_delete()` 方法**

紧接 `_on_encouragement_add` 后追加：

```python
    def _on_encouragement_delete(self, index: int) -> None:
        """删除按钮：按索引移除一条并刷新列表"""
        if not self._settings_service:
            return
        current = self._settings_service.get_user_encouragements()
        if 0 <= index < len(current):
            new_list = current[:index] + current[index + 1 :]
            try:
                self._settings_service.set_user_encouragements(new_list)
            except Exception as e:  # noqa: BLE001
                Logger.error(f"SettingsScreen: 删除激励语录失败 {e}")
                self.show_toast("删除失败，请重试")
                return
            self._refresh_encouragement_list()
```

- [ ] **Step 3.6: 启动 app 做人工冒烟**

在 PowerShell 中运行项目启动命令（按项目惯例，例如 `python -m app.main`，如不确定先看 `app/main.py` 入口或现有启动脚本）：

Run: `python -m app.main`

冒烟步骤：
1. 启动后进入"设置"标签页
2. 找到"个性化激励语句"分组（应该是最末尾，折叠状态），点击展开
3. 看到空状态文本"尚未添加，战报将随机使用内置 5 句"
4. 在输入框输入"测试语录 A"，点"添加"
5. 列表里应出现一行"测试语录 A"，右侧有 X 按钮
6. 再添加"测试语录 B"、"测试语录 C"
7. 点中间一条的 X，列表应剩 2 条
8. 测试空字符串：清空输入框点添加 → 应弹 toast "请输入内容"
9. 测试重复：再次添加"测试语录 A" → 弹 toast "已存在相同语录"
10. 测试超长：粘贴一个 > 100 字的字符串 → 弹 toast "单条不能超过 100 字"
11. 切到主页 / 触发战报生成 → 查看战报底部的鼓励语，应来自剩余 2 条之一（多次触发统计应只在 2 条之间出现）
12. 删光所有自定义语录 → 再生成战报 → 鼓励语应回落到 5 条内置之一
13. 全程不应有崩溃或 traceback 出现在 Kivy Logger 输出

人工记录冒烟结论：上述 13 步全部通过 / 哪几步失败。

- [ ] **Step 3.7: Commit**

```bash
git add app/ui/screens/settings_screen.py
git commit -m "feat(ui/settings): 新增「个性化激励语句」折叠分组（增/删/校验）"
```

---

## 完成标准

- 所有单元测试 PASS（settings + report 套件）
- UI 人工冒烟 13 步全部通过
- 不引入新的 DB 迁移、新的 repository、新的 service
- 3 个 commit 干净分布：service 改动、报告接入、UI 接入

## 后续可能扩展（不在本计划范围）

- "恢复 / 导入内置语录"按钮
- 拖动排序
- 行内编辑
- 导出 / 分享一份语录给好友
