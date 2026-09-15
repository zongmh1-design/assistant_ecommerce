# 开发阶段与进度

## 状态说明

- `已完成`：满足本阶段文档或功能验收条件。
- `待开始`：尚未开发。
- 每完成一个阶段必须停止、汇报并等待下一条指令。

## Phase 0：项目初始化（已完成）

**目标**：建立最小仓库结构，明确范围、业务流程、数据模型分批、单体架构、AI 边界和开发顺序。

**涉及模块**：仓库基础、项目文档、环境变量示例。

**验收条件**：

- 根目录包含 `README.md`、`.gitignore`、`.env.example`。
- 六份核心设计文档内容与需求一致，Mock 和合规边界明确。
- 不存在 API、ORM、数据库迁移、前端或真实 AI 调用。
- 仓库中没有 API Key、密码、Token 或本地隐私配置。

## Phase 1：认证 + 用户权限（已完成）

**目标**：完成登录、当前用户识别、角色权限和用户状态的最小闭环。

**涉及模块**：`User`、认证 API、密码哈希、访问令牌、角色校验、用户管理的最小能力。

**验收条件**：已实现 FastAPI 启动入口、配置、SQLAlchemy、Alembic、`users` 表、Argon2 密码哈希、JWT 登录、`/auth/me` 和统一角色依赖。管理员、运营人员、查看人员的允许/拒绝路径已通过 HTTP 测试；禁用用户不能登录；不保存或返回明文密码。

**验证记录**：pytest 12 项通过；Alembic 已用 PostgreSQL 方言离线生成从空库创建 `users` 表的 SQL。当前机器未配置可用 PostgreSQL 客户端和测试库，因此真实 PostgreSQL 迁移需要按 README 在本地数据库执行。

## Phase 2A：店铺 + 商品（已完成）

**目标**：创建和查询店铺、商品，建立清晰的 `Store 1:N Product` 关系。

**涉及模块**：`Store`、`Product`、商品状态、分页与简单筛选、店铺和商品 API。`PlatformAccount` 不在 Phase 2A 实现。

**验收条件**：admin/operator 可创建和修改，viewer 只读；Product 必须关联已存在 Store；状态只允许 `draft/active/inactive`；金额使用 Decimal/NUMERIC；分页、`store_id/platform/status` 筛选、PATCH 空值语义、越权和 404 均有测试。

**验证记录**：完整 pytest 37 项通过，包含 Phase 1 回归；第二份 Alembic migration 使用 PostgreSQL 方言离线生成 SQL 并检查。当前机器没有可用 PostgreSQL 客户端和测试库，尚未执行真实 PostgreSQL `alembic upgrade head`。

## Phase 2B（原计划 Phase 3）：SKU + 库存（已完成）

**目标**：维护 SKU、库存汇总、库存预警和不可丢失的库存流水。

**涉及模块**：`ProductSku`、`InventoryItem`、`InventoryMovement`、库存调整 Service。

**验收条件**：一个商品可有多个 SKU，编码在商品内唯一；创建 SKU 自动生成零库存和 initial 流水；库存调整和流水在同一事务中完成；不能出现非法负库存或锁定量；viewer 只读；正常、异常、分页、权限和事务回滚均有测试。

**验证记录**：完整 pytest 56 项通过，包含 Phase 1 和 Phase 2A 回归；第三份迁移已用 PostgreSQL 方言离线生成 SQL。当前机器没有 PostgreSQL 服务或 `psql`，尚未执行真实 PostgreSQL `alembic upgrade head`。

## Phase 3A（原计划 Phase 4）：竞品 + 公开链接解析（已完成）

**目标**：完成竞品手工管理，并通过可替换 Parser 接口生成公开链接解析预览，经人工确认后进入正式竞品数据。

**涉及模块**：`Competitor`、`PublicLinkParseTask`、`PublicLinkParser`、`MockPublicLinkParser`。定时监控及快照不在本阶段。

**验收条件**：竞品必须关联商品；可手工增改查；Mock 解析支持确定成功与失败；结果明确标记为演示数据；成功结果需人工确认；重复确认和事务回滚有测试；不包含真实爬虫、账号、Cookie、验证码或风控绕过逻辑。

