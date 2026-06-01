# M8 — 激励模块 子任务

> 职责：连续出勤天数统计 + 通知栏常驻卡片

---

## 数据层

- [ ] **8.1** 创建 `app/repositories/streak_repo.py`：`get()` / `update(streak, last_date)`
- [ ] **8.2** 创建 `app/models/streak.py`：`AttendanceStreak` 数据类

## 服务层

- [ ] **8.3** 创建 `app/services/motivation_service.py`：`get_current_streak()` — 查询连续天数
- [ ] **8.4** 实现 `update_streak(date)` — 订阅 `DAY_FINISHED`，判定加减逻辑
  - 全部 normal → +1
  - 有 late/early_leave/absent/leave → 归零
  - 拍摄日 / 非工作日 → 不变
- [ ] **8.5** 实现 `update_notification(status)` — Android 通知栏常驻卡片
  - `checked_in` → "今日已打卡 ✅"
  - `not_checked_in` → "今日未打卡 ⏳"
  - `shooting` → "拍摄中 📸"
  - 使用 ongoing + low priority，不可划掉

## UI 层

- [ ] **8.6** 主界面添加连续出勤天数展示（"已连续正常出勤 X 天"）
- [ ] **8.7** 实现首次打卡后弹出男友承诺引导通知

## 测试

- [ ] **8.8** 连续正常 / 中断归零 / 拍摄日不变 / 非工作日不变 测试
- [ ] **8.9** 通知卡片状态切换测试
