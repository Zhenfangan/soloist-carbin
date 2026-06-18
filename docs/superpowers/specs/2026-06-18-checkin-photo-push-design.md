# 打卡推送通知 — 设计文档

| 字段 | 值 |
|---|---|
| 日期 | 2026-06-18 |
| 作者 | andy |
| 状态 | Draft（待 writing-plans 转化为实施计划） |
| 相关文件 | `app/services/checkin_service.py`、`app/services/event_bus.py`、`app/services/sync_service.py` |

---

## 1. 背景与目标

### 1.1 现状

- 项目已实现「打卡 + 拍照」流程：`CheckinScreen → CameraService → CheckinService`，照片落本地 `user_data/photos/{date}/{period}_{action}.jpg`
- 项目已有 `EventBus`：`CheckinService.check_in / check_out / mark_absent / apply_leave` 都会 publish 相应事件
- 项目已有 `sync_service.py` 但为 stub，且其设计目标是「服务器中转 + 检阅端浏览器」，需用户主动打开网页

### 1.2 用户需求

andy 希望「打卡后服务器推送到我手机」—— 接收方为 andy 自己，使用华为 Android（非鸿蒙 NEXT），希望**主动推送到手机锁屏 / 通知中心**，无须打开网页。

### 1.3 目标（V1）

1. 每次「签到 / 签退 / 判定旷工」时，向 andy 的手机推送一条文字通知
2. 通知内容含：时段、动作、时间、状态（正常 / 迟到 / 早退 / 旷工 / 请假 / 拍摄日）
3. 离线时入队、网络恢复后补发，不丢消息
4. UI 零侵入、可在设置页开关与配置
5. 第一次接入，**最简、最少依赖、最少 bug**

### 1.4 非目标（V1 不做）

- 不推送照片（v2 可加 ntfy attachment）
- 不做自有服务器中转（APP 直推 ntfy.sh 公共服务）
- 不做请假 UI 改造（独立任务；后端已支持，推送规则已预留）
- 不做多渠道（不上微信 / Bark / Telegram）
- 不修改 `sync_service.py` stub（其归属另一模块，本任务不耦合）

---

## 2. 总体架构

```
CheckinScreen.拍照确认
        ↓ (call)
CheckinService.check_in / check_out / mark_absent
        ↓ (publish, 同步)
EventBus
   ├── CHECK_IN_COMPLETED
   ├── CHECK_OUT_COMPLETED
   └── ATTENDANCE_JUDGED
        ↓ (subscribe)
NtfyPushService._on_event
   ├── 去重检查 (5s TTL)
   ├── 格式化消息文本
   └── 入内存 queue
        ↓ (daemon thread 消费)
HTTP POST  {server}/{topic}
   ├── 成功 → 丢弃
   └── 失败 → 落盘 user_data/push_queue.json
        ↓ (APP 下次启动)
NtfyPushService.start() 读取 JSON → flush 补发
```

### 关键性质

| 属性 | 保证方式 |
|---|---|
| UI 零侵入 | 通过 EventBus 订阅，不动 `checkin_screen.py` |
| 业务零侵入 | `CheckinService` 已 publish 事件，不改 |
| 唯一接入点 | `app/main.py` 启动时 `NtfyPushService(...)` 实例化即自动订阅 |
| 不阻塞 UI | EventBus.publish 是同步的，订阅者**只入队**，HTTP 在 daemon 线程发 |
| 离线不丢消息 | 失败入持久化 JSON 队列，重启时补发 |
| 时钟模拟一致 | 推送文本里时间取自 `payload['checkin_time']`，与 UI 显示一致 |

---

## 3. 组件清单

### 3.1 新增 / 修改文件

| 文件 | 状态 | 改动 |
|---|---|---|
| `app/services/ntfy_service.py` | 新建 | `NtfyPushService` 类、文案映射、内存 + 持久化队列、daemon 线程 |
| `app/services/settings_service.py` | 修改 | `DEFAULTS` 新增 3 个键（见 §5） |
| `app/ui/screens/settings_screen.py` | 修改 | 新增「推送通知」区块：开关、topic 输入、测试按钮 |
| `app/main.py` | 修改 | 启动时实例化 `NtfyPushService` 并调用 `start()` |
| `app/tests/test_ntfy_service.py` | 新建 | 单测：消息格式 / 状态映射 / 去重 / 开关 / 空 topic skip |
| `app/tests/test_ntfy_offline_queue.py` | 新建 | 单测：失败入队、重启 flush |
| `app/tests/test_ntfy_integration.py` | 新建 | 集成：真实 EventBus.publish 触发推送（mock HTTP） |

### 3.2 NtfyPushService 接口草案

