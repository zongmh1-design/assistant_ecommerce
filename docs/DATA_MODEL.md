# 数据模型设计

## 1. 设计原则

- 数据模型按开发阶段逐批实现，不一次性创建全部 ORM Model、迁移或数据库表。
- 表随开发阶段增加，禁止一次性落地全部表。
- `Product` 是单品运营流程的中心对象，运营结果必须能够追溯到具体商品。
- 库存变化必须写入 `InventoryMovement`，不能只覆盖当前库存数字。
- AI 输出保存结构化字段、输入快照或来源信息以及必要的原始输出，支持用户编辑。
- 外部平台凭据不以明文进入数据库。

## 2. 分批落地方案

### 第一批核心表（Phase 1–2）

项目最早阶段必须存在，只支持认证、店铺和商品基础能力。

| 表 | 主要职责 | 主要关系 |
| --- | --- | --- |
| `users` | 登录身份、角色、状态和密码哈希 | 后续作为创建人、确认人等审计主体 |
| `stores` | 店铺基础信息和平台归属 | 一个店铺拥有多个商品 |
| `products` | 商品基础信息、经营属性和状态 | 多个商品归属一个店铺；后续运营对象均关联商品 |

落地状态：Phase 1 已创建 `users`；Phase 2A 已通过第二份迁移创建 `stores`、`products`。其他表仍按后续阶段增加。

### 第二批运营表（Phase 2–4）

商品基础能力完成后，增加平台占位、SKU、库存和竞品能力。

| 表 | 主要职责 | 主要关系 |
| --- | --- | --- |
| `platform_accounts` | 店铺的平台账号占位和安全授权元数据 | 多个账号归属一个店铺 |
| `platform_product_mappings` | 本地商品与外部平台商品/SKU 标识的映射 | 多个映射归属一个商品 |
| `product_skus` | 商品可售规格、价格、成本和状态 | 多个 SKU 归属一个商品 |
| `inventory_items` | SKU 当前库存、锁定库存和预警阈值 | 第一版一个 SKU 对应一个库存汇总记录 |
| `inventory_movements` | 每次库存变化前后值、原因和来源 | 多条流水归属一个 SKU |
| `competitors` | 商品的竞品基础资料 | 多个竞品归属一个商品 |
| `public_link_parse_tasks` | 公开链接有限解析任务及错误记录 | 多个任务归属一个商品，可产生竞品补充数据 |
| `competitor_monitors` | 竞品变化监控配置 | 多个监控可归属一个竞品 |
| `competitor_monitor_snapshots` | 某次监控获取的价格、卖点等快照 | 多个快照归属一个监控 |

说明：竞品监控不是 Phase 4 的首个最小功能；先完成手工录入，再按实际演示需要增加解析任务和监控表。

落地状态：Phase 2B 已创建 `product_skus`、`inventory_items`、`inventory_movements`；Phase 3A 已创建 `competitors` 和 `public_link_parse_tasks`。平台占位、映射、定时监控及快照仍未创建。

### 第三批 AI 和素材表（Phase 5–8）

进入 AI 方案和素材任务开发后增加。

| 表 | 主要职责 | 主要关系 |
| --- | --- | --- |
| `product_diagnoses` | 保存诊断输入快照、结构化结果、原始输出和人工编辑结果 | 多次诊断归属一个商品，历史记录不覆盖 |
| `creative_plans` | 统一保存主图方案和视频脚本，以及生成来源和白名单输入快照 | 多个方案归属一个商品；生成时可使用该商品最新诊断 |
| `generation_jobs` | 图片/视频异步生成任务、状态、尝试次数和结果 | 归属商品，并关联一个创意方案 |
| `generation_job_events` | 任务状态变化和错误时间线 | 多个事件归属一个生成任务 |
| `generated_assets` | 成功生成的图片/视频及人工审核信息 | 归属商品和创意方案，可追溯到生成任务 |

`creative_plans.plan_type` 区分 `main_image` 与 `video_script`；不分别建立两套高度重复的方案表。

落地状态：Phase 4A 已通过第五份迁移创建 `product_diagnoses`；Phase 4B 通过第六份迁移增加 Provider、模型和可选用量元数据；Phase 5 通过第七份迁移创建 `creative_plans`；Phase 6 通过第八份迁移创建 `generation_jobs` 和 `generation_job_events`；Phase 7 通过第九份迁移创建 `generated_assets`。

### 第四批投放和经营分析表（Phase 8–12）

素材能力稳定后，再增加推广、投放实验、经营数据和复盘。

