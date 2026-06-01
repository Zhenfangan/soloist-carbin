# M4 — 拍摄日模块 子任务

> 职责：拍摄日设定/切换 + 复盘问卷 + 文字总结生成

---

## 数据层

- [ ] **4.1** 创建 `app/models/shooting.py`：`ShootingDay` / `ShootingReflection` 数据类
- [ ] **4.2** 创建 `app/repositories/shooting_repo.py`：`get_by_date` / `set_shooting_day` / `cancel` / `save_reflection` / `get_reflection`

## 服务层

- [ ] **4.3** 创建 `app/services/shooting_service.py`：`set_shooting_day(date, reward_desc)` + 发布 `SHOOTING_DAY_SET`
- [ ] **4.4** 实现 `cancel_shooting_day(date)` — 窗口期校验（当天上午打卡前）
- [ ] **4.5** 实现 `is_shooting_day(date)` / `get_reflection_questions()`
- [ ] **4.6** 实现 `submit_reflection(date, answers)` — 保存复盘 + `_generate_summary(answers)` 模板拼接
- [ ] **4.7** 实现 `_generate_summary(answers)` — 三种顺利度各一套模板，随机过渡词
- [ ] **4.8** 实现复盘触发调度：拍摄日 23:00 检查未复盘 → 弹窗

## UI 层

- [ ] **4.9** 创建拍摄日设定组件：日期选择器 + 奖励描述输入
- [ ] **4.10** 创建 `app/components/shooting_reflection_dialog.py`：四问题表单 + 顺利度三选一
- [ ] **4.11** 创建拍摄中状态展示：主界面显示"📸 拍摄中" + 隐藏打卡

## 测试

- [ ] **4.12** 提前预设 / 当天窗口期内切换 / 超时拒绝 测试
- [ ] **4.13** 复盘总结三种场景（smooth/normal/rough）生成测试
