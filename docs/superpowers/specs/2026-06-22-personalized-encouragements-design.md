# 个性化激励语句 — 设计文档

> 创建日期：2026-06-22
> 状态：待用户复核

## 1. 背景与目标

战报（日报 / 拍摄日报）末尾的"鼓励语"目前从硬编码 5 句的 `ENCOURAGEMENTS` 列表中随机抽取。代码已留扩展点（`report_service.py:_pick_encouragement` 注释明确写着"未来从用户自定义语录库随机抽取，合并 ENCOURAGEMENTS 作兜底；此处签名保持稳定"）。

本设计为用户提供"个性化激励语句"的设置入口，让用户可以增/删自己的鼓励语，战报里出现的鼓励语将从用户语录中随机抽取。

## 2. 关键设计决策

| 决策点 | 选择 |
| --- | --- |
| 用户清空所有自定义语录时 | 回落到内置 5 句 `ENCOURAGEMENTS` |
| 用户有自定义语录时的随机池 | **只从用户语录中随机**，内置 5 句完全不参与 |
| 设置页的交互形式 | 在折叠分组内直接管理（与"推送通知"分组同风格） |
| 存储方式 | 复用 `settings` 表，单 key + JSON 数组字符串 |

## 3. 数据层

新增 settings key：

```
encouragements_user (TEXT, 默认 "[]")
```

- 在 `SettingsService.DEFAULTS` 中加一行：`"encouragements_user": "[]"`
- 不新建 repository，不新建表，不做数据库迁移

## 4. 服务层

### 4.1 SettingsService 新增两个 helper

```python
def get_user_encouragements(self) -> list[str]:
    """读取用户自定义语录列表；JSON 解析失败时返回空列表"""

def set_user_encouragements(self, items: list[str]) -> None:
    """写入用户自定义语录列表（JSON 编码后存入 settings 表），发布 SETTINGS_CHANGED 事件"""
```

实现要点：
- `get_user_encouragements`：`json.loads(self.get("encouragements_user"))`，捕获 `json.JSONDecodeError` 与类型异常 → 返回 `[]`，并 Logger.warning
- `set_user_encouragements`：`self.set("encouragements_user", json.dumps(items, ensure_ascii=False))`，借用现有 `set()` 自动发布 `SETTINGS_CHANGED`

### 4.2 ReportService 改造接入点

`app/services/report_service.py:_pick_encouragement` 修改为：

```python
def _pick_encouragement(self, date: str) -> str:  # noqa: ARG002
    user_items = self._read_user_encouragements()
    pool = user_items if user_items else ENCOURAGEMENTS
    return random.choice(pool)

def _read_user_encouragements(self) -> list[str]:
    """从 settings_repo 读 encouragements_user 并 JSON 解析；失败返回空"""
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

注意：`ReportService` 已经持有 `settings_repo`（见现有构造函数），无需新增依赖注入。直接调 `settings_repo.get(...)` 即可，不引入 `SettingsService` 依赖，保持现有耦合层级。

## 5. UI 层

### 5.1 SettingsScreen 新增折叠分组

在 `app/ui/screens/settings_screen.py` 的 `__init__` 末尾，"推送通知组" 之后，新增第 6 个分组：

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

### 5.2 _build_encouragement_group() 结构

```
┌─ CollapsibleGroup「个性化激励语句」(折叠) ──────────────┐
│  ┌─ 输入行 (BoxLayout, h=48) ─────────────────────────┐ │
│  │ [PixelInput hint="添加一条激励语句…"      ] [添加] │ │
│  └────────────────────────────────────────────────────┘ │
│  ┌─ 列表容器 (BoxLayout vertical, size_hint_y=None) ──┐ │
│  │  (空时显示一行说明 Label)                          │ │
│  │  ─── 否则每条一行 ───                              │ │
│  │  [Label("……自动换行的语录文本……")        ] [×]   │ │
│  │  [Label("……")                            ] [×]   │ │
│  │  …                                                  │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

- 顶部输入行（高度 48）：
  - `PixelInput`（`size_hint=(1, 1)`，`hint_text="添加一条激励语句…"`）
  - `PixelButton("添加", size_mode="small", width=70, color=MINT_GREEN)`
- 列表容器：垂直 `BoxLayout`，每条目高度 48（文本若超长，行高自适应增长到最多两行 96px）
- 空状态：列表容器只放一行灰色 `Label("尚未添加，战报将随机使用内置 5 句")`

### 5.3 交互行为

- **添加**：
  1. 取 `PixelInput.text.strip()`
  2. 空字符串 → toast "请输入内容"，不入库
  3. 长度 > 100 字符 → toast "单条不能超过 100 字"，不入库
  4. 已存在相同字符串 → toast "已存在相同语录"，不入库
  5. 成功 → `settings_service.set_user_encouragements(current + [new])` → 清空输入框 → 重建列表 UI