```python
class NtfyPushService:
    def __init__(self, settings_service: SettingsService, queue_path: Path | None = None) -> None: ...

    def start(self) -> None:
        """启动 daemon 线程 + flush 持久化队列；订阅 EventBus 事件。"""

    def stop(self) -> None:
        """停止线程并 flush 当前内存队列到磁盘（测试用）。"""

    def send_test(self) -> bool:
        """从设置页点击「测试推送」时调用，同步发一条 'soloist 测试通知'，返回成功与否。"""

    # 内部
    def _on_event(self, event_type: EventType, payload: dict[str, Any]) -> None: ...
    def _format_message(self, event_type: EventType, payload: dict[str, Any]) -> str | None: ...
    def _enqueue(self, msg: str) -> None: ...
    def _consume_loop(self) -> None: ...
    def _persist_queue(self) -> None: ...
```

---

## 4. 推送规则

### 4.1 订阅与触发

| 订阅事件 | 处理逻辑 |
|---|---|
| `CHECK_IN_COMPLETED` | 永远推送，文案含状态 |
| `CHECK_OUT_COMPLETED` | 永远推送，文案含状态 |
| `ATTENDANCE_JUDGED` | **仅当** `status ∈ {absent_morning, absent_afternoon}` 推送（旷工通知） |

`ATTENDANCE_JUDGED` 在签到、请假、旷工判定时都会发；通过状态过滤避免重复（签到的 normal/late 走 `CHECK_IN_COMPLETED`、请假留给将来 UI 完成后扩展）。

### 4.2 文案样例

| 事件 + 状态 | 推送内容 |
|---|---|
| CHECK_IN_COMPLETED + normal | `上午签到 09:12 ✨ 正常` |
| CHECK_IN_COMPLETED + late | `上午签到 09:35 ⚠️ 迟到` |
| CHECK_OUT_COMPLETED + normal | `上午签退 12:00 ✨ 正常` |
| CHECK_OUT_COMPLETED + early_leave | `上午签退 11:30 ⚠️ 早退` |
| ATTENDANCE_JUDGED + absent_morning | `🚨 上午旷工：到 12:00 仍未签到` |

旷工文案里的「12:00」取自 `settings.morning_end` / `afternoon_end`，而非 `payload['checkin_time']`（旷工事件 payload 不含时间）。

### 4.3 文案映射常量

```python
STATUS_LABELS = {
    "normal":           ("✨", "正常"),
    "late":             ("⚠️", "迟到"),
    "early_leave":      ("⚠️", "早退"),
    "absent_morning":   ("🚨", "上午旷工"),
    "absent_afternoon": ("🚨", "下午旷工"),
    "leave":            ("🏠", "请假"),     # 预留，请假 UI 完成后生效
    "shooting":         ("🎬", "拍摄日"),
}

PERIOD_CN = {"morning": "上午", "afternoon": "下午", "evening": "晚上"}
ACTION_CN = {"in": "签到", "out": "签退"}
```

### 4.4 去重

- key: `f"{date}|{period}|{status}|{event_type.value}"`
- 容器: `dict[key, monotonic_ts]`
- TTL: 5 秒；超时项被新事件触发时清理（无需后台 GC）
- 用 `time.monotonic()`，**不**走项目的 `get_clock()`（去重是真实时间维度，不该被时钟模拟影响）

---

## 5. 配置项

`SettingsService.DEFAULTS` 新增：

| key | 默认 | 类型 / 含义 |
|---|---|---|
| `ntfy_enabled` | `"0"` | `"1"` 启用，`"0"` 禁用（禁用时 `_on_event` 直接 return） |
| `ntfy_topic` | `""` | ntfy 主题名，空值时跳过推送并 INFO 日志一次 |
| `ntfy_server` | `"https://ntfy.sh"` | 服务器根 URL，便于将来自建 |

### 设置页 UI

`settings_screen.py` 增加「推送通知」区块：

1. **开关** —— 绑定 `ntfy_enabled`
2. **Topic 输入框** —— 绑定 `ntfy_topic`，旁边一个「生成随机」按钮（16 位 `secrets.token_urlsafe`）
3. **服务器输入框** —— 折叠在「高级」，绑定 `ntfy_server`
4. **测试推送按钮** —— 调 `NtfyPushService.send_test()`，结果用 toast / label 反馈

---

## 6. 数据流（端到端，单次签到）

