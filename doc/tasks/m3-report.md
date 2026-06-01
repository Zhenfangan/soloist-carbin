# M3 — 战报模块 子任务

> 职责：手账风格长图生成（数据收集 → HTML 渲染 → 截图 → 保存相册）

---

## 数据模型

- [ ] **3.1** 创建 `app/models/report.py`：`ReportData` / `PeriodDetail` / `PromiseDetail` 数据类

## 模板 & 素材

- [ ] **3.2** 创建 `app/assets/templates/daily_report.html`：办公日战报 Jinja2 模板（手账拼贴风）
- [ ] **3.3** 创建 `app/assets/templates/shooting_report.html`：拍摄日战报模板
- [ ] **3.4** 准备 `app/assets/fonts/` 手写字体 + `app/assets/images/` 贴纸/胶带 SVG

## 服务层

- [ ] **3.5** 创建 `app/services/report_service.py`：`collect_data(date)` — 从各 Repo 组装 `ReportData`
- [ ] **3.6** 实现 `generate_html(data)` — Jinja2 渲染 → HTML 字符串
- [ ] **3.7** 实现 `screenshot(html)` — Android WebView 加载 HTML → 截图 PNG（定宽，高度自适应）
- [ ] **3.8** 实现 `save_to_gallery(image_path)` — 权限检查 + 写入系统相册
- [ ] **3.9** 实现 `generate_and_save(date)` — 一键全流程

## UI 层

- [ ] **3.10** 创建 `app/screens/report_screen.py`：战报预览 + 保存按钮 + 分享入口

## 集成

- [ ] **3.11** 订阅 `DAY_CLOSED` → 自动生成保存战报；支持手动触发生成

## 测试

- [ ] **3.12** 办公日 / 拍摄日 战报数据收集完整性测试
- [ ] **3.13** HTML 模板渲染正确性测试（Jinja2 变量全覆盖）
- [ ] **3.14** 超 8h 鼓励框 / 男友承诺兑现显示 条件测试
