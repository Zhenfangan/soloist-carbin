# UI 渲染问题诊断报告

> 测试截图：`doc/ui-design/testphoto/1.png` ~ `4.png`
> 截图方式：微信截图，手动切换四个页面后截取
> 页面对应：1=打卡页 2=历史页 3=对赌页 4=设置页

---

## 1. 总体诊断结论

| 图片 | 页面 | 严重程度 | 根本原因 | 类型 |
|------|------|---------|---------|------|
| 1.png | 打卡页 | 轻微 | 整体偏灰，缺少 BG_CREAM 底色 | **代码问题** |
| 2.png | 历史页 | 轻微 | 整体偏灰，缺少 BG_CREAM 底色 | **代码问题** |
| 3.png | 对赌页 | 严重 | 背景大面积灰色（Kivy ScrollView 默认色），组件间空洞大 | **代码问题** |
| 4.png | 设置页 | 致命 | 99.7% 纯黑，仅标题 12px 文字可见，其余内容完全不显示 | **代码问题** |

**全部为代码问题，非测试问题。** 测试通过了是因为：
- 测试只验证 widget 属性和回调，不验证视觉渲染
- conftest.py 设置 `offscreen` 模式 → 无真实渲染
- 现有测试覆盖的是逻辑正确性，不是 UI 可见性

---

## 2. 逐图问题分析

### 2.1 Image 1 — 打卡页（CheckinScreen）

**像素统计：**
| 颜色 | 占比 | 来源 |
|------|------|------|
| #FFFFFF (白) | 64.2% | PeriodCard/StatusBox 卡片背景 |
| #000000 (黑) | 24.5% | 文字内容 |
| #FFE030 (明黄) | 6.9% | 按钮、当前时段 |
| #30C090 (薄荷绿) | 0.4% | 完成状态标识 |
| #F0E8D0 (卡片阴影) | 0.9% | 像素边框暗面 |

