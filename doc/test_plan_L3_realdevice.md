# L3 真机验证计划

> 目标:在真实安卓手机上验证 **相机拍照 / 相册保存 / ntfy 推送 / 分辨率适配**。
> 链路决策:**GitHub Actions 构建 APK** + **照片/战报存公共 Pictures 目录** + **手动传 APK 装机**。

---

## 现状诊断(为什么不能直接装)

桌面端全程用 mock,真机有 5 个缺口:

| # | 缺口 | 位置 | 后果 |
|---|------|------|------|
| 1 | requirements 缺 `plyer` | buildozer.spec:8 | 相机 ImportError |
| 2 | ntfy 依赖 `requests` 未打包 | buildozer.spec:8 | 推送 ImportError |
| 3 | 无 `android.permissions` + 无运行时请求 | buildozer.spec / 全局 | 相机/网络/存储被拒 |
| 4 | 写死 `DesktopCameraMock`,无平台判断 | main.py:99 | 真机也走桌面模拟 |
| 5 | 战报存 `~/Desktop` | checkin_screen:1015 | 安卓无桌面,保存失败 |

---

## Phase 0 — 让 App 真机就绪(代码/配置)

**全部我来改,改完一次性构建。**

- [ ] **P0-1 buildozer.spec 依赖**:requirements 加 `plyer`;ntfy 改用 `urllib`(stdlib)替代 `requests`,避免 p4a 打包 requests 的坑
- [ ] **P0-2 buildozer.spec 权限**:`android.permissions = INTERNET,CAMERA,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE`
- [ ] **P0-3 平台检测 + 相机选型**:main.py 用 `kivy.utils.platform`,android → `AndroidCameraService`,否则 mock
- [ ] **P0-4 运行时权限**:android 启动时 `request_permissions([CAMERA, WRITE/READ_EXTERNAL_STORAGE])`
- [ ] **P0-5 保存路径按平台分流**:新增 `app/utils/storage.py` 统一"图片保存根目录"——android 返回公共 Pictures 路径,桌面返回 Desktop。战报导出 + 相机照片都走它
- [ ] **P0-6 ntfy urllib 化**:`_send_one` 默认实现改 `urllib.request`(保留 `http_post` 注入口,测试不受影响)
- [ ] **P0-7 回归**:全量 pytest 必须仍全绿(桌面路径不被破坏)

> 相册可见性(MediaScanner 是否索引)受安卓版本影响,先按"存公共 Pictures + 触发媒体扫描"实现,**真机首测后按实际表现微调**。

---

## Phase 1 — 构建 APK(GitHub Actions)

- [ ] P0 改动 commit(**先征求你同意再 push**,push 是外发动作)
- [ ] push master → Actions 自动跑 `build-apk.yml`(buildozer android debug)
- [ ] 等约 30–45 分钟,Actions 页面 → 最新 run → Artifacts → 下载 `soloist-carbin-apk`
- [ ] 解压得到 `*.apk`

**首次构建风险**:p4a 拉 SDK/NDK + 编译,可能因 recipe/依赖失败。失败则看 Actions 日志逐项排查,可能要迭代 1–2 次。

---

## Phase 2 — 装机

- [ ] APK 传手机(微信文件传输助手 / QQ / U盘)
- [ ] 手机设置允许"安装未知应用"(对应来源 App)
- [ ] 点开 APK 安装 → 启动

---

## Phase 3 — 真机测试矩阵(我指挥,你操作+反馈截图)

### A. 启动 & 分辨率
- [ ] App 正常启动不闪退
- [ ] 三时段卡片 / 底部状态栏 / 战报 在真机分辨率下不错位、不溢出、字体可读
- [ ] 竖屏锁定,导航栏不被系统手势条遮挡

### B. 相机拍照
- [ ] 首次拍照弹权限请求 → 允许
- [ ] 调起系统相机 → 拍照 → 回到 App
- [ ] 照片落到 Pictures 目录,签到记录带上照片

### C. 相册/文件保存
- [ ] 战报"保存"→ 文件落到公共 Pictures
- [ ] 文件管理器 / 相册能看到照片与战报图

### D. ntfy 推送
- [x] ~~手机 ntfy app 订阅 topic~~(已装,桌面推送已验证收到)
- [ ] 真机 App 内推送到达(关键:验证 urllib 在安卓上 POST 成功)
- [ ] 签到/签退/旷工 → 对应中文推送到达

### E. 时钟(真机用真实系统时钟)
- [ ] 开发面板默认隐藏,生产走 SystemClock
- [ ] 当天日期/时段判定与手机系统时间一致

---

## 你需要准备

- 安卓手机:Android 7.0+(API 24+)、arm64
- 传 APK 的途径 + 允许未知来源安装
- 手机装 ntfy app + 想一个 topic 名 + 手机能上网
- 排错升级:若需看崩溃日志,再加 USB 线走 `adb logcat`(手动装机看不到日志)

---

## 备注

- 每轮真机测试若往库里写了数据,回桌面后我会照例清测试记录
- 此为 debug APK(未签名正式版),仅自用 sideload
