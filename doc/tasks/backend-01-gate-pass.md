# backend-01-gate-pass: 自动化门禁走查

## 职责

验证单一方法和静态类型在封闭环境下的完备性。在 0% UI 介入的前提下，通过 pytest / mypy / ruff 三道门禁，确保核心 Service 层与 Repo 层零类型错误、零逻辑回归。

## 环境前提

- 工作目录: `D:\my-project\soloist-carbin`
- Python 3.12 + 虚拟环境已激活
- 项目根目录下存在 `pytest.ini`、`mypy.ini`

---

## G-1: 全量后端单元测试

### 命令

```bash
cd D:\my-project\soloist-carbin
PYTHONPATH=. python -m pytest app/tests/ --ignore=app/tests/ui -v --tb=short
```

### 检查项

- [ ] 全部测试通过，无 FAILED
- [ ] 通过数 ≥ 130（当前基线约 365 collected，排除 UI 后约 150+)
- [ ] 无 ERROR 收集错误（UI 目录已被 `--ignore=app/tests/ui` 排除）

### 容错说明

若个别测试因数据库残留状态失败（非本次修改引入），记录文件名与失败原因，标记为已知问题，不阻断门禁通过。

### 期望输出截断示例

```
===================== 152 passed in 2.34s =====================
```

---

## G-2: mypy 强类型检查

### 目标范围

仅检查 `app/services/` 与 `app/repositories/` 目录。UI 层 (`app/ui/`) 和第三方库 (`kivy.*`) 已在 `mypy.ini` 中排除或忽略。

### 命令

```bash
cd D:\my-project\soloist-carbin
python -m mypy app/services/ app/repositories/ --strict --show-error-codes
```

### 检查项

- [ ] `app/services/` 零类型错误
- [ ] `app/repositories/` 零类型错误
- [ ] 无 `error:` 级别输出

### 期望输出

```
Success: no issues found in 12 source files
```

### 处置预案

若报 `[attr-defined]` 或 `[union-attr]`，逐行修复后重新运行，直到清零。

---

## G-3: Ruff 代码规范自查

### 命令

```bash
cd D:\my-project\soloist-carbin
ruff check app/services/ app/repositories/
```

### 检查项

- [ ] 无 `E` 级错误（Syntax/IO）
- [ ] 无 `F` 级错误（Pyflakes，如未使用导入、未定义变量）
- [ ] `W` 级警告可记录但不断门禁

---

## G-4: 针对性 Service 回归（快速冒烟）

在完整 pytest 之后，补充一组快速冒烟确保核心入口未退化：

```bash
cd D:\my-project\soloist-carbin
PYTHONPATH=. python -m pytest app/tests/test_checkin_service.py app/tests/test_settings_service.py app/tests/test_bet_service.py -v --tb=short
```

### 检查项

- [ ] `test_checkin_service.py` 全部通过（当前基线 27 passed）
- [ ] `test_settings_service.py` 全部通过
- [ ] `test_bet_service.py` 全部通过

---

## 交付标准

| 门禁 | 命令 | 合格线 |
|------|------|--------|
| pytest | `pytest app/tests/ --ignore=app/tests/ui` | ≥130 passed, 0 failed |
| mypy | `mypy app/services/ app/repositories/ --strict` | 0 errors |
| ruff | `ruff check app/services/ app/repositories/` | 0 E, 0 F |
| 冒烟 | `pytest app/tests/test_{checkin,settings,bet}_service.py` | 全绿 |

三项全部达标后，视为 Stage-1 Gate Pass，方可进入 Stage-2 生命周期测试。
