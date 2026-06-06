# 打卡自拍照片功能 — 设计方案

> 日期: 2026-06-06
> 作者: andy + Claude
> 状态: 已审查 (Open Question 已确认)
> 排期: Wave-camera (在 wave 2 修核心 UI bug 之后, wave 3 mascot 集成之前)

---

## 1. 背景

后端 9 个模块完成 + 三轮测试通过, UI 第一波修复 (wave 1) 完成。此时 andy 指出后端设计漏了一个**核心仪式感功能**: 打卡时调起手机原生相机自拍一张, 作为打卡凭证, 在主界面以及每日战报中显示。

这不是 UI 修复, 是新功能模块。必须以独立的、模块化的方式实现, 不是补丁堆叠。

## 2. 需求确认 (brainstorm 已敲定)

| # | 决策项 | 选择 |
|---|---|---|
| 1 | 拍照频次 | **打卡 + 签退都要拍** — 一天最多 4 张 (morning_in / morning_out / afternoon_in / afternoon_out) |
| 2 | evening 时段是否拍照 | **不拍** — evening 是弹性时段, 不强制 |
| 3 | 平台实现 | **抽象 CameraService 接口** — Android 调原生相机 (plyer.camera Intent), Windows 桌面阶段用 FileChooser mock |
| 4 | 存储模型 | **文件系统 + DB 存 path** — 原图存 `user_data/photos/YYYY-MM-DD/{period}_{action}.jpg`, DB 加 `photo_path` 列 |
| 5 | 主界面显示 | **顶部 4 格相册条** — 横排 4 张缩略图, 已拍亮色、未拍灰格, 点缩略图放大 |
| 6 | 战报显示 | **后端 ReportService 合成进长图** — 不在前端额外加区, 保持长图一体化 (可保存/分享) |
| 7 | 异常规则 | **必须拍才能打卡 (严格模式)** — 用户取消相机、拒绝权限、文件保存失败均不写打卡记录 |

## 3. 数据流

```
PeriodCard "上午上班" onClick
  ↓
CameraService.take_photo(period="morning", action="in")
  ↓ (Android: plyer.camera Intent / Windows: FileChooser mock)
  ↓
返回 path = user_data/photos/2026-06-06/morning_in.jpg
  ↓ (用户取消 → 返回 None → 中止, 不写打卡记录)
  ↓
CheckinService.check_in(date, period, photo_path=path)
  ↓
DB: checkin 表新增一行, photo_path 列写入
  ↓
CheckinScreen.refresh() → 顶部 PeriodPhotoStrip 第 1 格亮起
```

## 4. 模块划分

### 4.1 新增

| 模块 | 路径 | 职责 |
|---|---|---|
| `CameraService` (抽象) | `app/services/camera_service.py` | 定义 `take_photo(period, action) -> Path \| None` 抽象接口 |
| `AndroidCameraService` | `app/services/camera_android.py` | Android 实现 — 调 `plyer.camera` Intent, 保存到 user_data 目录 |
| `DesktopCameraMock` | `app/services/camera_desktop_mock.py` | Windows 实现 — 弹 Kivy FileChooser, 用户选本地图复制到 user_data 目录 |
| `PeriodPhotoStrip` (UI) | `app/ui/components/period_photo_strip.py` | 顶部 4 格相册条 widget; 读 photo_path 显示缩略图, 点击放大 |
| `PhotoPreviewDialog` (UI) | `app/ui/components/photo_preview_dialog.py` | 点击缩略图后的全屏放大 ModalView |

### 4.2 修改

| 模块 | 路径 | 改动 |
|---|---|---|
| `Checkin` (model) | `app/models/checkin.py` | 加字段 `photo_path: str \| None = None` |
| Alembic 迁移 | `app/db/migrations/` | `ALTER TABLE checkin ADD COLUMN photo_path TEXT` |
| `CheckinService.check_in` | `app/services/checkin_service.py:53` | 参数加 `photo_path: str` (严格模式必填) |
| `CheckinService.check_out` | `app/services/checkin_service.py:78` | 同上 |
| `ReportService.generate_report_image` | `app/services/report_service.py` | 合成长图时在顶部添加 4 格相册条 (从 photo_path 读图 → PIL 压缩 + 拼接) |
| `CheckinScreen` | `app/ui/screens/checkin_screen.py` | 日期头下方插入 `PeriodPhotoStrip`; PeriodCard 的"上班/下班"按钮回调改为先调 CameraService 再调 CheckinService |
| `PeriodCard` | `app/ui/components/period_card.py` | 暴露 `on_action(period, action)` 回调, 不再直接调 CheckinService |
| `buildozer.spec` | 项目根 | 添加 `android.permissions = CAMERA, WRITE_EXTERNAL_STORAGE` |

## 5. 接口契约

```python
# app/services/camera_service.py
from abc import ABC, abstractmethod
from pathlib import Path

class CameraService(ABC):
    @abstractmethod
    def take_photo(self, period: str, action: str) -> Path | None:
        """调起相机拍照, 返回图片 path。

        Args:
            period: morning / afternoon
            action: in (上班) / out (下班)

        Returns:
            Path 到保存的图片; None 表示用户取消或失败
        """
        raise NotImplementedError


# app/services/checkin_service.py (修改后)
def check_in(self, date: str, period: str, photo_path: str) -> CheckinResult:
    """打卡 — photo_path 必填 (严格模式)"""
    ...

def check_out(self, date: str, period: str, photo_path: str) -> CheckinResult:
    """签退 — photo_path 必填 (严格模式)"""
    ...
```

### 5.1 调用方伪代码 (CheckinScreen)

