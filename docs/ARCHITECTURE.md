# 系统架构

## 1. 架构结论

第一版采用简单单体架构：一个后端应用、一个关系型数据库、一个前端应用，以及可在同一代码库中运行的任务执行器。按业务阶段逐步增加模块，不使用微服务。

## 2. 后端分层

```text
Client / Frontend
        │
        ▼
       API        请求解析、认证、权限、Schema 校验、响应转换
        │
        ▼
     Service      业务规则、流程编排、事务边界
        │
        ▼
   Repository     数据读写表达，不包含业务判断
        │
        ▼
     Database     关系型持久化
```

核心约束：

- API 不直接操作数据库。
- Repository 不决定“是否允许确认投放”等业务规则。
- 权限入口在 API 层执行，关键业务权限在 Service 再校验，避免绕过。
- 前端只负责展示、表单、状态反馈和触发 API；重要规则留在后端。

## 3. AI 与外部集成

```text
Service ──> AI Provider Interface ──> Mock Provider / Future Real Provider
   │
   └─────> External Integration Interface ──> Mock Adapter / Future Platform Adapter
```

### AI Provider

- Service 准备业务输入并要求明确的结构化输出 Schema。
- Provider 负责模型调用、超时、响应解析和供应商错误转换。
- 第一版可以先使用确定性的 Mock Provider。
- 更换模型供应商时，尽量只增加或替换 Provider，不修改核心业务流程。

### External Integration

- 电商授权、商品 API、竞品数据、图片/视频生成和广告平台均通过适配接口隔离。
- Mock Adapter 必须明确标识，不能让界面或文档误称为真实平台接入。
- 真实适配器只有在获得合法授权和明确需求后才实现。

## 4. 异步任务

```text
API → Job Service → GenerationJob(pending)
                         │
                         ▼
                 Manual Executor
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
          result_json        Error / Retry / Timeout
              │                     │
              └────> Job Event <────┘
```

- API 创建任务后立即返回 pending 任务，不执行图片或视频生成。
- Phase 6 通过显式 run API 充当手工执行入口；未实现后台 Worker 或队列。执行器先提交 `running`，再调用可替换 `MediaGenerator`，最后用第二个事务保存结果或失败。
- 每个重要状态变化写入 `GenerationJobEvent`。
- PostgreSQL 使用 `SELECT ... FOR UPDATE` 防止两个请求同时领取同一 pending Job；SQLite 测试不具备真实 PostgreSQL 行锁语义。
- 第一版不预设分布式队列。达到真实后台执行需求后，再基于现有 Job 状态模型评估独立执行器。
- Mock Generator 也必须走相同任务流程，以验证业务状态机，而不是直接返回“成功”。

## 5. 建议的代码结构

目录随阶段逐步增加，下面是目标结构而不是 Phase 0 立即创建清单：

```text
app/
  api/             # 路由、依赖、请求与响应
  core/            # 配置、数据库连接、安全基础设施
  models/          # 已落地阶段的 ORM Model
  schemas/         # Pydantic 输入输出 Schema
  services/        # 业务规则和用例
  repositories/    # 数据访问
  ai/              # Provider 接口、Mock 与真实适配器
  integrations/    # 外部平台接口与适配器
  generation/      # MediaGenerator 接口、依赖选择和 Mock 实现
tests/              # 与已实现模块同步增加
scripts/            # 必要的初始化或演示脚本
sample_data/        # 非敏感示例数据
docs/               # 项目设计与进度
```

Phase 0 只创建 `app/__init__.py` 和文档。其他目录在出现第一个真实文件时再创建，避免空目录和占位代码。

## 6. 事务与错误边界

- Service 定义一次业务操作的事务边界，例如“调整库存 + 写库存流水”必须原子完成。
- API 将业务异常转换为稳定的 HTTP 错误响应，不把数据库或供应商细节直接暴露给前端。
- AI 和外部平台错误统一转换为应用可理解的错误类型，同时保留脱敏日志。
- 异步任务失败不回滚已经提交的任务记录，而是写入失败状态、原因和事件，允许按规则重试。
- 运行事务不能覆盖外部 Generator 调用：`running + started Event` 先 commit，外部调用结束后再用第二个事务原子保存终态和 Event。

### Job 结果到素材库

```text
Asset Sync API
→ GeneratedAssetService
→ succeeded GenerationJob + result_json
→ Image/Video Result Schema
→ version allocation
→ GeneratedAsset(pending)
→ 人工审核与元数据维护
```

- `GenerationJob` 保存一次执行的状态和原始结构结果；`GeneratedAsset` 保存已经通过业务校验、可审核和可使用的素材记录。
- sync 不挂接在 Job Service 成功分支中，当前由显式 API 触发，避免任务执行和素材库职责耦合。
- 批量 sync 按 Job 独立事务处理；坏数据不会回滚其他合法素材。
- 同方案版本分配使用 PostgreSQL CreativePlan 行锁与数据库唯一约束。当前没有对象存储、文件处理或真实媒体内容。

### 推广链接与公开跳转

```text
Authenticated API → PromotionLinkService → Repository → Database
                         │
                         └→ LLMProvider（只生成 UTM 建议）

Public GET /r/{tracking_code}
→ PromotionLinkService
→ insert PromotionLinkClick + atomic UPDATE click_count
→ one transaction commit
→ 302 Redirect target_url
```

