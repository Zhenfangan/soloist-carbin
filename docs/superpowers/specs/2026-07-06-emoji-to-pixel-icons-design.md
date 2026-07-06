# Emoji 替换为像素图标 — 设计文档

> 创建日期：2026-07-06
> 状态：待用户复核

## 1. 背景与目标

App 用 `app/ui/fonts.py:emj()` 把 emoji 包成 `[font=emoji]...[/font]` markup，依赖 Windows 的 Segoe UI Emoji 字体渲染。这在桌面开发环境好使，但真机（华为 HBN-AL80）不带这个字体，所有 emoji 全部显示成方块「点」。

真机唯一能画彩色 emoji 的字体是 Android 系统自带的 NotoColorEmoji，但 `fonts.py` 里的历史注释记录了明确的踩坑：加载它会导致 Kivy 的 SDL2_ttf/FreeType 渲染管线与其 CBDT/CBLC 彩色位图字形表不兼容，真机启动即 `Fatal signal 11 SIGSEGV` 崩溃循环，已回退且明确不能重新加入。

本设计放弃"用字体画 emoji"这条路，改为 App 自有的像素风图标（复用 `IconLoader` 既有加载机制），从根上不依赖任何系统 emoji 字体，真机不会再显示成点，也不存在字体兼容性崩溃风险。

## 2. 关键设计决策

| 决策点 | 选择 |
| --- | --- |
| emoji 渲染方式 | 弃用系统 emoji 字体，改为项目自有像素图标（32×32 PNG，复用 `IconLoader`） |
| 图文组合方式 | Kivy markup Label 不支持行内图片标签（已查证 `kivy.core.text.markup` 只有 `[b]/[color]/[font]/[ref]` 等纯文字标签），故新增 `IconLabel` 组合组件（Image + Label 横向排列） |
| 一行多图标（`🔥…🔥`、`⏰迟到🏃早退`） | 用两个 `IconLabel` 并排放同一横向行内，复用同一组件，不新建专门类 |
| 已有图标复用 | ✅→`check_mark.png`、🚨→`warning.png`、➕→`btn_add.png`（已核实三者语义/外观均可直接复用） |
| 新图标取色 | 复用 `tokens.py` 既有的 `SEMANTIC_COLORS`/`DOPAMINE_COLORS`，不发明新色值 |
| 新图标画法 | 沿用现有 `check_mark.png`/`warning.png` 的风格：32×32、小格子(16×16)绘制关键形状后最近邻放大 2×，黑色描边 `#1A140F` + 纯色填充，PIL 脚本生成（非外部素材） |
| `emj()` / `fonts.py` 里 emoji 字体注册 | 全部删除（连同 `_EMOJI_FONT_CANDIDATES`、`emoji` 字体注册逻辑），彻底不再依赖任何 emoji 字体 |

## 3. 图标清单

App 内实际用到 15 个不同 emoji（已用 `grep -o` 全量核实，非估算）：

| emoji | 语义 | 处理方式 | 新图标名 | 取色 |
| --- | --- | --- | --- | --- |
| ✅ | 完成/正常 | 复用现有 | `check_mark` | — |
| 🚨 | 旷工 | 复用现有 | `warning` | — |
| ➕ | 添加任务 | 复用现有 | `btn_add` | — |
| ✍️ | 签到/待签到 | 新画 | `icon_pen` | normal 蓝 `#1E70A8` |
| 🛌 | 请假 | 新画 | `icon_bed` | leave 紫 `#B090F0` |
| 🌙 | 签退时间标记 | 新画 | `icon_moon` | 中性灰蓝 `#8A9AB0`（装饰性，非状态色） |
| ⏰ | 迟到 | 新画（已有样品） | `icon_clock` | late 粉 `#FF6B8A` |
| 🏃 | 早退 | 新画 | `icon_run` | early_leave 橙 `#FF9040` |
| 📸 | 拍摄中 | 新画 | `icon_camera` | shooting 橙 `#FF9040` |
| 🎯 | 今日目标 | 新画 | `icon_target` | 主黄 `#FFE030` |
| 📅 | 日期 | 新画 | `icon_calendar` | sky 浅蓝 `#60C8FF` |
| 🔥 | 连续天数 | 新画（已有样品） | `icon_flame` | warm_orange `#FF9040` |
| 📊 | 今日状态 | 新画 | `icon_chart` | sky 浅蓝 `#60C8FF` |
| ⏳ | 等待签到 | 新画 | `icon_hourglass` | 中性灰 `#8A8078`（`TEXT_GRAY`） |
| 📝 | 今日任务 | 新画 | `icon_memo` | sky 浅蓝 `#60C8FF` |

样品 `sample_streak_flame.png` / `sample_late_clock.png`（已在 brainstorming 阶段生成于 `app/ui/assets/icons/`，供质量审阅）将在实施时改名为正式的 `icon_flame.png` / `icon_clock.png` 并重新生成（样品文件本身不注册进 `ICON_FILES`，是临时产物）。

## 4. 组件架构

### 4.1 新增 `IconLabel`（`app/ui/components/icon_label.py`）

