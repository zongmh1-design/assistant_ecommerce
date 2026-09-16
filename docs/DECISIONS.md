# 技术与业务决定

本文件记录已经确认、会影响后续实现的重要决定。未确认事项不得写成既定事实。

## 已确认

### D-001：第一版采用简单单体架构

- **状态**：已确认
- **原因**：项目强调业务清晰、可运行、可演示和本人可解释。
- **结果**：采用 `API → Service → Repository → Database` 分层；AI 与外部平台通过接口适配；不引入微服务。

### D-002：按阶段创建数据库表和代码模块

- **状态**：已确认
- **原因**：一次性建立全部表会增加理解和修改成本，也无法逐阶段验证业务。
- **结果**：表分四批设计，并在对应 Phase 到来时才创建 ORM 和迁移。

### D-003：第一版以单个商品闭环为主线

- **状态**：已确认
- **原因**：确保核心运营过程可以完整演示。
- **结果**：`Product` 是诊断、方案、任务、素材、投放、经营数据和报告的中心归属对象；`Store 1:N Product` 仍保留自然扩展能力。

### D-004：外部平台能力明确 Mock 或不接入

- **状态**：已确认
- **原因**：优先验证自身业务系统，并遵守授权、安全和平台规则。
- **结果**：真实电商授权、商品 API 使用 Mock；竞品使用手工、Mock 或示例数据；图片/视频生成允许 Mock；广告平台不真实接入。

### D-005：AI 输出结构化且允许人工修改

- **状态**：已确认
- **原因**：业务结果需要校验、保存、追溯和人工负责。
- **结果**：优先使用 Pydantic Schema；模型适配与业务 Service 分离；失败不能伪装成成功内容。

### D-006：Phase 1 后端技术栈

- **状态**：已确认
- **结果**：Python 3.12、venv、pip + `requirements.txt`、FastAPI、SQLAlchemy 2.x、Alembic、PostgreSQL、REST、Pydantic 和 pytest。Phase 1 不开发前端。

### D-007：认证和权限方式

- **状态**：已确认
- **结果**：密码使用 Argon2 安全哈希；登录签发 JWT Bearer Access Token，包含 `user_id`、`role`、`exp`；Phase 1 不实现 Refresh Token。访问时重新读取用户状态和角色，旧 Token 在用户禁用或角色变化后失效。

### D-008：全局数据约定

- **状态**：已确认
- **结果**：数据库主键使用整数自增 ID；时间以带时区 `datetime` 按 UTC 存储；金额使用 Python `Decimal` 和数据库 `NUMERIC/DECIMAL`；第一版不做全局软删除，有历史保留要求时优先使用状态字段。

### D-009：平台字段与 Store 删除边界

- **状态**：已确认
- **原因**：第一版平台集合很小，不值得建立复杂平台系统；商品属于店铺且后续会产生历史数据。
- **结果**：Store/Product 平台使用 Python Enum 和数据库 `VARCHAR + CHECK`，不使用 PostgreSQL 原生 ENUM。新增平台需要新迁移调整 CHECK。`products.store_id` 使用非空外键和 `ON DELETE RESTRICT`，不使用 CASCADE DELETE；Phase 2A 不提供删除接口。

### D-010：库存初始化、停用写入与并发边界

- **状态**：已确认
- **原因**：库存必须同时具备当前状态和可追溯流水，但培训项目暂不需要复杂仓储或并发框架。
- **结果**：创建 SKU 时在同一事务中生成零库存 `InventoryItem` 和 `initial` 流水；库存调整在同一事务中修改库存并新增流水。inactive SKU 允许读历史但禁止库存写入。Phase 2B 不加行锁或乐观锁，因此并发调整仍可能发生 lost update；真实并发出现时优先在 PostgreSQL 库存读取处使用 `SELECT ... FOR UPDATE`，或在需要无锁冲突检测时增加 optimistic locking 版本字段。

### D-011：公开链接解析结果必须人工确认

