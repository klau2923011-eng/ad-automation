# 广告素材自动化系统

本仓库是一个可本地运行的广告素材自动化 MVP，覆盖素材上传、SHA-256 重复检测、媒体探测和后续视频处理扩展。

## 运行

需要 Python 3.11+；视频处理阶段还需要 FFmpeg/ffprobe。

```powershell
pip install -r requirements.txt
uvicorn ad_automation.app:app --reload
```

运行数据和上传素材保存在 `ad_automation_data/`，不会提交到 Git。真实巨量引擎与快手接口需要官方文档和测试凭证后再接入。
