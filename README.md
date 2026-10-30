# 广告素材自动化系统

本仓库是一个可本地运行的广告素材自动化 MVP，覆盖素材上传、SHA-256 重复检测、媒体探测和后续视频处理扩展。

## 运行

需要 Python 3.11+ 和 FFmpeg/ffprobe。Windows 可通过 `winget install --id Gyan.FFmpeg.Shared` 安装；应用会自动发现 WinGet 安装目录，也可用 `AD_AUTOMATION_FFMPEG` 和 `AD_AUTOMATION_FFPROBE` 指定路径。

```powershell
pip install -r requirements.txt
uvicorn ad_automation.app:app --reload
```

运行数据和上传素材保存在 `ad_automation_data/`，不会提交到 Git。真实巨量引擎与快手接口需要官方文档和测试凭证后再接入。

## 一键演示

演示入口会生成一个本地竖屏测试视频，启动服务并尝试打开浏览器；不会使用或上传个人素材。

```powershell
python -m ad_automation.demo
```

打开后按顺序操作：上传视频 → 选择处理方式 → 处理（任务会在后台运行，界面自动刷新）→ 平台状态 → 同步素材 → 模拟拒绝 → 异常中心 → 确认告警。
