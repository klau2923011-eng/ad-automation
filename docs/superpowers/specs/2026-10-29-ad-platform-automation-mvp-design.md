# 广告素材自动化处理系统 MVP 设计

## 目标

新增一个独立的广告素材自动化系统，先提供可在单机运行的 MVP。系统覆盖素材入库、视频批处理、素材状态管理、投放平台同步、SPI 回调和异常记录；巨量引擎与快手的真实字段映射在取得官方文档和测试凭证后实现，MVP 使用模拟平台验证接口契约。

## 范围

一期包含：

- 素材上传、元数据、文件哈希和基础感知指纹。
- FFmpeg 驱动的视频处理任务：片段裁切/排序、角标或字幕、编码参数和画质增强参数。
- 任务状态机、失败重试、结构化事件日志和异常记录。
- 统一 `PlatformAdapter` 接口，以及可配置的模拟平台适配器。
- 平台素材上传、状态查询、数据同步和 SPI 回调幂等处理。
- 本地 Web 控制台：素材库、处理任务、平台状态、异常中心。

一期不包含：公网生产部署、用户登录和权限、多租户、自动规避平台审核或去重策略、真实平台凭证和未经文档验证的接口字段。

## 架构

采用 Python 模块化单体：FastAPI 提供 HTTP API 和静态控制台；SQLite 保存素材、任务、平台同步和告警元数据；本地目录保存原始素材与处理产物；本地任务执行器运行 FFmpeg。队列执行器以接口形式隔离，后续可替换为 Redis/Celery 或其他异步队列，不改变 API 契约。

建议目录：

```text
ad_automation/
  app.py                 # FastAPI 入口
  config.py              # 环境变量和路径配置
  db.py                  # SQLite 初始化与会话
  models.py              # 素材、任务、事件、告警模型
  schemas.py             # API 数据结构
  api/                   # HTTP/SPI 路由
  services/              # 素材、任务、同步、告警服务
  platforms/             # PlatformAdapter 与 mock/真实适配器
  media/                 # 指纹和 FFmpeg 工作流
  web/                   # MVP 控制台
  tests/
```

## 数据流

1. 上传接口校验扩展名和大小，将文件写入原始素材目录，计算 SHA-256 与感知指纹并创建 `asset`。
2. 创建处理任务时保存有序步骤和参数，状态由 `pending` 进入 `running`、`succeeded` 或 `failed`。
3. 处理器为每个步骤生成可审计的 FFmpeg 命令，产物写入任务目录并创建新的素材版本；重复指纹只标记为 `duplicate`，不删除文件。
4. 同步服务通过 `PlatformAdapter` 上传产物，保存平台素材 ID 和原始响应，随后按退避策略轮询状态。
5. SPI 回调先用事件 ID/平台事件键做幂等去重，再映射到内部状态并记录原始 payload。
6. 异常规则根据任务失败、平台审核失败、同步超时和回调签名错误创建告警；告警可确认但不删除原始事件。

## 关键接口

- `POST /api/assets`：上传素材并返回素材 ID、指纹和状态。
- `GET /api/assets`：分页查询素材，可按状态、平台和重复标记过滤。
- `POST /api/jobs`：创建批处理任务，参数包含素材 ID、步骤列表和输出配置。
- `GET /api/jobs`、`GET /api/jobs/{id}`：查询任务和步骤日志。
- `POST /api/jobs/{id}/retry`：对失败任务重新排队。
- `POST /api/platforms/{platform}/sync`：同步指定素材或任务产物。
- `POST /api/spi/{platform}`：接收平台回调，验证签名并幂等入库。
- `GET /api/alerts`、`POST /api/alerts/{id}/ack`：查询和确认告警。
- `GET /api/health`：检查数据库、素材目录和 FFmpeg 可用性。

## 平台适配器契约

```python
class PlatformAdapter(Protocol):
    def upload_asset(self, asset: Asset) -> UploadResult: ...
    def get_asset_status(self, remote_id: str) -> RemoteAssetStatus: ...
    def normalize_callback(self, payload: dict, headers: Mapping[str, str]) -> CallbackEvent: ...
    def verify_callback(self, payload: bytes, headers: Mapping[str, str]) -> bool: ...
```

适配器负责平台认证、请求和字段映射；服务层负责重试、幂等、状态机和告警。平台密钥只从环境变量读取，不下发到浏览器。

## 错误处理与可观测性

- 外部请求使用超时、指数退避和最大尝试次数；不可恢复错误进入 `dead_letter` 状态。
- 任务状态迁移受限于显式状态机，非法迁移写入事件并返回 409。
- 所有外部响应、回调摘要、FFmpeg 命令和异常堆栈写入结构化事件日志，敏感字段脱敏。
- SPI 回调使用配置的 HMAC 密钥；重复事件返回成功但不重复改变状态。

## 测试策略

- 单元测试：哈希/感知指纹、任务状态机、重试策略、回调签名、mock 适配器字段归一化。
- API 测试：上传、创建任务、查询状态、重试、回调幂等和告警确认。
- FFmpeg 集成测试：使用仓库内或测试夹具生成的短视频验证命令执行和输出元数据。
- 真实平台接入前，使用录制的官方测试响应覆盖每个平台适配器，不以猜测字段作为验收依据。

## 运行方式

开发环境运行单个 FastAPI 进程，默认使用项目目录下的 SQLite 和 `ad_automation_data/`。需要系统安装 `ffmpeg` 和 `ffprobe`；平台配置、SPI 密钥和存储路径通过环境变量覆盖。生产化前必须补充认证、权限、PostgreSQL、队列、对象存储、HTTPS 和告警渠道。

