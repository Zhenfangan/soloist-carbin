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

```python
class IconLabel(BoxLayout):
    """图标 + 文字的组合行 — emoji 的像素图标替代品。

    水平排列: 小图标 Image(nearest 过滤) + Label。
    """

    def __init__(self, icon: str | None = None, text: str = "",
                 font_size: int = FONT_SIZE_BODY,
                 color: tuple = ..., icon_size: int = 18, **kwargs) -> None:
        ...

    def set_status(self, icon: str | None, text: str) -> None:
        """动态更新图标 + 文字(替换现有 `label.text = f"{emj(...)} ..."` 的写法)。"""
```

- `icon=None` 时不显示图标（保留纯文字场景，如无状态占位符）
- 内部图标 `Image` 走 `IconLoader.get_icon_path()` + `apply_pixel_filter`，与现有图标风格统一
- `icon_size` 默认 18px（明显小于 32px 原图，行内文字大小的图标；32×32 源图缩小显示，`allow_stretch=True` + nearest 过滤保持锐利）

### 4.2 一行多图标场景（两处，具体处理方式钉死如下）

- `period_card.py:427`（`⏰迟到🏃早退`）：横向 `BoxLayout` 内放两个 `IconLabel` 并排 —— `IconLabel(icon='icon_clock', text='迟到')` + `IconLabel(icon='icon_run', text='早退')`。
- `checkin_screen.py:332`（`🔥 已连续正常出勤 N 天 🔥`，首尾各一个相同图标）：横向 `BoxLayout` 内放 `IconLoader.get_icon('icon_flame')`（裸 Image，不经 `IconLabel`）+ `IconLabel(icon='icon_flame', text=f'已连续正常出勤 {streak} 天')` —— 首图标用裸 `Image`，尾图标随文字一起交给 `IconLabel`，不新建专门的多图标组件。

### 4.3 `fonts.py` 清理

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
