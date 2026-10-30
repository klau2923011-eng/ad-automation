# 广告素材自动化 MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `executing-plans` to implement this plan task-by-task with review checkpoints.

**Goal:** 构建一个可本地运行的广告素材处理与模拟投放平台演示系统。

**Architecture:** Python 模块化单体，FastAPI + SQLite + 本地文件系统，进程内任务执行器调用 FFmpeg；平台通过 `PlatformAdapter` 与 mock 实现隔离。

**Tech Stack:** Python 3.11+、FastAPI、Pydantic、SQLAlchemy、SQLite、pytest、FFmpeg/ffprobe。

**Spec:** `docs/requirements/ad-automation-mvp-requirements.md`；架构：`docs/architecture/ad-automation-mvp-architecture.md`。

## 全局约束

- 本阶段只做本地可运行 DEMO，不接入真实投放平台。
- 不上传视频、数据库、日志、密钥、缓存或本地环境文件。
- 每个新行为先写失败测试，确认测试按预期失败，再写最小实现。
- 每个阶段独立验证并单独提交；未经测试和检查不得合并主分支。
- SQLite 和素材文件均写入 `ad_automation_data/`，并由 `.gitignore` 排除。

## 文件结构

```text
ad_automation/
  app.py
  config.py
  db.py
  models.py
  schemas.py
  api/{assets,jobs,platforms,spi,alerts}.py
  services/{assets,jobs,sync,alerts}.py
  platforms/{base,mock}.py
  media/{fingerprint,probe,ffmpeg}.py
  web/{index.html,app.js,styles.css}
tests/
  conftest.py
  test_health.py
  test_assets.py
  test_jobs.py
  test_platforms.py
  test_spi.py
  test_alerts.py
requirements.txt
README.md
```

## 阶段一：项目骨架与健康检查

交付：可启动的 FastAPI 应用、配置/数据库边界、运行依赖、健康检查与测试夹具。

### Task 1：依赖与包骨架

**文件：** 新建 `requirements.txt`、`ad_automation/__init__.py`、`ad_automation/config.py`、`tests/__init__.py`、`tests/conftest.py`。

- [ ] 写配置测试：临时数据目录可通过 `AD_AUTOMATION_DATA_DIR` 覆盖，未设置时落在项目运行数据目录。
- [ ] 运行 `pytest tests/test_health.py -q`，先确认缺少模块/配置的预期失败。
- [ ] 加入 FastAPI、uvicorn、SQLAlchemy、python-multipart、pytest、httpx 依赖和配置对象。
- [ ] 重跑测试，验证临时目录设置与目录创建。
- [ ] 提交仅包含依赖、配置和测试相关文件。

### Task 2：数据库与健康检查

**文件：** 新建 `ad_automation/db.py`、`ad_automation/app.py`、`tests/test_health.py`。

- [ ] 写 API 测试，要求 `GET /api/health` 返回 `ready`、`database`、`ffmpeg` 字段，且创建 SQLite 文件于临时目录。
- [ ] 确认测试因应用入口和健康路由不存在而失败。
- [ ] 实现应用工厂、SQLite 初始化和 FFmpeg/ffprobe 可用性探测。
- [ ] 运行 `pytest tests/test_health.py -q`，验证 HTTP 状态和 JSON 字段。
- [ ] 阶段验收：`uvicorn ad_automation.app:app` 可启动且健康检查可访问；提交本任务文件。

## 阶段二：素材入库与指纹

交付：安全上传、哈希/感知指纹、视频元数据探测、重复标记和素材查询。

### Task 3：素材模型和指纹

**文件：** 新建 `ad_automation/models.py`、`ad_automation/media/fingerprint.py`、`tests/test_assets.py`；修改 `db.py`。