| 表 | 主要职责 | 主要关系 |
| --- | --- | --- |
| `promotion_links` | 目标链接、追踪码、场景和点击汇总 | 多个链接归属一个商品 |
| `promotion_link_clicks` | 单次点击的时间及有限客户端信息 | 多条点击归属一个推广链接 |
| `ad_recommendations` | 结构化投放建议及人工确认记录 | 多次建议归属一个商品，确认人关联用户 |
| `ad_experiments` | 已确认建议对应的实验计划与状态 | 归属商品，可关联建议、素材和推广链接 |
| `performance_records` | 商品在某周期的曝光、点击、转化、花费和收入 | 归属商品，可选关联方案、素材、链接和实验 |
| `review_reports` | 某周期的结构化经营分析和下一步动作 | 归属商品，基于一组经营记录和关联运营数据 |

落地状态：Phase 8 已通过第十份迁移创建 `promotion_links` 和 `promotion_link_clicks`；Phase 9 通过第十一份迁移创建 `ad_recommendations`；Phase 10 通过第十二份迁移创建 `ad_experiments`；Phase 11A 通过第十三份迁移创建 `performance_records`。文件导入和报告仍未实现。

## 3. Store、Product、ProductSku 重点关系

```text
Store 1 ──────< Product 1 ──────< ProductSku
  │                 │                  │
  │                 │                  ├── 1 InventoryItem
  │                 │                  └── N InventoryMovement
  │                 ├── N Competitor
  │                 ├── N PublicLinkParseTask
  │                 └── N 后续运营对象
  └── N PlatformAccount
```

### Store → Product

- 一个 `Store` 可以拥有多个 `Product`。
- 一个 `Product` 必须且只属于一个 `Store`，通过 `products.store_id` 关联。
- `products.store_id` 非空并建立数据库外键；Service 在写入前检查 Store，数据库约束负责最终一致性。
- 外键使用 `ON DELETE RESTRICT`，ORM 不配置级联删除。本阶段没有 Store 删除 API；未来必须先讨论商品及历史数据如何保留，不能直接级联删除。
- `Store.platform` 和 `Product.platform` 都使用受控枚举值，但数据库落地为 `VARCHAR + CHECK`，不是 PostgreSQL 原生 ENUM。新增平台需要同步修改代码枚举并通过新迁移调整两个 CHECK 约束。
- Phase 2A 不强制 Product 与所属 Store 的 `platform` 相同：Store 平台描述店铺归属，Product 平台描述当前商品记录的平台。通常二者应一致；跨平台映射规则留到明确设计 `PlatformProductMapping` 时处理。

### Product → ProductSku

- 一个 `Product` 可以拥有多个 `ProductSku`。
- 一个 `ProductSku` 必须且只属于一个 `Product`，通过 `product_skus.product_id` 关联。
- `Product.price/cost` 表示商品展示或默认值；SKU 可保存自己的实际价格和成本。存在 SKU 时，交易与库存计算优先使用 SKU 值。
- Phase 2B 已采用 `UNIQUE(product_id, sku_code)`：同一商品不能重复编码，不同商品可以复用编码。
- `product_skus.product_id` 非空并使用 `ON DELETE RESTRICT`，不允许级联删除商品历史。
- SKU 状态只有 `active/inactive`；inactive 可读，但库存调整和库存设置只读。

### ProductSku → Inventory

- 第一版一个 SKU 对应一个 `InventoryItem` 汇总当前库存，不提前支持多仓。
- 每次调整库存都同时新增一条 `InventoryMovement`，记录 `before_qty`、`change_qty`、`after_qty`、原因和业务来源。
- `available_qty` 建议由 `stock_qty - locked_qty` 计算，不重复持久化，避免值不一致。
- Phase 2B 创建 SKU 时自动创建唯一 `InventoryItem(0, 0, 0)` 和一条 `initial` 流水，整个初始化一次提交。
- `inventory_items.sku_id` 唯一，保证第一版 ProductSku 1:1 InventoryItem。
- 数据库 CHECK 保证数量非负、`locked_qty <= stock_qty`；Service 在请求提交前返回可理解的业务错误，数据库约束防止绕过 Service 的非法写入。
- 普通设置 PATCH 只能修改 `warning_threshold` 和 `location_text`；`stock_qty` 只能通过库存调整用例改变，`locked_qty` 暂无写接口。

### Product → Competitor / PublicLinkParseTask