- 建议、创建和跳转共用一个明确 Service，但建议不持久化，最终 target URL 始终由用户控制。
- 原子计数表达式避免典型 read-modify-write lost update；Click insert 和 counter update 共用事务。
- SQLite 自动测试验证 SQL 形态和事务回滚，不能证明 PostgreSQL 的真实高并发调度语义。

### 投放建议与人工决策

```text
API + JWT/write permission
→ AdRecommendationService
→ Product/Diagnosis/CreativePlan/Asset/PromotionLink Repositories
→ whitelist Context → existing LLMProvider → strict Schema
→ AdRecommendation(pending)
→ human edit
→ human confirmed/rejected
```

- Service 只依赖现有 `LLMProvider`，不知道供应商 URL、Key、HTTP 或重试实现。
- 生成只读现有业务数据并写一条历史建议；不依赖广告 SDK，不存在广告执行适配器。
- 编辑和确认通过 `SELECT ... FOR UPDATE` 读取建议，避免并发编辑与最终决策互相覆盖；SQLite 测试不代表 PostgreSQL 行锁并发已实测。
- API 权限依赖提供当前 User，Service 只接受该用户 ID 写入 `confirmed_by`，请求 Schema 禁止伪造确认人。

### 投放实验计划

```text
API → AdExperimentService
    → explicit confirmed AdRecommendation
    → optional approved Asset / active PromotionLink
    → whitelist Context → existing LLMProvider → strict Schema
    → AdExperiment(draft)

Status API → Service transition rules → Database only
```

- 内容编辑与状态变更使用独立接口；Service 通过行锁读取实验，只有 draft 可修改正文。
- 状态 API 只更新领域记录，不调用 External Integration。`running` 是人工声明外部实验开始，不是 Worker 或广告执行事件。
- 不存在 Campaign Service、广告 SDK、定时任务、队列或预算执行模块。

### 经营数据

```text
PerformanceRecord API
→ PerformanceRecordService
    → Product / CreativePlan / GeneratedAsset / PromotionLink / AdExperiment Repository
    → validate period, ownership and experiment state
    → calculate Decimal metrics in one business entry point
→ PerformanceRecordRepository
→ PostgreSQL
```

- Route 不计算指标，Repository 不承载业务公式；Create 和 Update 共用 Service 的 `calculate_metrics()`。
- 数据库保存派生指标用于后续报告稳定读取，同时 CHECK 约束作为绕过 Service 时的最后防线。
- 本模块不依赖 LLMProvider，也不读取 PromotionLink click_count 推导经营 clicks。

### 经营数据文件导入

```text
Upload API
→ PerformanceRecordFileParser
    → CSV stdlib / openpyxl first worksheet
    → header + row number + basic type conversion
→ PerformanceRecordImportService
    → PerformanceRecordCreate
    → PerformanceRecordService.validate_and_prepare() for preview
    → PerformanceRecordService.create() for each imported row
→ row-level response
```

- Parser 不查询数据库、不计算 CTR/CVR/ROI，也不判断对象归属。
- Preview 是无状态只读检查；Import 不信任 Preview，重新解析并重新验证。
- 正式导入每个合法行独立 commit；一行失败会 rollback 该行，不影响已成功或后续合法行。
- 文件限制集中为 5 MB、最多 1000 个非空数据行。没有 ImportBatch、缓存、队列或后台 Worker。

### 经营复盘报告

```text
ReviewReport API
→ ReviewReportService
→ ProductRepository + ReviewReportRepository
→ contained PerformanceRecord rows + excluded overlap count
→ deterministic Decimal aggregation and limited grouping
→ whitelist ReviewReportContext
→ existing LLMProvider
→ strict ReviewReportOutput
→ ReviewReportRepository
→ Database
```

- Repository 只负责周期查询、关联对象预加载和报告读写；Service 负责总量、比率、分组和 AI 错误边界。
- 总指标复用 `PerformanceRecordService.calculate_metrics()`，不在 Route、Prompt 或 LLM 中重复公式。
- 先完成所有确定性汇总，再调用 Provider；无数据、汇总失败或输出非法都不会创建报告。
- `input_context_json` 是生成时快照。后续 PerformanceRecord 修改不改写历史报告，报告人工编辑也不反向修改经营数据。

### Demo 编排与 HTTP Smoke

```text
POST /workspace/demo-data (admin only)
→ DemoDataService
→ existing Store/Product/SKU/Inventory/.../ReviewReport Services
→ committed business stages
→ resumable ID response

scripts.smoke_test_demo_flow
→ login over HTTP
→ POST demo-data
→ query every major object and public redirect over HTTP
→ PASS / failed step
```

- DemoDataService 是薄编排层，不直接写业务 ORM 对象或 SQL；查询固定 Demo 名称用于幂等检测，所有写入继续经过既有 Service 和状态规则。
- 不使用覆盖 LLM/Generator 的长事务。每个现有 Service 按自己的事务边界提交，失败响应保留已完成步骤，再次调用继续补齐。
- Smoke 脚本不导入数据库 Session，不嵌入 SQLite，只验证正在运行的 FastAPI 实例。

## 7. 第一版部署边界

Phase 13 完成的是新环境启动说明、离线迁移验证和后端 HTTP 演示，不等于生产部署。当前仍采用单体 FastAPI + PostgreSQL；未引入前端、容器编排、队列或生产 Worker。
