# M7 — 同步模块 子任务

> 职责：WebSocket 实时推送 + 云端备份恢复 + 后端检阅端

---

## 数据层

- [ ] **7.1** 创建 `app/repositories/sync_repo.py`：同步状态记录（上次备份时间等）

## APP 端服务层

- [ ] **7.2** 创建 `app/services/sync_service.py`：`connect()` — 建立 WebSocket + 自动重连
- [ ] **7.3** 实现 `push_event(event_type, payload)` — 推送单条事件
- [ ] **7.4** 实现 `backup_full()` — SQLite → JSON → POST `/sync/backup`
- [ ] **7.5** 实现 `restore_full()` — GET `/sync/restore` → 清空本地 → 逐表写入
- [ ] **7.6** 实现离线缓存：无网络时缓存事件，恢复后批量推送

## 后端服务 (server/)

- [ ] **7.7** 创建 `server/main.py`：FastAPI 入口 + 中间件（Token 认证、日志）
- [ ] **7.8** 创建 `server/routes/sync_routes.py`：`POST /sync/backup` / `GET /sync/restore` / `POST /sync/event`
- [ ] **7.9** 创建 `server/routes/review_routes.py`：`GET /review/status` / `GET /review/history`
- [ ] **7.10** 创建 `server/services/push_service.py`：WebSocket 连接池 + `broadcast()` / `send_to_user()`
- [ ] **7.11** 实现 `/ws` WebSocket 端点（Token 认证在 query param）

## 检阅端网页

- [ ] **7.12** 创建 `server/templates/review.html`：左侧实时状态面板 + 右侧历史数据（纯 HTML + JS）
- [ ] **7.13** 实现网页 WebSocket 连接：自动接收推送更新状态

## 测试

- [ ] **7.14** WebSocket 连接/断线重连/心跳 测试
- [ ] **7.15** 打卡事件推送端到端 + 备份→恢复数据一致性 测试
- [ ] **7.16** Token 认证失败 → 401 测试