- **状态**：已确认
- **原因**：公开页面数据可能缺失、过时或解析错误，未经确认写入正式竞品会污染后续商品诊断输入。
- **结果**：`PublicLinkParseTask` 只保存解析预览和错误信息。仅 succeeded 任务可以由 admin/operator 明确确认；确认时以 PostgreSQL 行锁读取任务，创建 `Competitor` 与写入 `confirmed_competitor_id` 在同一事务中完成，避免重复确认。业务 Service 只依赖 `PublicLinkParser` 接口，当前注入不访问网络且明确标记为 `mock_demo` 的实现。

### D-012：诊断采用白名单 Context、Provider 抽象和验证后落库

- **状态**：已确认
- **原因**：直接把 ORM 对象发送给模型会泄露无关技术字段；只依赖模型自报的结构可能让非法输出污染正式业务数据；不保存输入快照又无法解释历史诊断。
- **结果**：使用专用函数将 Product + Competitors 映射为最小 `ProductDiagnosisContext` 并保存快照；Service 只依赖 `LLMProvider`；Provider 结果必须再次通过 `ProductDiagnosisOutput` 后才创建记录。当前集中注入不访问网络的 `MockLLMProvider`，`source_type=mock_ai`，不引入模型注册、Agent、RAG 或重试系统。

### D-013：真实 LLM 使用单一 OpenAI-compatible 通道且不自动降级

- **状态**：已确认
- **原因**：需要以低复杂度验证真实模型调用，同时避免配置错误时静默返回 Mock 结果，让用户误判数据来源。
- **结果**：`LLM_PROVIDER` 只允许 `mock/openai_compatible`，集中工厂选择实现。真实模式使用已有轻量 `httpx2` 客户端，配置明确超时；只对 timeout、临时网络错误、429、5xx 做有限指数退避重试，认证、明确 4xx 和非法输出不重试。配置不完整直接失败，不回退 Mock；不记录 Key、Authorization Header 或完整 Prompt。

### D-014：诊断调用元数据使用两个字段加可空 JSON

- **状态**：已确认
- **原因**：Provider 和模型是稳定、常读的信息，而 Token usage 在兼容 API 中并不总是存在，且字段可能随供应商能力变化。
- **结果**：第六份迁移增加可空 `provider_name`、`model_name` 和 `usage_json`。usage 只接收非负整数的三类标准 Token 字段，不拆表、不做成本计费。

### D-015：主图方向与视频脚本统一为 CreativePlan

- **状态**：已确认
- **原因**：两类结果都属于商品的可编辑文本创意方案，具有相同归属、状态、生成来源和追溯要求；分表会重复 API、Service 和状态逻辑。
- **结果**：使用单表 `creative_plans`，以 `plan_type=main_image/video_script` 区分，类型内容放入受对应 Pydantic Schema 约束的 `content_json`。每次模型调用必须完整得到 3 条后才在一个事务中保存；Provider、模型、可选 usage 和白名单输入 Context 一并保存。`CreativePlan` 不等同于图片或视频素材。

### D-016：CreativePlan 选择唯一且 archived 为终态

- **状态**：已确认
- **原因**：后续生成任务需要一个明确采用的方案，同时保留旧方案历史；第一版无需可逆状态机。
- **结果**：允许 `draft → selected/archived`、`selected → archived`，不允许 `archived → draft`。选择新方案时，同一事务归档同商品同类型的旧 selected；主图和视频互不影响。Service 实行业务规则，数据库使用部分唯一索引兜底并发冲突。

### D-017：Generator 调用前先提交 running 状态

- **状态**：已确认
- **原因**：真实图片或视频调用可能耗时较长。如果 pending、外部调用和终态都放在一个长事务中，其他请求看不到 running，并会长时间占用事务和行锁。
- **结果**：run 的事务 1 通过 PostgreSQL 行锁领取 pending Job，写入 running、attempts、锁字段和 started Event 后 commit；随后在无数据库事务的阶段调用 Generator；事务 2 原子写入 succeeded/failed 与对应 Event。迟到结果在结束前再次锁定并校验 running，不覆盖已经由 sweep 标记的 timeout。

