# 广告素材自动化处理系统 MVP 架构

## 1. 总体结构

采用 Python 模块化单体。FastAPI 提供 API 和静态控制台；SQLite 保存业务元数据；本地文件系统保存原始素材和产物；任务执行器在进程内运行 FFmpeg。外部平台通过适配器隔离，后续可替换为真实 OpenAPI 实现。

```text
Web 控制台
    |
FastAPI API ── 服务层 ── SQLite
    |              |
SPI 回调       任务执行器 ── FFmpeg/ffprobe
    |
PlatformAdapter ── Mock 平台（MVP）
```

## 2. 模块边界

- `config.py`：读取路径、大小限制、SPI 密钥和重试配置。
- `db.py` / `models.py`：SQLite 连接、表结构和事务边界。
- `media/`：文件校验、SHA-256、感知指纹、媒体探测和 FFmpeg 命令构造。
- `services/assets.py`：素材入库、重复判断、元数据查询。
- `services/jobs.py`：任务状态机、步骤执行、重试和事件记录。
- `platforms/base.py`：平台适配器协议和统一结果类型。
- `platforms/mock.py`：本地可预测的上传、状态和回调模拟。
- `services/sync.py`：平台同步、轮询和回调状态归一化。
- `services/alerts.py`：告警创建、查询和确认。
- `api/`：只负责 HTTP 校验、调用服务和响应转换。
- `web/`：展示数据和触发 API，不保存平台密钥。

## 3. 数据模型

核心表为 `assets`、`processing_jobs`、`job_steps`、`platform_bindings`、`events`、`alerts`。所有表使用 UUID 主键和 UTC 时间。`events` 保存不可变的事件记录；当前状态字段只作为查询优化，状态变更必须同时写事件。

## 4. 状态与幂等

任务只允许 `pending → running → succeeded/failed`，失败重试回到 `pending`，超过次数进入 `dead_letter`。平台回调以 `(platform, external_event_id)` 唯一约束去重；素材上传以 SHA-256 做精确重复检测。重复请求返回已有资源，不重复创建副作用。

## 5. 安全与隐私

服务端从环境变量读取平台密钥和 SPI HMAC 密钥；日志对 Authorization、签名和 token 字段脱敏。上传文件名必须经过路径安全处理，文件写入固定数据目录。`.gitignore` 排除数据库、上传目录、产物、日志、缓存和环境文件。

## 6. 当前实现与限制

- 当前为单进程模块化 Demo，任务使用 FastAPI `BackgroundTasks`，SQLite 与本地文件目录不适合多实例生产部署。
- 当前仅实现 `mock` 适配器；SPI 使用 `AD_AUTOMATION_SPI_SECRET` 的 HMAC，默认 `dev-secret` 仅用于本地演示。
- 当前没有登录、权限、多租户、真实投放请求和定时轮询；生产接入前需补齐 Pydantic 契约、鉴权、限流和审计。

## 7. 运行与演示

单机启动命令为 `uvicorn ad_automation.app:app --reload`。启动时创建数据目录和 SQLite 表，健康检查同时报告数据库、数据目录和 FFmpeg 可用性。演示脚本使用 mock 平台，不发起任何外部投放请求。

## 8. 演进路径

阶段一（当前）：素材处理、Mock 同步、SPI 幂等和告警演示。

阶段二（接入稳定性）：Pydantic 请求模型、重试退避、事件审计、平台超时监控和巨量/快手官方适配器测试。

阶段三（生产化）：Redis 队列与独立 worker、PostgreSQL、对象存储、鉴权与租户隔离、可观测性和部署流水线。
