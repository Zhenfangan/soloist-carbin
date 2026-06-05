# 第一波 UI 修复 — 暂停存档

> 日期: 2026-06-05 18:30 GMT+8
> 状态: **暂停中** — andy 下班，明天继续

---

## 已完成

| Task | 描述 | 提交 SHA | 状态 |
|---|---|---|---|
| Task 1 | PixelInput 亮面 right 矩形 size 修复 + 回归测试 | `9d57257` | ✅ Spec compliant + Code quality APPROVED |
| Task 2 | PixelStepper 亮面 right 矩形 size 修复 + 回归测试 | `509765c` + `c4e7013`（spec 修正搬迁） | ✅ Spec compliant + Code quality APPROVED |

当前 HEAD: `c4e7013`

---

## 待办（明天继续）

| Task | 描述 | 文件 |
|---|---|---|
| Task 3 | AddTaskDialog input 的 `pos_hint` 从 `x=0.5` 改为 `center_x=0.5` + 回归测试 | `app/ui/components/add_task_dialog.py:117`, `app/tests/ui/test_base_components.py` |
| Task 4 | 删除未用的中文像素字体 `FZXS15.ttf` + `方正像素15.ttf` | `app/ui/assets/fonts/` |
| 验收 | 跑全套测试 + 启动 app 让 andy 复测 + 出第二波 spec | — |

---

## 明天恢复执行的方法

1. 打开本仓库，确认 HEAD 是 `c4e7013`：
   ```powershell
   git log -1 --oneline
   ```

2. 让 Claude 继续：
   > "继续执行第一波 UI 修复，从 Task 3 开始。Plan 在 `doc/superpowers/plans/2026-06-05-frontend-ui-fix-wave1.md`，已完成 Task 1、Task 2（HEAD = `c4e7013`），现在做 Task 3。"

3. Claude 应自动按 subagent-driven-development 流程派遣 implementer → spec reviewer → code quality reviewer 走完 Task 3、Task 4 + 验收。

---

## 已知的 pre-existing 问题（不归本次修复）

以下问题在第一波修复开始前就已经存在，**不属于本次任务范围**，但日后值得清理：

- `app/ui/components/collapsible_group.py:117` — mypy --strict 报错
- `app/tests/ui/test_assets.py` — 导入错误
- 若干 UI 测试失败（`_status_lines` 属性名错配、opacity 逻辑、emoji 字体相关）

---

## 第二波待修 bug（验收后再开 spec）

- 底部导航栏只显示 1 个 tab（3 张测试截图都有）
- `PixelNumberDialog` 确认按钮溢出窗口
- 输入框点开后无法接收输入 / 不弹 Windows IME

详见 `doc/superpowers/specs/2026-06-05-frontend-ui-fix-design.md` 的第 2 节。
