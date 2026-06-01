# UI-06 — 设置页

> 职责：全部参数设置界面，含分组折叠、时间选择器、数字输入、工作日选择、备份恢复
> 依赖：UI-01（设计令牌 + 基础组件）

---

## 分组折叠

- [ ] **6.1** 创建 `app/ui/screens/settings_screen.py`：`SettingsScreen` 主容器 — `ScrollView` 垂直布局，4 个 `CollapsibleGroup` 依次排列：上班时间、奖惩金额、对赌配置、其他，默认全部展开

## 上班时间组

- [ ] **6.2** 创建 `app/ui/components/time_picker_row.py`：`TimePickerRow` 类 — 单条时间设置行，左侧标签（"上午上班"）+ 右侧时间值按钮（"09:00"），点击弹出时间选择器，选中后调用 `SettingsService.set()`
- [ ] **6.3** 在 `settings_screen.py`：上班时间组内容 — 4 条 `TimePickerRow`（上午上班/下班、下午上班/下班）+ 工作日多选行（☑一☑二☑三☑四☑五☐六☐日），点击切换勾选，调用 `SettingsService.set_work_days()`

## 奖惩金额组

- [ ] **6.4** 创建 `app/ui/components/amount_picker_row.py`：`AmountPickerRow` 类 — 单条金额设置行，左侧标签（"迟到罚款"）+ 右侧金额值按钮（"-10"），点击弹出数字输入弹窗
- [ ] **6.5** 在 `settings_screen.py`：奖惩金额组内容 — 4 条 `AmountPickerRow`（迟到罚款、早退罚款、旷工罚款、全勤奖励），金额输入限制正整数，自动补负号（罚款类）

## 对赌配置组

- [ ] **6.6** 在 `settings_screen.py`：对赌配置组内容 — 3 条 `AmountPickerRow`（基础奖励、超额奖励、惩罚金额），金额为正整数

## 其他组

- [ ] **6.7** 在 `settings_screen.py`：其他组内容 — 男友奖励时长门槛（`AmountPickerRow`，单位小时）、拍摄日奖励金额（`AmountPickerRow`）
- [ ] **6.8** 在 `settings_screen.py`：服务器地址行 — `PixelInput` 文本行，预填当前 `SettingsService.get("server_url")`
- [ ] **6.9** 在 `settings_screen.py`：同步 Token 行 — `PixelInput` 密码遮蔽行，预填当前 Token
- [ ] **6.10** 在 `settings_screen.py`：备份数据按钮 — `PixelButton`（天空蓝），点击弹出确认框，确认后调用 `SyncService.backup_full()`，Toast 提示结果
- [ ] **6.11** 在 `settings_screen.py`：恢复数据按钮 — `PixelButton`（暖橙），点击弹出确认框（警告覆盖当前数据），确认后调用 `SyncService.restore_full()`
- [ ] **6.12** 在 `settings_screen.py`：版本号行 — "版本 1.0.0" 灰色小字，连点 5 次进入开发面板（`PixelInput` 显示原始 JSON 数据）

## 编辑交互

- [ ] **6.13** 创建 `app/ui/components/pixel_time_picker.py`：`PixelTimePicker` 弹窗 — 像素风格时间选择器，小时/分钟两列滚动选择，确认/取消按钮，返回 "HH:MM" 格式
- [ ] **6.14** 创建 `app/ui/components/pixel_number_dialog.py`：`PixelNumberDialog` 弹窗 — 像素风格数字输入，标题提示当前设置项名，`PixelInput`（数字键盘限制），确认/取消

## 测试

- [ ] **6.15** 编写 `app/tests/ui/test_settings_screen.py`：时间选择器→值回写、金额输入→值回写、工作日切换→勾选变化、分组折叠→内容隐藏
- [ ] **6.16** 在 `test_settings_screen.py`：备份按钮→调用 SyncService、恢复按钮→确认弹窗→调用 SyncService、版本号连点 5 次→开发面板出现