- 一个 `Product` 可以拥有多个正式 `Competitor`，也可以拥有多个公开链接解析任务。
- `competitors.product_id` 和 `public_link_parse_tasks.product_id` 都是非空外键，并使用 `ON DELETE RESTRICT`；本阶段不提供删除接口。
- `Competitor.price` 使用可空 `NUMERIC(12, 2)`；公开页面未必能提供可靠价格，不能用虚构数值补齐。
- `selling_points`、`review_keywords` 使用 JSON 数组，当前数据结构简单，不单独拆表。
- 解析任务保存 `pending/running/succeeded/failed`、尝试次数、结构化结果和失败原因。它是任务领域记录，不代表已经引入异步队列。
- 成功结果仍是预览数据。只有人工调用确认接口后才创建正式 `Competitor`。
- `confirmed_competitor_id` 可空且唯一，用于记录确认产物。确认时以 PostgreSQL 行锁读取任务，创建竞品和回写任务在同一事务中提交，避免顺序或并发重复确认。

### Product → ProductDiagnosis

- 一个 Product 可以拥有多条 ProductDiagnosis，同一商品重新生成会新增历史记录，不覆盖旧诊断。
- `product_diagnoses.product_id` 非空并使用 `ON DELETE RESTRICT`，本阶段不提供删除接口。
- `positioning`、`price_band` 使用文本字段；`audience_insights`、`pain_points`、`selling_point_analysis`、`risks`、`recommendations` 使用 JSON 数组。
- `input_context_json` 保存生成时经过白名单映射的 Product + Competitors 输入快照，不包含数据库 ID、创建时间或更新时间。
- `raw_output` 保存 Provider 的原始响应表示，仅用于追溯和调试；正常业务读取直接使用结构化列，不解析 raw_output。
- `source_type` 在 Mock 模式为 `mock_ai`，真实 Provider 为 `ai`；不把供应商或模型拼进该字段。
- `provider_name`、`model_name` 使用独立可空字符串；`usage_json` 可空，只保存兼容 API 可靠返回的 `prompt_tokens/completion_tokens/total_tokens`，不建立计费系统。

### Product → CreativePlan

- 一个 Product 可以拥有多条 CreativePlan；`plan_type` 仅允许 `main_image` 或 `video_script`，两类方案共享表但使用不同 Pydantic content Schema。
- `creative_plans.product_id` 非空并使用 `ON DELETE RESTRICT`，不提供删除接口，以状态归档保留历史。
- `title` 和 `rationale_text` 独立保存；主图的画面结构/核心文案/突出卖点，或视频的开头钩子/结构化分镜/口播/转化引导，保存到 `content_json`，不重复存储。
- 每次生成的 3 个方向分别保存为 3 条 `draft` 记录；Provider/Schema 失败时不创建记录，数据库批量写入只提交一次。
- `provider_name`、`model_name` 和可空 `usage_json` 记录 AI 来源。一次调用生成 3 条时，各记录保存同一份调用级 usage；统计调用量时不能把三条 usage 相加。
- `input_context_json` 只保存 Product 与最新 Diagnosis 的白名单字段；没有 Diagnosis 时明确保存 `diagnosis: null`。
- 状态只允许 `draft/selected/archived`。同一个 `product_id + plan_type` 最多一个 `selected`，Service 负责归档旧选择，数据库部分唯一索引负责一致性兜底；`archived` 第一版为终态。

### Product / CreativePlan → GenerationJob → GenerationJobEvent

- Product 和 CreativePlan 都是一对多关联 GenerationJob；两个外键非空并使用 `ON DELETE RESTRICT`，任务不提供删除接口。
- `job_kind` 只允许 `image/video`，且 Service 强制 `main_image → image`、`video_script → video`；只有 `selected` 方案能够创建任务。
- `job_status` 只允许 `pending/running/succeeded/failed/cancelled/timeout`。`attempts` 表示真正调用 Generator 的次数，创建为 0，retry 不清零，且数据库 CHECK 保证 `0 <= attempts <= max_attempts`。
- `locked_at/locked_by` 表示当前运行租约；终态时清空。执行者和每次状态变化保留在事件时间线中。
- `result_json` 当前只保存 Mock 图片/视频结果，不是 `GeneratedAsset`；失败保存当前 `error_message`，retry 时清空，旧错误继续保留在 failed Event。
- `updated_at` 用于定位任务最后一次状态变化；`created_at/started_at/finished_at` 分别表达任务创建、当前尝试开始和当前终态时间。
- GenerationJob 一对多关联按 ID 升序排列的 GenerationJobEvent，事件类型只包括 `created/started/succeeded/failed/retry_requested/cancelled/timeout`。

### GenerationJob → GeneratedAsset