- [ ] 测试 SHA-256 对相同字节稳定、感知指纹对相同图片帧相同。
- [ ] 先运行测试确认 fingerprint 模块缺失。
- [ ] 增加 Asset 表和流式 SHA-256；视频帧指纹通过 ffmpeg 抽取缩略帧后使用 Pillow 感知哈希，FFmpeg 缺失时报告明确错误。
- [ ] 使用生成的像素夹具测试相同与明显不同帧，不提交真实素材。
- [ ] 运行 `pytest tests/test_assets.py -q` 并提交模型/指纹相关文件。

### Task 4：上传和素材查询 API

**文件：** 新建 `ad_automation/schemas.py`、`ad_automation/media/probe.py`、`ad_automation/services/assets.py`、`ad_automation/api/assets.py`；修改 `app.py` 和 `tests/test_assets.py`。

- [ ] 写 API 测试：拒绝非视频扩展名、空文件和超限文件；接收有效测试视频；重复 SHA-256 标记 duplicate；列表和详情返回元数据。
- [ ] 确认测试在素材 API 未注册时失败。
- [ ] 实现扩展名/大小校验、随机安全文件名、ffprobe 元数据、SHA-256 和 SQLite 事务。
- [ ] 加入固定测试视频或由 ffmpeg 在测试中生成短视频；生成物仅存在 pytest 临时目录。
- [ ] 运行 `pytest tests/test_assets.py -q`；阶段验收上传、重复判断、查询都通过后提交。

## 阶段三：处理任务与 FFmpeg

交付：显式状态机、按步骤执行、产物版本、重试和可追溯事件。

### Task 5：任务模型与状态机

**文件：** 新建 `ad_automation/services/jobs.py`、任务/步骤/事件模型、`tests/test_jobs.py`；修改 `models.py`、`db.py`。

- [ ] 测试允许迁移 `pending → running → succeeded/failed`、失败重试回 pending、重试耗尽进入 dead_letter，并拒绝非法迁移。
- [ ] 运行测试确认状态迁移服务缺失。
- [ ] 实现状态转换表、最大 3 次重试及不可变事件记录。
- [ ] 运行 `pytest tests/test_jobs.py -q` 并提交领域状态逻辑。

### Task 6：FFmpeg 工作流与任务 API

**文件：** 新建 `ad_automation/media/ffmpeg.py`、`ad_automation/api/jobs.py`、`tests/test_jobs.py`；修改 `app.py`、`schemas.py`、`services/jobs.py`。

- [ ] 测试创建任务、按序裁切/编码、查询进度和步骤日志、失败后重试。
- [ ] 确认测试因 jobs 路由或处理器不存在而失败。
- [ ] 实现参数白名单和命令参数数组（不拼接 shell 字符串），裁切与编码处理器，输出写入任务专属目录。
- [ ] 真实调用 ffprobe 验证输出文件时长/编码；FFmpeg 不可用时任务明确失败并记录事件。
- [ ] 运行 `pytest tests/test_jobs.py -q`；阶段验收成功产物可被 ffprobe 读取后提交。

## 阶段四：Mock 平台与 SPI

交付：平台协议、mock 上传状态流转、HMAC 验证、回调幂等和状态同步。

### Task 7：平台契约和 Mock 适配器

**文件：** 新建 `ad_automation/platforms/base.py`、`ad_automation/platforms/mock.py`、`ad_automation/services/sync.py`、`tests/test_platforms.py`。

- [ ] 测试 mock 上传产生稳定格式 remote ID，状态查询能够返回统一状态对象。
- [ ] 确认适配器类型和服务缺失导致失败。
- [ ] 定义 `PlatformAdapter.upload_asset()`、`get_asset_status()`、`verify_callback()`、`normalize_callback()` 协议与结果 schema。
- [ ] 实现纯本地 mock 行为，不发送网络请求；测试上传、待审核、通过、拒绝状态转换。
- [ ] 运行 `pytest tests/test_platforms.py -q` 并提交平台边界和 mock 实现。

### Task 8：同步 API 与 SPI 回调

