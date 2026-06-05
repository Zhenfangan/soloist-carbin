# 前端 UI 修复 — 设计方案

> 日期: 2026-06-05
> 作者: andy + Claude
> 状态: 待审查

---

## 1. 背景

后端 9 个模块已完成 + 三轮测试通过；UI 阶段 1-4 也已实现（设计令牌 / 像素资源 / 4 个核心页面 / 引导整合）。但首次实测发现多处渲染与交互 bug。

本 spec 记录本次"前端 UI 修复"的范围、根因诊断、修复路径，作为后续 `writing-plans` 与 `do` 阶段的输入。

### 1.1 测试现场

启动 `python -m app.main`（窗口 420 × 750），andy 在 4 个页面切换 + 操作并截图，最终给出 3 张实测截图（保存在 `doc/ui-design/testphoto/ScreenShot_2026-06-05_173*.png`），分别对应：

- 截图 1：打卡页（被 Windows 剪贴板提示遮挡，但能看出主要布局）
- 截图 2：对赌页（中部大片空白）
- 截图 3：设置页 + "拍摄日奖励" 弹窗（确认按钮溢出窗口右边）

历史页 andy 反馈"正常"，未截图。

---

## 2. Bug 清单（最终）

| # | Bug | 位置 | 把握 | 波次 |
|---|---|---|---|---|
| 1 | `PixelInput._redraw` 亮面 right 矩形 `size=(w, h)` 应为 `(bw, h)` | `app/ui/components/pixel_input.py:103` | 100% | 第一波 |
| 2 | `PixelStepper._redraw` 同样的 `size=(w, h)` 应为 `(bw, h)` | `app/ui/components/pixel_stepper.py:151` | 100% | 第一波 |
| 3 | `AddTaskDialog` 输入框 `pos_hint={"x": 0.5}` 应为 `center_x` → input 溢出 card 128px | `app/ui/components/add_task_dialog.py:117` | 100% | 第一波 |
| 4 | `app/ui/assets/fonts/` 两个未使用的中文像素字体（`FZXS15.ttf`、`方正像素15.ttf`） | 文件系统 | 100% | 第一波 |
| 5 | 底部导航栏 3 张截图都只显示 1 个 tab，应 4 个 | `app/ui/navigation.py` | 90% | 第二波 |
| 6 | "拍摄日奖励" / `PixelNumberDialog` 弹窗的"确认"按钮溢出窗口右边 | `pixel_number_dialog.py` 或 `pixel_button.py` | 80% | 第二波 |
| 7 | 输入框点开后无法输入 / 不弹键盘 / 中文 IME 不工作 | `pixel_input.py` + ModalView + Windows IME | 60% | 第二波 |

### 2.1 已确认不动的项

- ❌ 字体方向：保留 `SmileySans-Oblique.ttf`（andy 决定不要像素风字体）
- ❌ 设置页"备份数据"（深蓝）、"恢复数据"（深棕）：设计意图，标识危险操作
- ❌ 历史页：andy 反馈正常
- ❌ 打卡页底部 "+ 添加任务"：`TaskInlineList` 设计本就有

---

## 3. 修复路径：分两波

### 第一波 — 代码确定的 bug + 文件清理

修复 #1 / #2 / #3 / #4。这 4 项是 100% 代码错误或纯文件操作，改动小、影响明确、可单独验证。

**预期连带效应**：
- #3 修完后，AddTaskDialog 的 input 不再溢出 card，可能解决 #7 中"点击没命中输入框"的猜测
- #1 修完后，PixelInput 右边不再被白矩形覆盖，可能让 #7 中"input 看起来能用但实际有遮挡"的猜测消失

完成后**先让 andy 复测一遍**：
- 打卡页 / 对赌页 / 设置页都点一遍
- 试着开各种弹窗（添加任务、拍摄日奖励、男友承诺等）
- 试着在弹窗内输入文字（关注是否能 focus、是否弹键盘、能否敲中英文）
- 重新截 3-5 张图

### 第二波 — 实测交互 bug 排查

基于第一波后的复测截图，针对 #5 / #6 / #7 剩余问题逐个排查根因：

- **#5 底部导航栏**：在 `BottomTabBar.__init__` 完成后打印每个 TabButton 的 pos / size / opacity，定位是布局问题还是绘制问题
- **#6 弹窗按钮溢出**：检查 `PixelButton` 在 `size_mode="small"` 下的 width 计算，对比 `card_w` 与按钮 layout 实际 width
- **#7 输入法**：根据第一波后的反馈分情况处理：
  - 若 focus 不上 → ModalView 与 TextInput 的 keyboard binding 问题
  - 若 focus 上但中文 IME 不工作 → Kivy on Windows 已知问题，需配置 `Config.set('kivy', 'keyboard_mode', 'system')`

第二波每个 bug 独立处理，可能产生子方案 spec。

### 3.1 拒绝方案

- **「一次性全修」**：要先实测才能定位 #5/#6/#7 根因，#1-3 修完后实测情况会变，没必要先把 #5-7 当做独立目标重投精力
- **「只修代码 bug 不动 #5-7」**：andy 实测时遇到了交互问题，必须处理，否则不能算"UI 修好"

---

## 4. 测试与验证

### 4.1 自动化测试（每波修完跑）

```powershell
pytest app/tests/ui/ -v
mypy --strict app/ui/
ruff check app/ui/
```

三者全过才认为代码门禁通过。

### 4.2 视觉验证（每波修完做）

启动 `python -m app.main`，andy 实际操作并截图。截图保存到 `doc/ui-design/testphoto/`，作为下一波的输入。

---

## 5. 不在本次范围

- 任何 UI 视觉风格的重新设计（颜色、字体、动画）
- 任何新功能添加
- 任何后端服务的改动

---

## 6. 文件清单（第一波）

将修改：
- `app/ui/components/pixel_input.py`（一处）
- `app/ui/components/pixel_stepper.py`（一处）
- `app/ui/components/add_task_dialog.py`（一处）

将删除：
- `app/ui/assets/fonts/FZXS15.ttf`
- `app/ui/assets/fonts/方正像素15.ttf`

（注：之前 git status 显示项目根有同名文件，实际检查后只在 fonts/ 目录下；项目根无字体文件需要清理）

如有对应测试需要相应调整（如 `pixel_input` 的视觉边框测试有像素断言），一并修改。

---

## 7. Open Question — 留给 andy 审查时回答

无。本 spec 已收齐所有澄清；如 andy 审查后有补充，再回写。