- Product 和 CreativePlan 都是一对多关联 GeneratedAsset；GenerationJob 是一对零或一，通过 `generation_job_id UNIQUE` 保证同一 Job 不能重复产生正式素材。
- 三个外键均非空并使用 `ON DELETE RESTRICT`，不提供素材删除接口。
- `asset_type` 只允许 `image/video`，必须与来源 Job 的 `job_kind` 一致。图片要求正宽高，视频要求正时长；Schema 负责业务错误，数据库 CHECK 负责最终数据完整性。
- 只有 succeeded Job 会被 sync 扫描。result_json 必须通过对应 `ImageGenerationResult/VideoGenerationResult`；坏结果不会创建 Asset，也不会反向篡改 Job 状态。
- `version_no` 由 Service 按 `product_id + creative_plan_id + asset_type` 自动递增。同步时锁定 CreativePlan 以串行化同方案版本分配，复合唯一约束最终兜底。
- `review_status` 为 `pending/approved/rejected`，创建默认 pending；允许 pending 作出 approved/rejected 决定，以及 approved/rejected 之间人工改判，但不退回 pending。`score` 可空且范围为 0–100。
- `tags_json` 使用字符串数组，Schema 去除首尾空白、丢弃空字符串并按首次出现顺序去重；`usage_scene` 和 `remark` 为可空自由文本。
- `model_name` 优先使用 Job result 中明确的 model_name；Mock 没有该字段时使用 `mock_image_generator/mock_video_generator`，不伪造真实模型名。

### Product → PromotionLink → PromotionLinkClick

- 一个 Product 可以拥有多个 PromotionLink；一个链接可以拥有多条点击明细，两个外键均非空且使用 `ON DELETE RESTRICT`。
- `tracking_code` 由后端使用 `secrets` 生成，不编码商品或用户 ID，并由唯一索引兜底碰撞；客户端、LLM 都不能指定。
- `target_url` 仅允许 `http/https`，系统不抓取目标页面；`utm_json` 只接受五个常见 UTM 字段。
- `status` 只允许 `active/inactive`。inactive 保留查询能力，但公开跳转返回不可用，不新增点击。
- 每次有效跳转在同一事务中插入 PromotionLinkClick，并用数据库原子表达式执行 `click_count = click_count + 1`。
- Click 只保存可空的原始 IP 和 User-Agent，不进行身份识别、地理定位、画像或跨站追踪。

### Product → AdRecommendation → User decision

- 一个 Product 可以保留多条 AdRecommendation，每次生成都新增历史记录，不覆盖旧建议；`product_id` 非空并使用 `ON DELETE RESTRICT`。
- 八类正文按严格 Pydantic Schema 生成后保存为文本或 JSON。预算字段先以 Decimal 校验，JSON 中以十进制字符串保存，分配合计必须等于总预算。
- `input_context_json` 只保存商品、最新诊断、selected 方案、approved 素材和 active 推广链接的白名单快照；素材使用本次 Context 内的别名，不暴露数据库 ID，也不包含点击明细、IP 或 User-Agent。
- `confirm_status` 为 `pending/confirmed/rejected`。只有 pending 可编辑并可由 admin/operator 决策；confirmed/rejected 都是终态。
- `confirmed_by` 由认证依赖提供的当前 User ID 写入，并通过 `ON DELETE RESTRICT` 外键关联 users；请求体不能指定。`confirmed_at` 使用 UTC aware datetime。
- Provider、模型、可选 Token usage 和输入快照用于追溯。确认仅代表建议可作为后续实验输入，不代表广告已创建或投放。

### Confirmed AdRecommendation → AdExperiment

- 一个 Product 和一条 AdRecommendation 都可以关联多条 AdExperiment；创建请求必须显式指定属于当前 Product 的 confirmed Recommendation，不能自动猜最新建议。
- `related_asset_id`、`related_link_id` 可空；提供时必须分别属于当前 Product 且为 approved/active。四个外键均为 `ON DELETE RESTRICT`。
- `budget_amount` 使用 Decimal 与 `NUMERIC(14,2)`，Schema 和数据库 CHECK 都要求大于 0。
- AI 输入只保存 Product、指定 confirmed Recommendation、可选素材和链接的白名单快照；素材/链接使用 Context 内别名，不向模型发送数据库 ID、tracking code 或 target URL。
- 状态为 `draft/confirmed/running/finished/cancelled`。只有 draft 正文可编辑；finished/cancelled 为终态。
- Provider、模型、可选 usage 和输入快照保留生成来源。`running` 只是人工记录外部实验状态，不表示系统执行广告。

### Product → PerformanceRecord