> **实施阶段修正**（原设计假设只有"单图标"和"两处硬编码双图标"两种情况；实际读完
> `period_card.py:_update_display` 完整上下文后发现 `_summary_label`/`_check_label`
> 是**运行时 0~2 个动态片段拼接**，不是固定写死的两种。改为通用"片段列表"API，
> 一个组件覆盖单图标/双同图标/双异图标/变长拼接所有情况，不再需要一次性拼装代码）：

```python
class IconLabel(BoxLayout):
    """图标 + 文字的组合行 — emoji 的像素图标替代品。

    水平排列一组 (icon_name|None, text) 片段, 每段是 图标 Image(nearest 过滤) + Label。
    """

    def __init__(self, icon: str | None = None, text: str = "",
                 font_size: int = FONT_SIZE_BODY,
                 color: tuple = ..., icon_size: int = 18, **kwargs) -> None:
        """单段构造糖: icon=None 时该段不显示图标。"""

    def set_status(self, icon: str | None, text: str) -> None:
        """单段动态更新 — 43/45 调用点的常见情况, 等价于 set_segments([(icon, text)])。"""

    def set_segments(self, segments: list[tuple[str | None, str]]) -> None:
        """N 段动态更新(清空重建子 widget) — 覆盖 0/1/2+ 段场景:
        - `_summary_label`(完成态摘要): 0~2 段, 如 [('icon_pen','09:05'), ('icon_moon','18:30')]
        - `_check_label`(迟到/早退徽章): 1~2 段, 如 [('icon_clock','迟到'), ('icon_run','早退')]
        - `_streak_label`(连续天数): 首尾同图标, 如 [('icon_flame',''), (None,'已连续出勤N天'), ('icon_flame','')]
        """
```

- 内部图标 `Image` 走 `IconLoader.get_icon_path()` + `apply_pixel_filter`，与现有图标风格统一
- `icon_size` 默认 18px（明显小于 32px 原图，行内文字大小的图标；32×32 源图缩小显示，`allow_stretch=True` + nearest 过滤保持锐利）

### 4.2 `PixelButton` 场景不加图标（实施阶段发现，范围修正）

`period_card.py:_action_btn`/`_leave_btn` 的 emoji 实际嵌在 `PixelButton`（`app/ui/components/pixel_button.py`）里，不是 `Label`。`PixelButton` 继承 Kivy `Button`，文字靠内置 Label 混入渲染、背景靠 `canvas.before` 手工画 3D 凸起边框 —— 不是能随意塞入子 widget 的容器，若要加图标得改造 `PixelButton` 内部渲染管线，风险/收益不成正比（按钮本身已靠颜色+形状+按压态传达状态，图标不是必需信息）。

**处理方式：这 5 处（构造 2 处 + 动态更新 3 处）只去掉 `emj()` 调用，保留纯中文文字，不引入图标**，即 `f"{emj('✍️')} 签到"` → `"签到"`。

### 4.3 顺带清理：`period_card.py:_get_status_text()` 死代码

审计确认 `_get_status_text()`（含其 `status_map` 字典）在全代码库**零调用点**，属历史遗留死代码。随本次改动一并删除，不做转换。

### 4.4 `fonts.py` 清理

删除：
- `_EMOJI_FONT_CANDIDATES` 列表
- `apply_global_font()` 中的 emoji 字体注册循环
- `emj()` 函数本身（连同其调用点，见下）

## 5. 落地范围

| 文件 | 改动 |
| --- | --- |
| `app/ui/assets/icons/*.png` | 新增 12 个图标（PIL 脚本生成，32×32，风格同现有图标） |
| `app/ui/assets/loader.py` | `ICON_FILES` 新增 12 项 |
| `app/ui/components/icon_label.py` | **新组件** `IconLabel` |
| `app/ui/components/period_card.py` | 20 处 `emj()` 调用 → `IconLabel`/`set_status`（含 1 处双图标行） |
| `app/ui/components/status_box.py` | 16 处 |
| `app/ui/screens/checkin_screen.py` | 6 处（含 1 处双图标行） |
| `app/ui/components/task_inline_list.py` | 2 处 |
| `app/ui/fonts.py` | 删除 `emj()` 与 emoji 字体注册逻辑 |
| `app/tests/ui/test_assets.py` | `ICON_FILES` 数量断言 24→36 |
| `app/tests/ui/test_icon_label.py` | **新测试** `IconLabel` 单测(TDD) |

## 6. 测试与验证

- TDD 为 `IconLabel` 写单测：图标+文字构造、`icon=None` 场景、`set_status` 动态更新、图标 nearest 过滤生效
- 逐文件替换后跑受影响测试，确认无回归
- 全量回归（基线 621 passed）
- 桌面渲染自检：`export_to_png` 对比新图标显示效果
- 真机装机验证：不再显示方块点，图标清晰可辨；重点回归此前刚修复的月历/休息日/像素图清晰度功能不受影响

## 7. 明确不做的事

- 不做通用的"emoji→图标"自动转换框架，只精确覆盖这 15 个已知 emoji
- 不追求图标的精细写实，风格与现有 `check_mark`/`warning` 一致的简笔画像素风
- 不改动 `report_preview.py` 战报里的品牌小猫图标等既有像素图（那部分已在上一轮 nearest 过滤修复中完成，与本次无关）