- **删除**：点 X → 直接从列表移除 → `settings_service.set_user_encouragements(new_list)` → 重建列表 UI
- **重建列表 UI**：`_refresh_encouragement_list()` 方法，清空列表容器子组件后按当前数据重新 `add_widget`

### 5.4 不做（YAGNI）

- 不做"恢复 / 导入内置语录"按钮（用户清空时自动回落已足够）
- 不做排序 / 拖动重排
- 不做编辑（要改就删了重加）
- 不做导入 / 导出
- 不做长度硬上限（100 字符仅是 UI 层友好提示，存储不强制）

## 6. 数据流

```
用户在输入框敲字 → 点「添加」
   ↓
SettingsScreen._on_encouragement_add()
   ↓
SettingsService.set_user_encouragements(list[str])
   ↓
SettingsRepo.set("encouragements_user", json_string)  → SETTINGS_CHANGED 发布
   ↓
SettingsScreen._refresh_encouragement_list()  (直接刷新 UI，不依赖事件)
```

```
战报生成
   ↓
ReportService.collect_data(date)
   ↓
self._pick_encouragement(date)
   ↓
settings_repo.get("encouragements_user")  → JSON.decode → list
   ↓
random.choice(user_list 或 ENCOURAGEMENTS)
   ↓
ReportData.encouragement
```

## 7. 错误处理

| 场景 | 行为 |
| --- | --- |
| JSON 字段损坏（手动改坏 settings 表） | 当作空列表，使用内置兜底，`Logger.warning("encouragements_user JSON decode failed: %s", raw)` |
| `settings_repo.get` 抛异常 | 让其冒泡到上层（与现有 `_get_setting` 行为一致） |
| UI 点添加时 `set` 抛异常 | toast "保存失败，请重试"，列表 UI 不动 |
| JSON 数组里混进非 string 元素 | `_read_user_encouragements` 在过滤阶段剔除 |

## 8. 同步 / 备份

**无需任何改动。** 现有 `SyncService.backup_full() / restore_full()` 整张读写 settings 表，新加的 `encouragements_user` key 自动随同步链路走。

## 9. 测试

### 9.1 服务层单元测试（`app/tests/test_settings_service.py`，新增 4 项）

- `test_user_encouragements_default_empty` — 全新 SettingsService 调 `get_user_encouragements()` 返回 `[]`
- `test_user_encouragements_set_and_get_roundtrip` — `set(["a","b"])` → `get()` 返回 `["a","b"]`
- `test_user_encouragements_handles_corrupted_json` — 直接通过 `settings_repo.set("encouragements_user", "not json")` 写入坏值，`get_user_encouragements()` 返回 `[]`
- `test_user_encouragements_set_publishes_event` — 订阅 `SETTINGS_CHANGED`，调用 `set_user_encouragements(...)` 后事件被发布

### 9.2 战报层单元测试（`app/tests/test_report_service.py`，新增 2 项）

- `test_encouragement_picks_from_user_list_when_present` — 通过 `settings_repo.set("encouragements_user", '["custom only"]')` 注入，调 100 次 `_pick_encouragement`，全部应等于 `"custom only"`
- `test_encouragement_falls_back_to_builtin_when_user_empty` — 默认状态下抽 100 次，结果集应是 `ENCOURAGEMENTS` 的子集

### 9.3 UI 人工验证

启动 app → 设置页 → "个性化激励语句" 折叠组 → 添加 3 条 → 删 1 条 → 触发当日战报 → 鼓励语应在剩下 2 条里随机；清空所有自定义条目 → 鼓励语应在内置 5 句里随机。

## 10. 变更清单

| 文件 | 变更 | 行数估算 |
| --- | --- | --- |
| `app/services/settings_service.py` | DEFAULTS 加一行；新增 2 个 helper + `import json` | +25 |
| `app/services/report_service.py` | `_pick_encouragement` 重写；新增 `_read_user_encouragements` + `import json` | +25 |
| `app/ui/screens/settings_screen.py` | 新增 group6 注册 + `_build_encouragement_group` + `_refresh_encouragement_list` + `_on_encouragement_add` + `_on_encouragement_delete` | +130 |
| `app/tests/test_settings_service.py` | 新增 4 个测试 | +50 |
| `app/tests/test_report_service.py` | 新增 2 个测试 | +30 |

合计约 260 行净增，触达 5 个文件，无 DB 迁移。

## 11. 实现顺序（供 writing-plans 参考）

1. SettingsService 改造 + 单元测试 → 绿
2. ReportService 接入点改造 + 单元测试 → 绿
3. SettingsScreen UI 折叠分组 + 列表/输入/删除交互
4. UI 人工冒烟（启动 app 添加/删除/触发战报）
5. 提交
