# UI-02 — 像素资源（角色 + 图标 + 字体）

> 职责：5 只像素小动物 sprite sheet + 16 个功能图标 + 像素字体集成
> 依赖：无（独立设计资源，可并行）

---

## 像素字体

- [ ] **2.1** 下载并放置像素字体文件到 `app/ui/assets/fonts/`：`PressStart2P.ttf`（英文像素）、`Silkscreen-Regular.ttf`（备选）、如需要中文像素字体则选 `Zpix.ttf`（最像素 11px 中文）
- [ ] **2.2** 创建 `app/ui/fonts.py`：`load_pixel_fonts()` — 注册所有像素字体到 Kivy 字体系统，返回字体名映射

## 像素角色 Sprite Sheet

- [ ] **2.3** 创建 `app/ui/assets/sprites/dudu_32x32.png`：兜兜（小熊）sprite sheet，32×32 每帧 × 4 帧横向排列 = 128×32，待机/跳1/跳2/✌️ 各一帧，主色 `#D4A040` + 亮面 `#F0C060` + 暗面 `#A88030` + 轮廓 `#6B4420`，≤4 色，nearest-neighbor 放大
- [ ] **2.4** 创建 `app/ui/assets/sprites/wengweng_16x16.png`：嗡嗡（小蜜蜂）sprite sheet，16×16 × 4 帧 = 64×16，待机/飞1/飞2/打气，主色 `#FFE030` + 亮面 `#FFF0A0` + 暗面 `#D0B020` + 条纹 `#202020`
- [ ] **2.5** 创建 `app/ui/assets/sprites/tuantuan_32x32.png`：团团（熊猫）sprite sheet，32×32 × 4 帧 = 128×32，待机/冒出/抱星/转圈，主色 `#F0F0F0` + 亮面 `#FFFFFF` + 暗面 `#D0D0D0` + 黑眼圈 `#202020`
- [ ] **2.6** 创建 `app/ui/assets/sprites/wangzai_32x32.png`：旺仔（小狗）sprite sheet，32×32 × 4 帧 = 128×32，待机/摇尾1/摇尾2/撒花，主色 `#FF6B8A` + 亮面 `#FFA0B8` + 暗面 `#D94A6A` + 白肚皮 `#FFFFFF`
- [ ] **2.7** 创建 `app/ui/assets/sprites/migu_16x16.png`：咪咕（小猫）sprite sheet，16×16 × 4 帧 = 64×16，待机/歪头/眨眼/灵感，主色 `#B090F0` + 亮面 `#D0C0FF` + 暗面 `#9070D0` + 黄眼 `#FFE030`

## 像素功能图标

- [ ] **2.8** 创建 `app/ui/assets/icons/` 目录，编写图标清单 16 项：打卡（印章+勾）、历史（日历折角）、对赌（十字靶心）、设置（8齿齿轮）、签到（空心方格→填实+勾）、签退（空心方格+箭头）、请假（方形信封）、添加（十字加号）、战报（卷轴）、保存（下箭头+横线）、结算（天平）、箭头←、箭头→、勾号✓、叉号✗、警告⚠
- [ ] **2.9** 逐个绘制 16 个像素图标 PNG，画布 16×16，单色为主最多 2 色，1px 线条，nearest-neighbor 放大至 32×32 dp 使用

## 资源加载器

- [ ] **2.10** 创建 `app/ui/assets/loader.py`：`SpriteLoader` 类 — `load_sprite(mascot_id)` 从 PNG 加载并切片为帧列表（按 `frame_width` 等分宽度），返回 `list[Image]`
- [ ] **2.11** 在 `loader.py`：`IconLoader` 类 — `get_icon(icon_name)` 返回对应图标 `Image`，支持 `color` 参数做染色（单色图标用 `Image.color` 属性）
- [ ] **2.12** 在 `loader.py`：`preload_all()` — 启动时将全部 sprite 和 icon 一次性加载到内存字典

## 测试

- [ ] **2.13** 编写 `app/tests/ui/test_assets.py`：验证所有 sprite PNG 文件存在、尺寸正确（16×16 或 32×32 每帧）、帧数≥4
- [ ] **2.14** 在 `test_assets.py`：验证 16 个图标文件存在、SpriteLoader 切片帧数正确、IconLoader 返回正确 Image
