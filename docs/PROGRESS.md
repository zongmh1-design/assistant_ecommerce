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

## Phase 4A（原计划 Phase 5）：结构化商品诊断（已完成）

**目标**：基于 Product 和 Competitors 的必要字段构造 AI Context，通过可替换 Provider 生成并保存可编辑的结构化历史诊断。

**涉及模块**：`ProductDiagnosis`、输入 Context、Prompt、`ProductDiagnosisOutput`、`LLMProvider`、`MockLLMProvider`、诊断 Service/API。

**验收条件**：Context 不含内部 ID/时间/技术字段；无竞品仍可生成；输出包含定位、价格带、人群、痛点、卖点、风险和建议；非法输出和 Provider 失败不落库；admin/operator 可生成编辑，viewer 只读；同一商品保留多次历史诊断。

**验证记录**：完整 pytest 88 项通过，包含此前阶段回归；第五份迁移已用 PostgreSQL 方言离线生成 SQL。当前机器没有 PostgreSQL 服务或 `psql`，尚未执行真实 PostgreSQL `alembic upgrade head`。

## Phase 4B：OpenAI-compatible LLM Provider（已完成）

**目标**：不改变商品诊断主流程，通过集中配置在 Mock 与一个真实 OpenAI-compatible Chat API 通道之间切换。

**涉及模块**：Provider 配置工厂、`OpenAICompatibleLLMProvider`、HTTP 超时、有限重试、有限 JSON fence 处理、调用元数据、人工验证脚本。

**验收条件**：Mock/Real 选择明确；真实模式缺失配置或未知类型明确失败且不回退；401/403/400 不重试；timeout、network、429、5xx 有限重试；非法 JSON/Schema 不落库；API Key 不进入日志、测试或 Git；自动测试不访问外网。

**验证记录**：完整 pytest 111 项通过，包含原有 88 项；第六份迁移使用 PostgreSQL 方言离线验证。当前未配置真实 API Key，也没有执行真实网络调用，因此只确认 MockTransport 自动化链路，不声称真实供应商 API 已验证。

## Phase 5（原计划 Phase 6）：主图方案 + 视频脚本（已完成）

**目标**：用统一 `CreativePlan` 管理两类结构化创意方案。

**涉及模块**：`CreativePlan`、白名单 Creative Context、主图和视频 Prompt/输出 Schema、方案编辑与状态、现有 `LLMProvider` 和扩展后的 `MockLLMProvider`。

**验收条件**：每次每类严格生成 3 个独立方案；无诊断时仍可生成；用户可编辑；状态支持 `draft/selected/archived`，同商品同类型最多一个 selected；两类方案共享业务对象但 Schema 清晰；输入快照和 Provider 元数据可追溯；Provider、Schema 和数据库写入失败均不产生部分批次。

**验证记录**：完整 pytest 131 项通过，包含此前 111 项；第七份迁移已纳入检查。当前生成的只是文字主图方向和视频脚本，没有实现真实图片/视频、异步任务或素材库。

## Phase 6（原计划 Phase 7）：生成任务状态流程（已完成）

**目标**：实现创建与执行分离的图片/视频生成任务领域模型；用手工 run 入口演示执行，不引入后台队列。

**涉及模块**：`GenerationJob`、`GenerationJobEvent`、`GenerationJobService`、`MediaGenerator`、Mock Image/Video Generator、超时扫描。

**验收条件**：只有 selected 且类型匹配的方案可创建任务；支持 `pending/running/succeeded/failed/cancelled/timeout`；running 在 Generator 前独立提交；attempts、重试上限、pending 取消和管理员超时扫描明确；状态与 Event 同事务；PostgreSQL 行锁防重复领取；Mock 不访问网络或创建文件。

**验证记录**：完整 pytest 154 项通过，包含此前 131 项；第八份迁移纳入 PostgreSQL 方言离线验证。当前没有后台 Worker、真实媒体模型、文件存储或 GeneratedAsset。

## Phase 7（原计划 Phase 8）：素材库（已完成）

**目标**：将 succeeded Job 的合法结果显式同步为正式素材记录，并完成人工审核、版本和使用信息管理。

**涉及模块**：`GeneratedAsset`、`GeneratedAssetService`、Result Schema、幂等逐 Job sync、素材查询、审核状态、版本、评分、标签和备注。

**验收条件**：只有 succeeded Job 的合法结果能产生素材；素材唯一追溯到商品、方案和任务；坏 Job 不阻塞合法 Job；同步幂等；版本由系统分配并有并发兜底；admin/operator 可同步和审核，viewer 只读；不接对象存储或真实文件。