- 一个 Product 可以保存多条周期经营记录；可选关联同商品的 CreativePlan、GeneratedAsset、PromotionLink 和 AdExperiment，所有外键使用 `ON DELETE RESTRICT`。
- 关联 Experiment 仅允许 `running/finished`；`draft/confirmed/cancelled` 不能新录入实际结果。已保存记录不会因实验后续状态变化被自动删除。
- 用户只录入 `impressions/clicks/conversions/spend/revenue`。Service 统一计算并保存 `ctr/conversion_rate/roi`；Create/Update Schema 禁止客户端提交派生字段。
- `spend/revenue` 使用 `NUMERIC(14,2)`；CTR/CVR 使用 `NUMERIC(12,6)`；ROI 使用 `NUMERIC(20,6)`，`spend=0` 时 ROI 为 NULL。
- 数据库 CHECK 兜底周期顺序、非负、`clicks <= impressions`、`conversions <= clicks` 和比例范围；Service 在写入前提供明确业务校验。
- 第一版不对同商品、实验和周期建立唯一约束，也不自动覆盖历史记录；导入阶段再设计来源、修正和重复处理。
- `PromotionLink.click_count` 是链接累计跳转数，`PerformanceRecord.clicks` 是指定统计周期、特定业务口径的人工指标，两者不自动互相赋值。

### Product → ReviewReport

- 一个 Product 可以保存多份历史 ReviewReport；相同周期允许重复生成，不建立周期唯一约束，避免覆盖经营数据修正或模型变化前的历史结论。
- `product_id` 非空且使用 `ON DELETE RESTRICT`；`period_end > period_start` 同时由 Schema 和数据库 CHECK 保证。
- `summary_text` 保存周期摘要，`insights_json`、`problem_judgements_json`、`next_actions_json` 分别保存严格结构化的洞察、问题判断和后续动作。单独增加问题判断字段是为了让“事实洞察”和“经营问题定性”保持明确边界。
- `provider_name/model_name/usage_json` 保存 AI 来源，`input_context_json` 保存生成时的商品、周期、确定性汇总和有限分组快照；不保存 tracking code、目标 URL、IP、User-Agent 或点击明细。
- 报告生成只读 PerformanceRecord，不修改原始经营数据；人工只能编辑报告正文，不能改周期、Provider 元数据或输入快照。

## 4. 其他关键关系

- `Product 1:N Competitor`：竞品只在其对标商品上下文中有意义；数据来自手工录入或已确认的解析预览。
- `Product 1:N ProductDiagnosis`：保留历史诊断，不覆盖旧记录。
- `Product 1:N CreativePlan`：同一商品有多轮、多类型方案；主图与视频各自维护唯一 selected。
- `CreativePlan 1:N GenerationJob`：允许同一方案重试或生成多个版本。
- `GenerationJob 1:N GenerationJobEvent`：事件构成任务审计时间线。
- `GenerationJob 1:0..1 GeneratedAsset`：一个成功任务当前最多同步一个素材，通过唯一来源 Job 保证幂等。
- `Product 1:N PromotionLink 1:N PromotionLinkClick`：链接归属商品，计数汇总与点击明细事务一致。
- `Product 1:N AdRecommendation`：建议保留历史；状态记录人工确认结果。
- `AdRecommendation 1:N AdExperiment`：只允许从已确认建议创建实验计划。
- `GeneratedAsset 1:N AdExperiment`、`PromotionLink 1:N AdExperiment`：均为可选绑定，创建和 draft 修改时重新校验状态与商品归属。
- `Product 1:N PerformanceRecord`：按周期积累人工录入的原始指标和系统计算的派生指标。
- `Product 1:N ReviewReport`：按明确周期保存可追溯、可编辑且不覆盖历史的经营分析结果。

## 5. 已确认的全局约束

- 主键统一使用整数自增 ID；外部唯一标识使用独立业务字段。
- 第一版数据库使用 PostgreSQL。
- 时间字段使用带时区 `datetime` 并按 UTC 存储。
- 金额字段使用 Python `Decimal`，数据库使用 `NUMERIC/DECIMAL`，禁止使用 `float`。
- 第一版不做全局软删除；有历史保留要求的对象优先使用状态字段。

## 6. 待实现阶段确认的约束

- 哪些业务对象只允许停用/归档，以及是否允许物理删除无历史数据的草稿。
- 后续 AI 对象是否需要独立 Schema 版本和人工编辑版本；CreativePlan 当前已保存白名单输入快照，但不建立版本系统。
- 导入批次是否需要独立 `import_batches` / `import_row_results` 表；应在 Phase 11B 根据预览、部分成功和审计需求决定。