```python
def on_period_action(self, period: str, action: str) -> None:
    photo = self._camera_service.take_photo(period, action)
    if photo is None:
        # 用户取消或失败 — 严格模式: 不写打卡记录
        return
    if action == "in":
        self._checkin_service.check_in(self._date_str, period, str(photo))
    else:
        self._checkin_service.check_out(self._date_str, period, str(photo))
    self.refresh()
```

## 6. 异常处理 (严格模式)

| 场景 | 处理 |
|---|---|
| 用户在相机内点取消 | `take_photo` 返回 `None` → 调用方中止, **不写打卡记录** |
| Android 拒绝相机权限 | `take_photo` 抛 `PermissionError` → CheckinScreen 弹 `ConfirmDialog` 提示"未授权相机, 无法打卡" → 不写记录 |
| Windows mock 没选文件 | `take_photo` 返回 `None` → 同上 |
| 文件保存到磁盘失败 (磁盘满 / 权限) | `take_photo` 抛 `IOError` → CheckinScreen 弹错误提示 → 不写记录 |
| photo_path 文件后续被删 / 移走 | `PeriodPhotoStrip` 显示"图片缺失"占位灰格; 不影响打卡有效性 |

## 7. 文件系统组织

```
user_data/
├── photos/
│   ├── 2026-06-06/
│   │   ├── morning_in.jpg
│   │   ├── morning_out.jpg
│   │   ├── afternoon_in.jpg
│   │   └── afternoon_out.jpg
│   ├── 2026-06-07/
│   │   └── ...
│   └── ...
├── soloist.db
└── ...
```

**命名规则**: `{period}_{action}.jpg` — 简单、可读、便于人工备份/排查。

**压缩**: 拍照原图直接保存 (不压缩), 缩略图由 PIL 按需生成 (主界面相册条 64×64, 战报长图 128×128)。

## 7.5 照片生命周期与战报缩略图归档 (andy 关键决策)

照片采用 **"原图临时 + 战报永久缩略图"** 双层归档策略:

| 层 | 位置 | 寿命 | 用途 |
|---|---|---|---|
| 原图 | `user_data/photos/YYYY-MM-DD/*.jpg` | **临时, 用户可手动清理** | 当日主界面相册条放大查看; 战报合成时读取一次 |
| 缩略图 | 嵌入 `ReportService.generate_report_image` 输出的战报长图 PNG | **永久, 跟战报同寿** | 长期查阅当日打卡记录, 即使原图被清, 战报里还能看 |

**关键设计后果**:

1. **photo_path 列允许 NULL**: 用户清掉了原图, `photo_path` 仍指向已不存在的文件 → `PeriodPhotoStrip` 检测文件不存在时显示"已清理"灰格 (不报错)
2. **战报合成必须在原图存在时立即拼图**: `ReportService.generate_report_image` 调用时读 4 张原图压缩到 128×128 写进长图。一旦战报生成完成, 照片就**永久保留**在战报 PNG 里
3. **备份功能不动 photos 目录**: 现有"备份数据"功能只导出 DB + 战报长图 PNG, photos 目录不纳入。备份恢复后主界面相册条全部显示"已清理"灰格, 但战报长图里的缩略图仍可看
4. **不压缩原图**: Android 原生 Intent 拍出来什么质量就存什么。用户负责自己清理空间, app 不强制压缩
5. **首次实现要在 settings 加一项"清理 30 天前照片"** (后续 nice-to-have, 不属本 spec, 但 spec 里要预留接口位置)

## 8. 排期

| Phase | 内容 | 预计 |
|---|---|---|
| **Wave 2** (先) | 系统诊断 wave 1 残留 + 修核心 UI bug (添加任务点不开 / 查看战报弹不出 / 对赌页排版乱 / 弹窗按钮溢出 / 底部 nav 只 1 个 tab) | ~3 天 |
| **Wave-camera** (本 spec) | 实现本文档所有内容 | ~4 天 |
| **Wave 3** | mascot 集成 — 打卡页头/中部、对赌页中部、设置/历史一角、弹窗里, 不同位置用不同形象 | ~3 天 |

每个 Wave 完成后 andy 实测 + 截图 + 决定下一波。

## 9. 不在本 spec 范围

- 照片编辑 / 滤镜 / 美颜
- 多张照片合成 GIF / 视频
- 照片分享到外部 (微信/微博)
- 历史照片浏览界面 (相册主页) — 暂时只能从对应日期的战报点开看
- 云备份 — 现有"备份数据"功能保留, photos 目录是否纳入备份范围? **Open Question #1**

## 10. Open Questions — andy 已确认

1. ❌ **photos 目录不纳入备份**。只备份战报长图 (战报里嵌缩略图作为永久归档, 见 Section 7.5)
2. ❌ **不压缩原图**。Android 拍出来什么质量就存什么; 用户负责自行清理 photos 目录释放空间
3. ⏳ **PeriodCard 单/双按钮 UI 现状** — 留到 wave-camera plan 阶段查清, 不阻塞 spec

---

## 11. 验收标准

- 在 Windows 桌面 (FileChooser mock) 走完整流程: 点 4 次"打卡/签退" → 4 张图保存 → 主界面相册条 4 格亮起 → 点 "结束今日并查看战报" → 长图内含 4 张照片
- 在 Android 设备 (APK) 同样流程: 调起原生相机 → 拍照 → 保存 → UI 显示
- 用户取消相机 → 不写打卡记录, 主界面相册格保持灰色
- 用户拒绝相机权限 → 友好提示
- 单元测试覆盖 CameraService 抽象 + AndroidCameraService 与 DesktopCameraMock 的 mock 测试
- E2E 测试: PeriodCard 点击 → CameraService → CheckinService → DB 持久化 → UI 刷新
