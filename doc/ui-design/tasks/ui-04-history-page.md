# UI-04 — 历史页

> 职责：周/月/年三种历史视图，含日历色块、每日卡片、月度汇总
> 依赖：UI-01（设计令牌 + 基础组件）

---

## 顶部 Tab 与切换

- [ ] **4.1** 创建 `app/ui/components/history_tabs.py`：`HistoryTabs` 类 — 三个 Tab 按钮 [ 周 ] [ 月 ] [ 年 ]，像素直角按钮，选中项明黄色底 + 暗面边框，未选中奶油色底
- [ ] **4.2** 在 `history_tabs.py`：Tab 切换动画 — 150ms 渐隐渐显（透明度交叉），切换后更新下方内容区
- [ ] **4.3** 在 `history_tabs.py`：左右箭头 ← → 组件，8×8 像素三角箭头，用于切换周/月/年范围

## 周视图

- [ ] **4.4** 创建 `app/ui/components/day_card.py`：`DayCard` 类 — 单日摘要卡片，2px 边框 + 2px 右移纯黑阴影，内容：日期+星期（如"5月25日 周一"）、各时段状态摘要（正常✅/迟到⚠️/旷工🔴等）、工作时长、当日奖惩金额、底部"点击看明细→"
- [ ] **4.5** 在 `day_card.py`：特殊状态渲染 — 拍摄日显示 📸 橙色底 + 咪咕图标、"点击看复盘→"；非工作日/休息日显示 🐼 团团图标 + "休息日"；请假显示 🔵 蓝色底
- [ ] **4.6** 创建 `app/ui/screens/history_screen.py`：周视图容器 — 顶部 "← 5/25-5/31 第22周 →" 切换栏 + `ScrollView` 内含 7 张 `DayCard` + 底部 "本周合计: +N" 汇总
- [ ] **4.7** 在 `history_screen.py`：左右滑动切换周（Gesture 检测），滑动距离 > 50px 触发切换

## 月视图

- [ ] **4.8** 创建 `app/ui/components/calendar_cell.py`：`CalendarCell` 类 — 单日色块，12×12 dp，颜色映射：绿=全天正常、黄=有迟到/早退、红=有旷工、蓝=请假、橙=拍摄日、🐼=非工作日、○=无数据/未来
- [ ] **4.9** 在 `history_screen.py`：月视图容器 — 顶部 "← 2026年 6月 →" 切换栏 + 7 列星期头（一二三四五六日）+ 6 行 × 7 列 `CalendarCell` 网格 + 底部按周汇总（"第1周: +50" "第2周: -30"...）
- [ ] **4.10** 在 `history_screen.py`：月视图左右滑动切换月份（Gesture 检测）

## 年视图

- [ ] **4.11** 创建 `app/ui/components/month_card.py`：`MonthCard` 类 — 单月汇总卡片，2px 边框 + 2px 阴影，内容："N月" + 出勤天数/迟到次数/旷工次数/总时长/奖惩净额
- [ ] **4.12** 在 `history_screen.py`：年视图容器 — 顶部 "← 2026年 →" 切换栏 + `ScrollView` 内含 12 张 `MonthCard`（按月排列）

## 路由与数据

- [ ] **4.13** 在 `history_screen.py`：整合三视图切换逻辑 — 默认打开当前周视图，记忆上次查看的 Tab
- [ ] **4.14** 在 `history_screen.py`：数据绑定 — 通过 `HistoryService` 获取周/月/年数据，Tab 切换时重新请求

## 测试

- [ ] **4.15** 编写 `app/tests/ui/test_history_screen.py`：Tab 切换渲染正确视图、DayCard 各状态颜色正确、CalendarCell 颜色映射正确
- [ ] **4.16** 在 `test_history_screen.py`：周/月/年箭头切换范围正确、汇总计算正确