**问题：整体缺少 BG_CREAM (#FFF8E8) 暖色底色。**
- PeriodCard、StatusBox、TaskInlineList 各自绘制 CARD_WHITE 背景 → 所以页面看起来是白色而非奶油色
- 卡片之间的间隙区域暴露了底层 Kivy 默认灰色背景
- 不致命，但视觉上不如设计预期的暖色调

### 2.2 Image 2 — 历史页（HistoryScreen）

**像素统计：**
| 颜色 | 占比 | 来源 |
|------|------|------|
| #FFFFFF (白) | 66.4% | DayCard 卡片背景 |
| #000000 (黑) | 22.0% | 文字 |
| #3A3028 (棕) | 4.0% | TEXT_BROWN 标签文字 |
| #FFE030 (明黄) | 3.0% | HistoryTabs/Tab 激活态 |

**问题：与 Image 1 相同，缺少 BG_CREAM 底色。** DayCard 组件有自己的白色背景，所以内容区基本正常。

### 2.3 Image 3 — 对赌页（BetScreen）

**像素统计：**
| 颜色 | 占比 | 来源 |
|------|------|------|
| #000000 (黑) | 69.6% | 大量空白区域 |
| #FFFFFF (白) | 13.2% | WeekSummaryHeader 头部区域 |
| #787468 (灰褐) | 8.7% | 接近 TEXT_GRAY |
| #F0E8D0 (卡片阴影) | 6.9% | BetConfigSection 卡片边框 |
| #FFE030 (明黄) | 0% (仅28px) | **几乎无黄色元素！** |

**空间分布（逐行扫描）：**
- y=35~130：**有白色内容** — WeekSummaryHeader 正常渲染（含薄荷绿完成色、黄褐色高亮）
- y=135~245：**纯灰色** — Kivy ScrollView 默认灰色背景，任务列表为空导致大片空白
- y=255~295：**CARD_SHADOW 卡片出现** — BetConfigSection 的像素边框渲染，内部有 TEXT_BROWN 文字
- y=305~690：**纯灰色** — 按钮等组件之间的间隙暴露灰色背景

**根本原因（三重）：**
1. **test_launcher.py 无全局 BG_CREAM 背景** → Kivy ScrollView 默认灰色（#9DA19D）暴露
2. **任务列表为空** → task_container 高度为 0，灰色区域扩大
3. **BetScreen._layout 的子组件间 spacing** → 间隙暴露底层灰色

### 2.4 Image 4 — 设置页（SettingsScreen）⚠️ 致命

**像素统计：**
| 颜色 | 占比 | 来源 |
|------|------|------|
| #000000 (纯黑) | 99.7% | 无任何渲染内容 |
| #3A3028 (TEXT_BROWN) | <0.01% | 仅 "设置" 标题两行共 24 像素 |
| #120F0D (近黑) | 0.1% | 屏幕噪声 |

**内容扫描：整个内容区（y=35~722）只有：**
- y=56：TEXT_BROWN 文字 **12 像素** — "设置" 标题
- y=68：TEXT_BROWN 文字 **12 像素** — 第一个 CollapsibleGroup 标题
- **其余所有行：纯黑 (0,0,0)**
- 所有 "bright" 像素均在 x=0 位置 → 窗口边框，不是内容

**根本原因（四重）：**

1. **SettingsScreen 本身是 BoxLayout，无背景** → 默认透明黑色
   
2. **CollapsibleGroup 组件不绘制自身背景**
   - `CollapsibleGroup.__init__`：无 `canvas.before`，无 `_redraw` 方法
   - 头部和内容区都是透明子组件
   - 依赖父级提供背景 → 父级是黑色 BoxLayout → 结果黑色

3. **test_launcher.py 无 BG_CREAM 全局背景**
   - `main.py:74-77` 有 `Color(*_to_rgba(BG_CREAM))` + `Rectangle`
   - `test_launcher.py` 完全没有这段代码
   
4. **CollapsibleGroup 内部 content BoxLayout 的 minimum_height 为 0**
   - `_make_vbox()` 创建的 BoxLayout 使用 `bind(minimum_height=box.setter("height"))`
   - 但在添加到窗口前 `do_layout()` 未执行，`minimum_height` 保持为 0
   - 导致 CollapsibleGroup 的 `_content_box.height = 0`（折叠态默认）
   - 展开时 content.height = 100（Widget 默认值），但子组件实际不占空间

**视觉结果：** 整个页面只有标题栏和底部导航栏可见，内容区纯黑。仅 "设置" 两个字的 24 像素渲染在黑色背景上（极难看到）。

---

## 3. 根本原因汇总

### P0 — 致命：test_launcher.py 缺少全局背景

```python
# main.py（正确）
self._root = FloatLayout()
with self._root.canvas.before:
    Color(*_to_rgba(BG_CREAM))           # ← 奶油色背景
    self._bg_rect = Rectangle(...)

# test_launcher.py（缺少）
root = BoxLayout(orientation="vertical")
# ← 没有任何背景设置！默认黑色/透明
```

**修复：** 在 `test_launcher.py` 的 `build()` 方法中为 `root` 添加 BG_CREAM 背景 canvas。

### P0 — 致命：CollapsibleGroup 缺少背景渲染

```python
# app/ui/components/collapsible_group.py
class CollapsibleGroup(FloatLayout):
    def __init__(self, ...):
        # ← 没有 canvas.before
        # ← 没有 _redraw 方法
        # ← 没有绑定 pos/size 触发重绘
```

**修复：** 为 CollapsibleGroup 添加像素边框 + CARD_WHITE 背景的 `_redraw` 方法，绑定到 `pos` 和 `size`。

### P1 — 严重：BetScreen / SettingsScreen 的内容区高度计算

`_make_vbox()` 返回的 BoxLayout 使用 `minimum_height` 绑定，但 `minimum_height` 在未加入窗口前保持为 0。需要显式设置初始高度或者改用 `size_hint` 方式。

### P2 — 一般：字体回退问题

`get_available_font_name()` 优先返回 `press-start-2p`（仅拉丁字符），中文需依赖 Roboto 回退。`apply_global_font()` 调用 `LabelBase.default_font_name = pixel_font` 和 `Config.set("kivy", "default_font", [...])`，但 `Config.set` 在 `build()` 内部调用时可能已过晚（Kivy 文本提供者在 `App.run()` 时就已初始化）。

---

## 4. 修复方案

### 修复 1：test_launcher.py 添加全局背景

**文件：** `app/test_launcher.py`
**修改：** 在 `build()` 方法的 root 创建后，添加 canvas.before 绘制 BG_CREAM

### 修复 2：CollapsibleGroup 添加背景渲染

**文件：** `app/ui/components/collapsible_group.py`
**修改：** 添加 `_redraw` 方法绘制 CARD_WHITE 背景 + 像素凸起边框 + 阴影

### 修复 3：SettingsScreen/BetScreen 自身添加背景

**文件：** `app/ui/screens/settings_screen.py`、`app/ui/screens/bet_screen.py`
**修改：** 在 ScrollView 或根布局的 canvas.before 中添加 CARD_WHITE/BG_CREAM 背景

### 修复 4：全局默认字体改为 silkscreen（支持中文）

**文件：** `app/ui/fonts.py`
**修改：** `get_available_font_name()` 优先返回 `silkscreen`（支持中文）而不是 `press-start-2p`

---

## 5. 已应用的修复（2026-06-02）

| 修复 | 文件 | 变更 |
|------|------|------|
| P0-1 | `app/test_launcher.py` | 根 BoxLayout 添加 BG_CREAM canvas.before 背景 + `_update_bg` 回调 |
| P0-2 | `app/ui/components/collapsible_group.py` | 添加 `_redraw()` 方法：绘制 CARD_WHITE 背景 + 凸起像素边框 + 阴影，绑定 pos/size |
| P0-3 | `app/ui/screens/settings_screen.py` | content BoxLayout 添加 CARD_WHITE 背景 canvas + `_update_content_bg` |
| P1 | `app/ui/screens/bet_screen.py` | `_layout` BoxLayout 添加 CARD_WHITE 背景 canvas + `_update_layout_bg` |
| P2 | `app/ui/fonts.py` | `get_available_font_name()` 优先 silkscreen（支持中文）；`apply_global_font()` 构建完整回退链 |

## 6. 已添加的测试改进

| 测试 | 文件 | 内容 |
|------|------|------|
| 组件背景验证 | `app/tests/ui/test_visual.py` | 14 个测试，验证每个核心组件（PixelButton、PeriodCard、CollapsibleGroup 等）创建后 canvas.before 非空 |
| 页面布局验证 | 同上 | 验证 SettingsScreen._content_bg_rect 和 BetScreen._layout_bg 存在 |

## 7. 测试结果

- **379 测试全部通过** (120 后端 + 259 UI)
- **mypy strict: 0 errors**
- **ruff: 0 errors**