**验证记录**：完整 pytest 184 项通过，包含此前 154 项；第九份迁移纳入 PostgreSQL 方言离线验证。当前 Asset 仅引用 Mock URL，没有真实图片、视频、上传、缩略图或转码能力。

## Phase 8：推广链接与基础点击统计（已完成）

**目标**：完成推广参数建议、人工创建链接、公开 tracking code 跳转和基础点击统计。

**涉及模块**：`PromotionLink`、`PromotionLinkClick`、`PromotionLinkService`、`PromotionLinkSuggestion`、现有 `LLMProvider`。

**验收条件**：AI 只建议场景和 UTM，不决定 target URL 或 tracking code；tracking code 后端随机生成且唯一；active 公开跳转会在同一事务中写 Click 并原子增加计数；inactive 不跳转；admin/operator 写、viewer 只读；不连接广告平台或第三方短链。

**验证记录**：完整 pytest 208 项通过，包含此前 184 项；第十份迁移已通过 PostgreSQL 方言离线验证。SQLite 验证事务回滚和原子 UPDATE SQL，但不宣称验证 PostgreSQL 真实并发语义。当前没有真实 PostgreSQL 服务可执行在线迁移。

## Phase 9：AI 投放建议与人工确认（已完成）

**目标**：根据现有单品运营数据生成可编辑、可追溯的结构化投放建议，并由人工最终确认或驳回。

**涉及模块**：`AdRecommendation`、白名单 Context、严格 AI 输出 Schema、独立 Prompt、现有 `LLMProvider`、人工编辑与终态决策。

**验收条件**：每次生成新增历史建议；数据不足时不编造指标；预算使用 Decimal 语义；pending 可编辑；confirmed/rejected 为终态；确认人只能来自当前登录用户；admin/operator 写、viewer 只读；不包含广告执行代码或第三方 SDK。

**验证记录**：完整 pytest 226 项通过，包含此前 208 项；第十一份迁移已纳入 PostgreSQL 方言离线检查。当前没有真实 PostgreSQL 服务可执行在线迁移，也没有真实广告平台调用。

## Phase 10：投放实验计划与状态（已完成）

**目标**：从用户明确指定的 confirmed AdRecommendation 生成可编辑 draft 实验，并人工管理后续状态。

**涉及模块**：`AdExperiment`、严格 Context/输出 Schema、Prompt、现有 `LLMProvider`、可选 Asset/Link 绑定、正文编辑与独立状态接口。

**验收条件**：Recommendation 必须 confirmed 且归属商品；Asset/Link 必须 approved/active 且同商品；预算为正 Decimal；初始 draft 且只有 draft 可编辑；状态流转严格；running 只作人工记录；viewer 只读；无广告执行、经营数据或队列。

**验证记录**：完整 pytest 260 项通过，包含此前 226 项；第十二份迁移已纳入 PostgreSQL 方言离线检查。当前没有真实 PostgreSQL 服务可执行在线迁移，也没有广告平台执行能力。

## Phase 11A：经营数据手工录入（已完成）

**目标**：支持手工创建和修改周期经营数据，由系统统一计算 CTR、Conversion Rate 和 ROI。

**涉及模块**：`PerformanceRecord`、Create/Update/Read Schema、Repository、Service、REST API 和第十三份迁移。

**验收条件**：原始指标非负且满足点击/转化上限；周期正向；金额和计算全程 Decimal；`spend=0` 时 ROI 为 NULL；可选关联对象严格归属商品；仅 running/finished Experiment 可录入；admin/operator 写、viewer 只读；修改后重算；不调用 LLM，不读取累计 click_count 作为周期 clicks。

**验证记录**：Phase 11A 专项 pytest 30 项通过，完整 pytest 290 项通过；OpenAPI、编译、pip check、Alembic 单一 head 和 PostgreSQL 方言离线迁移均通过。当前环境没有 psql，未执行真实 PostgreSQL 在线迁移。

## Phase 11B：经营数据文件导入（已完成）

**目标**：支持 CSV / Excel 字段检查、预览、逐行错误反馈和允许部分成功的确认导入。

**涉及模块**：XLSX 模板、专用 CSV/XLSX Parser、Preview/Import Service、行级结果 Schema、multipart API、`openpyxl`。