### D-018：Phase 6 只允许取消 pending Job

- **状态**：已确认
- **原因**：当前手工同步执行入口和 Mock Generator 没有真实的中断信号或外部取消 API。把 running 直接标为 cancelled 会造成函数仍在执行而数据库声称已停止。
- **结果**：只允许 `pending → cancelled`。running 返回明确的 `running_job_cancellation_not_supported`；failed/timeout 通过 retry 回到 pending 后才能重新执行。未来真实 Generator 支持 cancellation 时再扩展，不伪造能力。

### D-019：Job result 经过显式校验后才进入素材库

- **状态**：已确认
- **原因**：`GenerationJob.result_json` 是 Generator 的执行输出，可能缺字段、类型错误或与 job_kind 不一致；它也没有审核状态、版本、标签和使用信息，不能直接当作正式业务素材。
- **结果**：通过显式 `/assets/sync` 将 succeeded Job 逐条转换。每条 result 使用对应 Pydantic Schema 校验，合法后才创建 `GeneratedAsset(pending)`；坏结果保留 Job 的 succeeded 历史并返回同步失败详情，不污染素材表，也不阻塞其他 Job。

### D-020：素材同步按 Job 独立事务并由系统分配版本

- **状态**：已确认
- **原因**：批量同步中单个脏结果不应让所有合法素材回滚；客户端分配版本又容易重复或跳号。
- **结果**：每个 Job 独立 commit/rollback，`generation_job_id UNIQUE` 保证幂等。版本按 `product_id + creative_plan_id + asset_type` 递增；同步时锁定 CreativePlan，数据库复合唯一约束最终兜底。SQLite 测试不宣称验证 PostgreSQL 行锁并发语义。

### D-021：推广建议与正式链接分离，tracking code 保持稳定

- **状态**：已确认
- **原因**：LLM 适合建议命名、场景和 UTM，但不应猜测用户最终落地页，也不应承担唯一标识生成。已发布的 tracking code 若因修改 target URL 而变化，会让旧渠道链接失效。
- **结果**：`PromotionLinkSuggestion` 不落库且不包含 target URL/tracking code；用户明确提交只允许 http/https 的目标地址，后端用 `secrets` 生成随机码。修改 target URL 后 tracking code 保持不变，因此旧链接会转向新地址；第一版不做链接版本化。

### D-022：点击明细与原子计数同事务，限制隐私用途

- **状态**：已确认
- **原因**：普通 ORM 读取后加一可能发生 lost update；计数与明细分开提交又会产生永久不一致。IP 和 User-Agent 还涉及生产隐私合规。
- **结果**：每次 active 跳转在同一事务中插入 Click，并执行数据库原子 `click_count = click_count + 1`；失败全部回滚。只保存需求规定的可空原始 IP/User-Agent，不做定位、画像或跨站追踪。真实生产环境应按当地法规与隐私政策决定脱敏和保留周期；SQLite 测试不代表 PostgreSQL 高并发已实测。

### D-023：投放建议终态冻结，人工确认不等于真实投放

- **状态**：已确认
- **原因**：后续实验和复盘需要知道当时采用的原始策略；若 confirmed/rejected 后仍可修改正文，确认记录将失去审计含义。同时培训项目不应伪装拥有广告执行能力。
- **结果**：每次生成创建新的 pending AdRecommendation，只有 pending 可编辑；人工 confirmed/rejected 后正文冻结，若需调整则生成新建议。`confirmed_by` 只能取当前认证用户，确认只是允许未来作为 AdExperiment 输入，不调用平台、不修改预算、不出价、不扣费。

### D-024：实验来源显式选择，running 只表示人工状态

- **状态**：已确认
- **原因**：商品可能保留多轮 confirmed 建议，自动取最新会让实验来源不清；当前系统又没有广告平台和可验证的执行通道，不能把状态变化伪装成真实投放。
- **结果**：生成请求必须明确 recommendation_id，且只接受同商品 confirmed 建议；可选素材/链接需 approved/active。AI 结果从 draft 开始，只有 draft 可编辑，人工按规则推进状态。running/finished 只是运营人员记录外部实验进度，不调用 Campaign、预算、出价或扣费接口。

