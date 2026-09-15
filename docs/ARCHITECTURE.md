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
                 Worker / Executor
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
        Result / Asset       Error / Retry / Timeout
              │                     │
              └────> Job Event <────┘
```

- API 创建任务后立即返回任务标识，不等待图片或视频生成完成。
- Worker / Executor 领取任务并更新 `running`，完成后写入结果和素材，失败时保存原因。
- 每个重要状态变化写入 `GenerationJobEvent`。
- 第一版不预设分布式队列。可以从数据库任务表加同进程/独立进程执行器开始；达到真实并发需求后再评估专用队列。
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
  jobs/            # 任务执行和状态迁移
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

## 7. 第一版部署边界

Phase 12 之前不部署生产环境。最终演示可以采用前端、单体后端、关系型数据库和一个任务执行进程的简单组合；具体运行方式在实际代码和依赖明确后记录，不提前引入容器编排。
