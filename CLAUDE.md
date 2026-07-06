
## 装机 / 下载 APK(重要 — 一律走阿里云,勿走 GitHub 直连)

- **APK 一律从阿里云 OSS 国内固定链接下载**,禁止从 GitHub Actions artifacts / `gh run download` 直连拉取(走国际线路会卡死:44MB 曾跑 15 分钟零进度)。
- 固定链接:`https://soloist-apk.oss-cn-guangzhou.aliyuncs.com/apk/latest.tar.gz`
  - 是 `.tar.gz`(gzip 外壳绕过阿里云 apk 后缀拦截),下载后 `tar -xzf` 解包即得 `.apk`。
  - 稳健下载:`curl.exe -L --retry 5 --retry-all-errors --fail`,下完 `tar -tzf` 校验完整性。
- 流程:push `master` → GitHub Actions 构建 → 自动覆盖上传该链接。CI `completed` 后等 1–2 分钟 OSS 才更新(否则下到旧包)。
- adb 不在 PATH,全路径:`C:\Users\kistc\AppData\Local\Android\Sdk\platform-tools\adb.exe`。安装:`& $adb install -r <apk>`。
- 完整步骤见 `doc/装机指南.md`。