**验证记录**：完整 pytest 71 项通过，包含此前阶段回归；第四份迁移已用 PostgreSQL 方言离线生成 SQL。当前机器没有 PostgreSQL 服务或 `psql`，尚未执行真实 PostgreSQL `alembic upgrade head`。

## Phase 5：商品诊断（待开始）

**目标**：基于商品、SKU 和竞品生成可编辑的结构化诊断。

**涉及模块**：`ProductDiagnosis`、诊断 Schema、诊断 Service、Mock AI Provider。

**验收条件**：输出包含定位、价格带、人群、痛点、卖点、风险和建议；Schema 校验有效；用户可编辑保存；输入不足、格式异常和调用失败有测试。

## Phase 6：主图方案 + 视频脚本（待开始）

**目标**：用统一 `CreativePlan` 管理两类结构化创意方案。

**涉及模块**：`CreativePlan`、主图和视频输出 Schema、方案状态、Mock AI Provider。

**验收条件**：每类至少生成 3 个方案；用户可编辑；状态支持 `draft/selected/archived`；两类方案共享业务对象但 Schema 清晰；异常输出有测试。

## Phase 7：异步生成任务（待开始）

**目标**：实现不阻塞普通 API 的图片/视频生成任务状态机。

**涉及模块**：`GenerationJob`、`GenerationJobEvent`、Job Service、Worker / Executor、Mock Generator。

**验收条件**：支持 `pending/running/succeeded/failed/cancelled/timeout`；Mock 可演示成功与失败；重试、取消、超时和重复任务有测试；事件时间线完整。

## Phase 8：素材库（待开始）

**目标**：保存生成素材并完成人工审核、版本和使用信息管理。

**涉及模块**：`GeneratedAsset`、素材查询、审核状态、版本、评分、标签和备注。

**验收条件**：成功任务可产生素材；素材可追溯到商品、方案和任务；AI 生成不自动等于可用；人工审核和权限有测试。

## Phase 9：推广 + 投放建议（待开始）

**目标**：完成追踪链接、结构化投放建议、人工确认和实验计划管理。

**涉及模块**：`PromotionLink`、`PromotionLinkClick`、`AdRecommendation`、`AdExperiment`。

**验收条件**：追踪码可记录点击；建议可编辑；必须人工确认或驳回；只有已确认建议可进入实验计划；不连接真实广告平台；权限和状态迁移有测试。

## Phase 10：经营数据（待开始）

**目标**：支持手工录入和 CSV / Excel 导入经营指标。

**涉及模块**：`PerformanceRecord`、导入模板、字段映射、预览、逐行校验和导入结果。

**验收条件**：支持核心八项指标；派生指标有一致计算规则；导入先预览后确认；错误行含原因；一行失败不阻断其他合法行；重复和边界数据有测试。

## Phase 11：经营分析报告（待开始）

**目标**：基于可追溯输入生成可编辑的结构化经营分析和下一轮动作。

**涉及模块**：`ReviewReport`、报告 Schema、确定性指标计算、报告 Service、Mock/真实 AI Provider。

**验收条件**：包含周期摘要、核心发现、问题判断和下一步动作；保留输入数据或稳定引用；用户可修改；输入不足和 AI 异常有测试；可回到下一轮诊断或方案优化。

## Phase 12：完整演示和部署（待开始）

**目标**：串联完整单品流程，补齐可重复演示、接口说明和部署文档。

**涉及模块**：前端整合、演示数据、数据库初始化/迁移、接口文档、导入模板、运行与部署说明。

**验收条件**：新环境可按文档启动；不同角色可演示权限；一条商品从建档到报告完整跑通；真实/Mock/未实现能力标识准确；不含敏感信息；部署仅在负责人明确确认后执行。

## 建议的第一个开发任务

进入 Phase 1 前，先确认 Python 版本、依赖管理方式、Web 框架、ORM、数据库和认证方式。确认后只实现“最小认证骨架 + `User` 表 + 三角色权限测试”，不要同时开发店铺或商品。
