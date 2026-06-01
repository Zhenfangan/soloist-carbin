# UI-01 — 设计令牌 + 基础组件

> 职责：全局设计常量 + 所有复用基础组件，后续页面消费这些即可
> 依赖：无

---

## 设计令牌

- [ ] **1.1** 创建 `app/ui/tokens.py`：定义主色板常量（`PRIMARY_YELLOW=#FFE030`、`PRIMARY_DARK=#E0A800`、`BG_CREAM=#FFF8E8`、`CARD_WHITE=#FFFFFF`、`CARD_SHADOW=#F0E8D0`、`TEXT_BROWN=#3A3028`、`TEXT_GRAY=#8A8078`、`SHADOW_BLACK=#000000`）
- [ ] **1.2** 在 `app/ui/tokens.py`：定义多巴胺辅色常量（珊瑚粉亮/暗、薄荷绿亮/暗、薰衣草亮/暗、天空蓝亮/暗、暖橙亮/暗、西瓜红亮/暗，共 12 个色值）
- [ ] **1.3** 在 `app/ui/tokens.py`：定义功能语义色常量（正常/迟到/早退/旷工/请假/拍摄日/已完成，每项含色块色、边框色、图标色三个字段）
- [ ] **1.4** 在 `app/ui/tokens.py`：定义网格常量（`GRID=8`、`BORDER_WIDTH=2`、`BTN_HEIGHT=48`、`CARD_PADDING=16`、`NAV_HEIGHT=56`、`ICON_SIZE=32`、`SPRITE_SIZE=64`）
- [ ] **1.5** 在 `app/ui/tokens.py`：定义像素字体常量（`FONT_PIXEL="press-start-2p"`、`FONT_HANZI_PIXEL="silkscreen"`、`FONT_SIZE_TITLE=18`、`FONT_SIZE_BODY=14`、`FONT_SIZE_SMALL=10`），含字体文件路径映射
- [ ] **1.6** 在 `app/ui/tokens.py`：定义像素阴影常量（`SHADOW_OFFSET=2`、`SHADOW_COLOR=#000000`、亮面偏移/暗面偏移），供组件引用

## 基础组件

- [ ] **1.7** 创建 `app/ui/components/pixel_button.py`：`PixelButton` 类 — 2px 亮面+暗面伪 3D 边框，按下时明暗交换（凹陷效果），支持 `text`/`color`/`on_press`/`disabled` 属性，最小高度 48px，字体用像素字体
- [ ] **1.8** 在 `pixel_button.py`：实现按钮尺寸变体 — `normal`（48px 高）/ `large`（64px 高，用于主打卡按钮）/ `small`（36px 高，用于辅助操作）
- [ ] **1.9** 创建 `app/ui/components/pixel_input.py`：`PixelInput` 类 — 内凹样式（暗面在顶部+左侧），2px 边框，直角，像素字体，支持 `hint_text`/`value`/`password`/`on_change`
- [ ] **1.10** 创建 `app/ui/components/pixel_dialog.py`：`ConfirmDialog` 类 — 通用像素边框弹窗，含标题、正文、确认/取消两个 `PixelButton`，背景半透明黑遮罩
- [ ] **1.11** 创建 `app/ui/components/collapsible_group.py`：`CollapsibleGroup` 类 — 像素三角箭头（▶ 折叠 / ▼ 展开），标题栏 + 可折叠内容区，阶梯式展开动画（200ms，每 8px 一步）
- [ ] **1.12** 创建 `app/ui/components/mascot_bubble.py`：`MascotBubble` 类 — 像素角色（16×16 网格放大至 64×64）+ 像素对话气泡（锯齿边角），支持 `mascot_id`/`message`/`position`（左下/右下）
- [ ] **1.13** 创建 `app/ui/components/pixel_checkbox.py`：`PixelCheckbox` 类 — 4×4 像素勾选框，选中时显示勾号 ✅，用于任务列表
- [ ] **1.14** 创建 `app/ui/components/pixel_stepper.py`：`PixelStepper` 类 — 像素风格步进器，[-] [数字] [+] 三段水平排列，按钮为 32×32 小方块

## 像素边框工具

- [ ] **1.15** 创建 `app/ui/utils.py`：`pixel_border_raised()` — 生成凸起像素边框样式（亮面 top+left，暗面 bottom+right，2px 粗）
- [ ] **1.16** 创建 `app/ui/utils.py`：`pixel_border_inset()` — 生成内凹像素边框样式（暗面 top+left，亮面 bottom+right，2px 粗）
- [ ] **1.17** 创建 `app/ui/utils.py`：`pixel_shadow()` — 生成 2px 偏移纯黑像素阴影样式
- [ ] **1.18** 创建 `app/ui/utils.py`：`snap_to_grid(value)` — 数值对齐到 8px 网格

## 测试

- [ ] **1.19** 编写 `app/tests/ui/test_tokens.py`：验证所有令牌常量类型正确、色值格式为 7 位 hex、网格常量均为正整数
- [ ] **1.20** 编写 `app/tests/ui/test_base_components.py`：`PixelButton` 按下态切换、`PixelInput` 文本绑定、`ConfirmDialog` 打开/关闭、`CollapsibleGroup` 展开/折叠、`PixelCheckbox` 勾选切换