### D-025：派生经营指标由应用计算并持久化

- **状态**：已确认
- **原因**：CTR、Conversion Rate 和 ROI 必须在创建与修改时保持同一公式；后续 ReviewReport 又需要稳定读取当时保存的历史指标。让客户端提交或在多个层重复计算都会产生口径漂移。
- **结果**：用户只提交原始指标；`PerformanceRecordService.calculate_metrics()` 是唯一计算入口，并将六位小数的 Decimal 派生结果持久化，不使用数据库 Generated Column。`spend=0` 时 ROI 保存 NULL。数据库 CHECK 只做最终完整性兜底。

### D-026：手工经营记录暂不去重，链接累计点击不映射周期点击

- **状态**：已确认
- **原因**：同一商品、实验和周期未来可能存在不同来源或人工修正，当前没有来源字段，过早增加唯一约束会阻止合法记录。PromotionLink.click_count 又是全生命周期累计跳转数，与 PerformanceRecord 的周期指标口径不同。
- **结果**：Phase 11A 不建立经营记录重复唯一约束、不自动覆盖；Phase 11B 再结合导入来源设计重复策略。PerformanceRecord.clicks 必须由用户或未来经过校验的文件导入提供，绝不自动复制 PromotionLink.click_count。

### D-027：PerformanceRecord 文件导入保持无状态

- **状态**：已确认
- **原因**：当前只需要小文件的预览和人工确认，没有跨请求审计、后台执行或统一导入中心需求；提前建立 ImportBatch 会增加表、状态和清理逻辑。
- **结果**：Preview 只解析并调用无写入的业务验证，不保存文件、Preview Token 或临时记录。用户确认后再次上传到 Import，系统重新读取并重新验证，避免依赖过期的关联对象或 Experiment 状态。

### D-028：导入逐行提交且不自动识别重复

- **状态**：已确认
- **原因**：第一版最多 1000 行，逐行事务最容易解释并满足部分成功；现有 PerformanceRecord 又允许同周期保留多条修正或不同来源记录，没有足够字段可靠判断重复。
- **结果**：每个合法行调用 Phase 11A `create()` 并独立 commit，失败只 rollback 当前行。相同文件再次导入允许创建新记录；重复识别留到未来具备来源和修正版本模型时设计。

### D-029：复盘比例必须基于汇总原始指标重算

- **状态**：已确认
- **原因**：各 PerformanceRecord 权重不同，直接平均 CTR/CVR/ROI 会扭曲整体表现。例如 100 展现/10 点击为 10%，10000 展现/100 点击为 1%，算术平均 5.5% 明显不能代表总计 10100 展现/110 点击的实际整体点击率。
- **结果**：ReviewReportService 先汇总曝光、点击、转化、支出和收入，再用统一 Decimal 公式重算 overall CTR/CVR/ROI；`spend=0` 时 ROI 为 NULL。只纳入完整落在请求周期内的记录，跨周期记录不截断并计入 Context 的 `excluded_count`。LLM 只能解释这些确定性数字，不能重算或修改它们。

### D-030：Demo 用固定业务名称恢复，不新增表或长事务

- **状态**：已确认
- **原因**：Demo 需要可重复执行和失败后继续，但当前不需要 Demo 标志字段、Saga、初始化批次表或跨外部调用的长事务。后者会扩大架构并让真实 Provider/Generator 长时间占用数据库事务。
- **结果**：使用固定 `store_name` 和 Demo 对象名称查询当前进度，读取可直接使用 ORM；所有写操作复用已有 Service。每个阶段按原事务提交，失败返回 `completed_steps/failed_step/error_code`，再次调用补齐缺失阶段；完整后返回稳定核心 ID。Demo 不创建用户或默认密码。

## 待确认

- Phase 2 开始前确认商品 URL、图片列表等字段的具体输入边界。
- 前端框架在进入前端开发阶段前确认。