**验收条件**：模板不包含派生字段；CSV 支持 UTF-8/BOM；XLSX 只读第一张表；Preview 零写入；Import 重新验证并允许部分成功；行号和字段错误清晰；5 MB/1000 行限制；复用 Phase 11A 规则；不使用 pandas、LLM、ImportBatch 或异步任务。

**验证记录**：Phase 11B 专项 pytest 24 项通过，完整 pytest 314 项通过；编译、pip check、OpenAPI multipart、Alembic 单一 head、敏感信息和阶段越界扫描均通过。本阶段没有数据库结构变化，不新增 Migration；当前环境没有 Office/LibreOffice 渲染器，XLSX 已完成 openpyxl 回读与样式结构检查，未做像素级渲染检查。

## Phase 12（原计划 Phase 11）：经营分析报告（已完成）

**目标**：基于可追溯输入生成可编辑的结构化经营分析和下一轮动作。

**涉及模块**：`ReviewReport`、白名单 Review Context、确定性 Decimal 聚合、分组摘要、严格输出 Schema、Prompt、现有 Mock/真实 AI Provider、人工编辑与历史查询。

**验收条件**：只纳入完整落在明确周期内的经营记录；基于原始总量重算 CTR/CVR/ROI；无数据不调用模型；Context 不含敏感点击明细；输出严格校验；失败不落库；同周期保留多份历史；人工可编辑正文但不能改变周期与输入快照；不自动触发下一轮流程。

**验证记录**：Phase 12 专项 pytest 16 项通过，完整 pytest 330 项通过；编译、pip check、59 条 OpenAPI 路径、Alembic 单一 head、PostgreSQL 方言离线迁移、敏感信息与阶段越界扫描均通过。第十四份迁移新增 review_reports，未修改历史迁移；当前环境未执行真实 PostgreSQL 在线迁移或真实 LLM 网络调用。

## Phase 13（原计划 Phase 12）：完整后端演示与运行验收（已完成）

**目标**：串联完整单品流程，补齐可重复 Demo Data、HTTP Smoke、接口演示、新环境 Quick Start 和需求追踪。

**涉及模块**：`DemoDataService`、admin-only Demo API、HTTP-only Smoke 脚本、Sample CSV、`DEMO.md`、`REQUIREMENT_TRACEABILITY.md` 和 README Quick Start。

**验收条件**：从既有管理员登录开始，通过现有 Service 创建完整单品闭环；库存和状态规则不绕过；失败可恢复且重复调用不复制业务图；Smoke 只走 HTTP；文档可用于新环境；Mock/真实/未接入边界清楚；不新增 Migration、业务模块或前端。

**验证记录**：Demo API/HTTP Smoke 专项 pytest 8 项通过，完整 pytest 338 项通过；编译、pip check、60 条 OpenAPI 路径与 16 条关键路径、Alembic 单一 head、PostgreSQL 方言离线迁移、Sample CSV、安全与阶段越界扫描、git diff 检查均通过。本阶段没有数据库结构变化，不新增 Migration；当前环境未执行真实 PostgreSQL HTTP Smoke、真实 LLM/媒体模型调用或生产部署。

## Phase 16：前端工作台（16A～16H）

**目标**：在不增加后端业务的前提下，完成 React 工作台、单品 Workbench、SKU/库存、竞品、诊断、创意、任务、素材、推广、投放、经营数据和复盘报告页面，并完成路由懒加载、生产构建与发布前检查。

**涉及模块**：`frontend/` 下的统一 `apiClient`、AuthContext、路由保护、业务 API 模块、页面和组件；Phase 16H 增加 route-level `React.lazy` / `Suspense`、README/DEMO/需求追踪更新。

**验收条件**：页面继续使用真实后端契约；admin/operator 与 viewer 的写入边界清晰；文件上传、模板下载和公开 tracking 跳转不伪造；外部 LLM/媒体/平台能力保持 Mock；初始构建不再静态包含全部业务页面。

**验证记录**：Phase 16H 前端自动测试保持 72 项；懒加载调整后曾发现登录页测试等待异步 chunk 的时序问题，已将登录入口保留为同步页面，业务页面仍按路由懒加载。当前工作区完成 `npm test`、`npm run lint` 和 `npm run build` 的修复后复跑；真实 Docker PostgreSQL、FastAPI 和浏览器联调受本机 Docker Engine 不可用影响，未声称通过。

## 下一阶段建议

后端和前端核心业务范围已冻结。下一步只应在具备 Docker/PostgreSQL 和可用浏览器环境时执行真实发布验收；不要新增业务模块。