```
T+0ms   用户点签到按钮 → CameraService.take_photo
T+...   用户拍完照、确认
T+ε     checkin_screen._finish_checkin(period, photo_path)
        → CheckinService.check_in(...)
            → DB upsert
            → _judge_checkin_status → "late"
            → EventBus.publish(CHECK_IN_COMPLETED, {date, period:'morning', checkin_time:'09:35', status:'late'})
                ├─ (UI 订阅者：状态刷新)
                └─ NtfyPushService._on_event
                    ├─ enabled? yes
                    ├─ 去重 key: "2026-06-18|morning|late|check_in_completed"  → 新键
                    ├─ format: "上午签到 09:35 ⚠️ 迟到"
                    └─ memory_queue.put(msg)
        return CheckinResult

  (daemon 线程在后台另一线)
        memory_queue.get() → "上午签到 09:35 ⚠️ 迟到"
        requests.post("https://ntfy.sh/{topic}", data=msg.encode("utf-8"), timeout=3)
        if 2xx:  done
        else:    fallback → persist_queue.append(msg) → write JSON
```

---

## 7. 错误处理与边界

| 场景 | 行为 |
|---|---|
| `ntfy_enabled = "0"` | `_on_event` 第一行 return，零开销 |
| `ntfy_topic == ""` | `_on_event` skip，**每 30s 最多 INFO 一次**（避免刷屏） |
| 网络异常 / 超时 | requests 抛 → catch → 落盘 JSON |
| ntfy 返回 4xx / 5xx | 同上落盘；连续 3 次失败进入 30 秒退避（指数 backoff 上限 30s） |
| 队列文件不存在 | 视为空数组，跳过 flush |
| 队列文件 JSON 解析失败 | WARN 日志、清空文件、不阻塞 |
| 队列条数上限 200 | 满了丢最早，WARN 日志 |
| APP 关闭时队列非空 | daemon 线程随进程退出。仅内存队列里「daemon 尚未取出」的消息可能在崩溃时丢失；正常关闭流程 `stop()` 会先 flush 内存队列到 JSON，下次启动自动补发 |
| 重复事件（`mark_absent` 反复触发） | 5s TTL 去重 set 拦截 |
| topic 名暴露隐私 | 引导生成 16 位随机串；ntfy 协议本身不要求注册 |
| 时钟模拟模式 | 推送文本里时间用 payload，跟 UI 一致；HTTP 重试用真实 monotonic |
| 测试推送 (`send_test`) | 同步走 requests，不入队，便于即时给用户反馈 |

---

## 8. 测试计划

### 8.1 单元测试

`app/tests/test_ntfy_service.py`：

1. `_format_message(CHECK_IN_COMPLETED, {status:'normal', ...})` → 期望文本
2. 状态映射全覆盖（normal/late/early_leave/absent_morning/absent_afternoon/leave/shooting）
3. `_on_event` 在 `enabled=0` 时 0 次入队
4. `_on_event` 在 `topic=""` 时 0 次入队
5. `ATTENDANCE_JUDGED + status=normal` 不入队（只 absent 入）
6. 同一 key 在 5s 内重复触发 → 仅 1 次入队
7. 6s 后再触发 → 入队
8. `send_test` mock 成功 / 失败两种返回

### 8.2 离线队列

`app/tests/test_ntfy_offline_queue.py`：

1. mock requests 抛 → 入持久化 JSON
2. 重启实例 → flush → 取出消息
3. JSON 损坏 → 不抛 + 清空
4. 队列上限 → 丢最早

### 8.3 集成

`app/tests/test_ntfy_integration.py`：

1. 真实 `get_event_bus().publish(CHECK_IN_COMPLETED, ...)` → mock HTTP 拦截 → 验证收到
2. `mark_absent` 触发 → 旷工通知文案
3. UI 不需启动：直接 service 层调用即可

### 8.4 手动验收（落盘 + 跑通后）

1. 桌面端跑 `python -m app.main`
2. 在 ntfy.sh 浏览器订阅 `https://ntfy.sh/andy-soloist-xK9pQ2`（或安卓装 ntfy APK）
3. 点签到 → 浏览器/手机 1 秒内收到 `上午签到 HH:MM ✨ 正常`
4. 关 Wi-Fi → 点签退 → 重开网 → 重启 APP → 收到补发
5. 设置页关掉开关 → 再签到 → 不收到

---

## 9. 未来扩展（不属于本任务）

- v2：推送附带照片（ntfy attach via PUT body）
- v3：多渠道（企业微信 / Bark / 邮件），抽象 `PushChannel` 接口
- v3：自建服务器中转（合并 `sync_service` 逻辑），统一管理多设备订阅
- 请假 UI 完成后，`ATTENDANCE_JUDGED + status=leave` 推送规则改为「推送」即可生效（仅 1 行改动）

---

## 10. 验收标准（DoD）

- [ ] 桌面端模拟打卡，ntfy.sh 浏览器实时收到文字通知
- [ ] 文本含时段中文 / 时间 / 状态 emoji 与文字
- [ ] 离线时点签到 → 联网重启后补发
- [ ] 设置页开关、topic、测试按钮可用
- [ ] 单元 / 离线 / 集成测试全绿
- [ ] UI 代码无新增、`CheckinService` 无新增