**文件：** 新建 `ad_automation/api/platforms.py`、`ad_automation/api/spi.py`、平台绑定模型和 `tests/test_spi.py`；修改 `app.py`、`services/sync.py`。

- [ ] 测试手动同步返回绑定记录；正确 HMAC 回调修改状态；重复 event ID 不重复改变状态；错误签名返回 401。
- [ ] 确认 API 未注册时测试失败。
- [ ] 对原始 request bytes 计算 HMAC-SHA256，使用 `hmac.compare_digest` 校验；用 `(platform, external_event_id)` 唯一约束保证幂等。
- [ ] 日志保存脱敏 payload；禁止把密钥或签名写入返回 JSON。
- [ ] 运行 `pytest tests/test_platforms.py tests/test_spi.py -q`；阶段通过后提交。

## 阶段五：告警与控制台

交付：告警生命周期和可视化演示工作台。

### Task 9：告警 API

**文件：** 新建 `ad_automation/services/alerts.py`、`ad_automation/api/alerts.py`、`tests/test_alerts.py`；修改任务、同步失败路径。

- [ ] 测试失败任务、平台拒绝和无效签名产生告警；列表可查询；确认后状态变为 acknowledged 且事件仍在。
- [ ] 确认 alert 路由和服务缺失时测试失败。
- [ ] 实现告警唯一关联键、防重复创建、列表筛选和确认时间记录。
- [ ] 运行 `pytest tests/test_alerts.py -q` 并提交告警功能。

### Task 10：Web 控制台

**文件：** 新建 `ad_automation/web/index.html`、`app.js`、`styles.css`；修改 `app.py`；新增 `tests/test_web.py`。

- [ ] 测试根路径返回控制台；静态资源可访问；视图能渲染素材、任务、平台、告警 API 数据。
- [ ] 确认静态资源未挂载时测试失败。
- [ ] 实现四个视图、上传/创建处理任务/同步/mock 回调/告警确认交互，以及加载、空、错误状态。
- [ ] 用浏览器检查桌面和窄屏主流程、控制台无 JS 错误。
- [ ] 阶段验收可从页面完成一条完整模拟链路后提交前端文件。

## 阶段六：演示与发布前检查

交付：清晰运行说明、配置模板、端到端演示流程和干净提交。

### Task 11：启动说明与端到端验收

**文件：** 修改 `README.md`；新建 `.env.example` 和端到端测试。

- [ ] 写端到端测试执行上传 → 创建处理任务 → mock 同步 → SPI 回调 → 告警查询。
- [ ] 先运行确认当前完整链路缺少相应接口。
- [ ] 补齐 README 的 Python/FFmpeg 前置条件、安装、启动、演示、测试和数据目录清理说明；`.env.example` 仅放非敏感占位值。
- [ ] 从干净临时目录按 README 启动并运行全部 `pytest -q`。
- [ ] 检查 `git diff --check`、`git status --short --ignored` 和待提交文件名；仅暂存产品源码、测试、文档和依赖文件。
- [ ] 完成阶段提交并推送功能分支；提交主分支前逐阶段复核测试和隐私排除规则。

## 阶段验收顺序

1. 阶段一：健康检查可用。
2. 阶段二：素材安全入库和重复识别可用。
3. 阶段三：短视频处理可产出并验证。
4. 阶段四：mock 同步与 SPI 状态流转可用。
5. 阶段五：告警和控制台主流程可用。
6. 阶段六：干净环境可按文档复现 DEMO，所有测试通过且无隐私文件入库。

## 分支与合并规则

- 开发分支：`feature/mvp`。
- 每个阶段完成后提交独立 commit，并推送到远程同名分支。当前网络不可达时保留本地提交，网络恢复后补推。
- 不直接在 `main` 编码；主分支只合入已测试、隐私检查通过的阶段结果。
- 合并前运行全量测试、`git diff --check`、检查暂存与忽略文件，并查看阶段差异。
