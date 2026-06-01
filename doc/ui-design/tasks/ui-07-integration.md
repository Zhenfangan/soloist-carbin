# UI-07 — 引导流程 + 全局整合

> 职责：首次引导分步设置 + 底部导航栏 + 页面路由 + 动画系统 + App 入口
> 依赖：UI-01~06 全部完成

---

## 动画系统

- [ ] **7.1** 创建 `app/ui/animations/core.py`：`FrameAnimator` 类 — 逐帧动画播放器，接收 sprite sheet 切片列表，按固定帧率（4 FPS = 250ms/帧）循环或单次播放，支持 `loop`/`reverse`/`on_complete` 回调
- [ ] **7.2** 在 `core.py`：`SpritePlayer` 类 — 将 `FrameAnimator` 绑定到一个 `Image` widget，自动更新 `source` 属性，封装为可复用的 Widget 子类
- [ ] **7.3** 在 `core.py`：`pixel_expand(height_delta, duration)` — 像素阶梯式高度变化动画，每 8px 一步，200ms 内完成
- [ ] **7.4** 在 `core.py`：`pixel_fade_in(widget, duration)` / `pixel_fade_out(widget, duration)` — 像素风格淡化，配 ease-in-out
- [ ] **7.5** 在 `core.py`：`pixel_slide_in(widget, direction, duration)` — 像素风格滑入，X 轴或 Y 轴，250ms

## 全局导航系统

- [ ] **7.6** 创建 `app/ui/navigation.py`：`BottomTabBar` 类 — 底部导航栏，固定高度 56px，4 个 Tab（打卡/历史/对赌/设置），每个 Tab 含像素图标（16×16→32×32）+ 小字标签，选中项明黄色高亮，未选中灰褐色
- [ ] **7.7** 在 `navigation.py`：创建 4 个像素 Tab 图标 PNG（打卡=印章、历史=日历、对赌=靶心、设置=齿轮），使用 UI-02 图标规范，存放于 `app/ui/assets/icons/tabs/`
- [ ] **7.8** 在 `navigation.py`：Tab 点击切换页面 — 使用 `ScreenManager` 切换 4 个子页面，页面切换动画 X 轴推入 200ms
- [ ] **7.9** 在 `navigation.py`：`AppScreenManager` 类 — Kivy `ScreenManager`，注册 4 个页面 Screen（CheckinScreen、HistoryScreen、BetScreen、SettingsScreen），切换时触发渐隐渐显

## 首次引导流程

- [ ] **7.10** 创建 `app/ui/screens/onboarding_screen.py`：`OnboardingScreen` 主容器 — 分步引导流程框架，一次只显示一张卡片
- [ ] **7.11** 在 `onboarding_screen.py`：第 1 步 — 欢迎卡片：🐻 兜兜大图（64×64）+ "欢迎来到 Soloist Cabin Pro" 标题 + 像素副标题 + "开始设置" `PixelButton`（明黄）
- [ ] **7.12** 在 `onboarding_screen.py`：第 2 步 — 上午时间设置：🐝 嗡嗡图标 + "上午上班/下班时间" + 两个 `TimePickerRow` + "下一步"按钮
- [ ] **7.13** 在 `onboarding_screen.py`：第 3~N 步 — 依次设置：下午时间（旺仔图标）→ 工作日选择（团团图标）→ 惩罚金额 → 全勤奖励 → 男友门槛 → 拍摄日奖励，每步一只小动物在卡片旁
- [ ] **7.14** 在 `onboarding_screen.py`：最后一步 — 完成卡片：🐻 兜兜 + 🐶 旺仔同框 + "全部准备好了！" + "进入主界面" `PixelButton`（薄荷绿）
- [ ] **7.15** 在 `onboarding_screen.py`："跳过"按钮 — 每个可选步骤（拍摄日相关）提供跳过按钮，灰色小字，点击跳过至下一步
- [ ] **7.16** 在 `onboarding_screen.py`：每步骤切换动画 — 200ms 像素阶梯式切换，旧卡片收起 → 新卡片展开

## App 入口

- [ ] **7.17** 更新 `app/main.py`：`SoloistApp` 继承 `MDApp`，加载像素字体 + 预加载所有 sprite/icon 资源
- [ ] **7.18** 在 `main.py`：首次启动检测 — 调用 `SettingsService.is_first_launch()`，是则显示 `OnboardingScreen`，否则直接进入 `AppScreenManager`（主界面）
- [ ] **7.19** 在 `main.py`：应用全局像素主题 — 设置窗口底色为奶油色 `#FFF8E8`，全局默认字体为像素字体
- [ ] **7.20** 在 `main.py`：退出时释放资源 — `SpriteLoader` 清理、`EventBus` 取消订阅

## 战报弹层集成

- [ ] **7.21** 创建 `app/ui/components/report_preview.py`：`ReportPreview` 类 — 全屏弹层（Y 轴从底部滑入，250ms），顶部标题行 "2026.6.1 战报" + 中间可滚动像素战报长图预览 + 底部两个 `PixelButton`："保存至相册"（天空蓝）、"退出并结算"（薄荷绿）
- [ ] **7.22** 在 `report_preview.py`："保存至相册"调用 `Screenshotter.save_png()` → Toast 提示成功
- [ ] **7.23** 在 `report_preview.py`："退出并结算"触发日切结算流程 → 关闭弹层 → 更新打卡页状态

## 全局整合检查

- [ ] **7.24** 全局像素一致性检查：所有页面使用 UI-01 令牌常量（不硬编码色值）、所有可点按钮使用 `PixelButton`、所有输入使用 `PixelInput`、所有弹窗使用像素边框样式
- [ ] **7.25** 全局交互检查：角色出场与 UI 文档第 5 章一致（兜兜→打卡/战报、嗡嗡→工作中/加班、团团→休息日/结算、旺仔→任务完成/承诺、咪咕→拍摄日/复盘）
- [ ] **7.26** 像素网格对齐检查：所有间距为 8 的倍数、所有边框 2px、所有阴影 2px 偏移纯黑

## 测试

- [ ] **7.27** 编写 `app/tests/ui/test_onboarding.py`：首次启动→引导流程完整走通、最后一步→进入主界面、跳过功能正常
- [ ] **7.28** 编写 `app/tests/ui/test_navigation.py`：4 个 Tab 切换→对应页面显示、选中高亮正确、页面切换动画触发
- [ ] **7.29** 编写 `app/tests/ui/test_animation.py`：`FrameAnimator` 帧序正确、4 FPS 帧率、`pixel_expand` 阶梯步进、`SpritePlayer` 渲染帧切换
- [ ] **7.30** 编写 `app/tests/ui/test_app_entry.py`：首次启动→引导页、非首次→主界面、字体加载成功、资源预加载完成
