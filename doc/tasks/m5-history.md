# M5 — 历史模块 子任务

> 职责：周/月/年三种视图的数据查询与展示

---

## 数据模型

- [ ] **5.1** 创建 `app/models/history.py`：`WeekViewData` / `DayCard` / `MonthViewData` / `CalendarCell` / `YearViewData` / `MonthSummary` 数据类

## 服务层

- [ ] **5.2** 创建 `app/services/history_service.py`：`get_week_view(week_start)` — 每天一张卡片（打卡状态 + 工时 + 奖惩汇总）
- [ ] **5.3** 实现 `get_month_view(year, month)` — 日历格子 + 颜色标记 + 按周汇总
- [ ] **5.4** 实现 `get_year_view(year)` — 12 个月汇总卡片（出勤天数/迟到/旷工/总时长/总奖惩）

## UI 层

- [ ] **5.5** 创建 `app/components/week_view.py`：卡片流，每天一张，点击展开明细
- [ ] **5.6** 创建 `app/components/month_view.py`：日历格子，颜色标记（绿/黄/红/蓝/橙）
- [ ] **5.7** 创建 `app/components/year_view.py`：12 个月汇总卡片
- [ ] **5.8** 创建 `app/screens/history_screen.py`：集成三个视图，顶部 Tab 切换

## 测试

- [ ] **5.9** 空数据 / 混合状态 / 跨月边界 数据查询测试
- [ ] **5.10** 月视图颜色标记 + 年视图汇总 正确性测试
