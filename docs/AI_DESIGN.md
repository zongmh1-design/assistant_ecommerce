# AI 模块规划

## 1. 总体原则

- Phase 4B 已在保留 Mock 的同时实现可配置 OpenAI-compatible Provider；是否访问真实网络完全由显式环境配置决定。
- `ProductDiagnosisService` 和 `CreativePlanService` 都依赖同一个 `LLMProvider` 接口，不直接依赖 Mock 或某家模型 SDK。
- 所有重要结果必须通过 Pydantic Schema 校验后保存，不能只保存一段不可解析文本。
- 保存生成时的输入来源或快照、Schema 版本、结构化输出和必要的原始输出，便于追溯。
- AI 生成结果都是草稿；用户可以修改并保存，关键决策必须由人确认。
- 超时、API 错误、JSON 解析失败、字段缺失和 Schema 校验失败都返回明确错误，不保存为成功结果。

## 2. 通用调用流程

```text
Service 收集业务数据
→ 构造白名单 Context
→ 独立 Prompt
→ LLMProvider（配置选择 Mock 或 OpenAI-compatible）
→ Provider 返回候选结构与 raw_output
→ Pydantic Schema 校验
→ 保存输入快照、结构化结果和原始输出
→ 用户编辑并保存
```

商品诊断保留 `product_id`、`source_type`、`provider_name`、`model_name`、可选 `usage_json`、白名单输入快照、结构化内容、`raw_output` 和时间。CreativePlan 保存 Provider、模型、可选 usage 和白名单 Creative Context，但不重复保存整批原始文本。Token 用量缺失时保持为空，不做成本计费。

## 3. 商品诊断

### 输入

- Product：`name`、`platform`、`category`、`price`、`cost`、`target_audience`、`selling_points`。
- Competitors：每项只包含 `name`、`platform`、`price`、`title`、`sales_hint`、`selling_points`、`review_keywords`。
- 不发送数据库 ID、`created_at`、`updated_at` 或 ORM 技术字段。没有竞品时传递空数组，不阻止生成。

### 输出 Schema

`ProductDiagnosisOutput`：

- `positioning: str`：商品定位。
- `price_band: str`：价格带分析。
- `audience_insights: list[str]`：目标人群洞察。
- `pain_points: list[str]`：用户痛点。
- `selling_point_analysis: list[str]`：卖点分析。
- `risks: list[str]`：风险点。
- `recommendations: list[str]`：优化建议。

### 保存、编辑与失败

- `ProductDiagnosisContext` 由专用函数从 Product 和 Competitor ORM 记录映射；Prompt 位于 `app/ai/prompts/product_diagnosis.py`。
- `get_llm_provider()` 集中根据 `LLM_PROVIDER` 选择实现。默认 `mock` 不访问网络；只有显式选择 `openai_compatible` 且配置完整时才创建真实 Provider，配置错误不自动回退。
- OpenAI-compatible 调用使用 System + User Prompt，并附带目标 JSON Schema 作为输出约束提示；不依赖服务端一定支持 `response_format/json_schema`。
- Provider 只接受纯 JSON 或明确的 Markdown JSON code fence，随后执行 `json.loads` 和目标 Pydantic Schema 校验，不猜测或修补缺失字段。
- Provider 返回后，Service 再用 `ProductDiagnosisOutput` 独立校验。只有校验成功才创建数据库记录。
- 保存到 `product_diagnoses`，关联 `product_id`，保留白名单输入快照、七个结构化字段和 Mock JSON raw_output。
- 用户只能修改七个结构化业务字段；`id/product_id/source_type/created_at` 不可通过 PATCH 修改。重新生成会新增记录，历史诊断不覆盖。
- Provider 返回 `provider_name/model_name/usage`，Service 以独立字段保存；真实模式 `source_type=ai`。
- 配置、认证、限流、超时、其他网络/服务端错误和非法输出映射到稳定错误 code，不向客户端暴露底层堆栈或敏感配置。所有失败都发生在创建诊断记录之前。

## 4. 主图方案

### 输入

- Product：`name`、`platform`、`category`、`price`、`target_audience`、`selling_points`。
- 优先读取该 Product 最新一条 ProductDiagnosis，只包含 `positioning`、`price_band`、`audience_insights`、`pain_points`、`selling_point_analysis`、`risks`、`recommendations`。
- 没有诊断时传递 `diagnosis=null`，只根据已知商品信息生成；不发送 ID、raw_output、Provider 元数据、Token usage 或时间字段。

### 输出 Schema

`MainImagePlansOutput` 必须包含正好 3 个 `MainImagePlanItem`：

- `title: str`：方案标题。
- `visual_structure: list[str]`：画面结构。
- `core_copy: list[str]`：核心文案。
- `highlighted_selling_points: list[str]`：突出卖点。
- `rationale: str`：方案理由。

### 保存、编辑与失败

- 每个方向保存为一条 `creative_plans`，`plan_type=main_image`，关联 `product_id`。
- Prompt 位于 `app/ai/prompts/main_image_plan.py`，明确只生成创意方向，不生成图片、不调用外部平台或执行投放。
- 用户可以按主图 content Schema 修改方案并执行受控状态迁移。
- 少于 3 个合法方案、字段缺失或 Schema 校验失败时整批视为失败；3 条只在一个数据库事务中提交，避免不完整批次。

## 5. 视频脚本

### 输入

- 与主图方案共用 `CreativePlanContext`：相同的 Product 白名单字段和可空的最新 ProductDiagnosis 白名单字段。

### 输出 Schema

`VideoScriptsOutput` 必须包含正好 3 个 `VideoScriptItem`：

- `title: str`：脚本标题。
- `opening_hook: str`：开头钩子。
- `storyboard: list[StoryboardScene]`：结构化分镜；每项包含 `scene_no`、`visual`、`duration_hint`、`voiceover`。
- `voiceover: list[str]`：口播文案。
- `conversion_cta: str`：转化引导。

### 保存、编辑与失败

- 每条脚本保存为 `creative_plans`，`plan_type=video_script`，关联 `product_id`。
- Prompt 位于 `app/ai/prompts/video_script.py`，明确只输出文字脚本，不生成视频、不调用外部平台或执行投放。
- 用户可以按视频 content Schema 修改脚本和执行受控状态迁移。
- 少于 3 条或字段不合法时生成失败；只有完整验证后才创建 3 条 ORM 记录，并在一个事务中提交。

### CreativePlan 共用流程与 Mock

```text
Product + Latest ProductDiagnosis（可空）
→ CreativePlanContext 白名单映射
→ main_image_plan.py / video_script.py
→ 已有 LLMProvider.generate_structured(...)
→ MainImagePlansOutput / VideoScriptsOutput
→ 再次 Pydantic 校验
→ 单事务保存 3 条 CreativePlan
```

- `get_llm_provider()` 仍集中选择 Mock 或 OpenAI-compatible 实现，Route 和 Service 不判断供应商。
- `MockLLMProvider` 根据传入的 `response_schema` 类型选择确定性输出，同时继续支持 `ProductDiagnosisOutput`；不依赖 Prompt 文本关键词判断任务。
- OpenAI-compatible Provider 的超时、有限重试、JSON 解析和错误映射全部复用 Phase 4B，不增加新的 AI 基础设施。
- 选择状态规则为 `draft → selected/archived`、`selected → archived`；`archived` 为终态。同商品同类型选择新方案时，同一事务归档旧 selected。
- CreativePlan 是可编辑的文字方案，不是 `GeneratedAsset`。真实图片/视频、GenerationJob、Worker 和素材库均不属于 Phase 5。

## 6. 推广链接建议

```text
Product + optional selected CreativePlan + optional approved GeneratedAsset
→ PromotionLinkSuggestionContext 白名单映射
→ promotion_link.py Prompt
→ 现有 LLMProvider
→ PromotionLinkSuggestion 严格校验
→ 仅返回建议，不创建 PromotionLink
```

- Product 只发送名称、平台、类目、目标人群和卖点；方案只发送类型、标题和结构化内容；素材只发送类型、使用场景和标签。
- 输出只包含链接名称、场景、四个 UTM 建议和理由，不包含 `tracking_code` 或 `target_url`。
- `MockLLMProvider` 按 `response_schema is PromotionLinkSuggestion` 返回确定结果；真实模式继续复用现有 OpenAI-compatible 超时、重试、解析和错误边界。
- 建议不单独建表：它不是最终业务链接。target URL 必须由用户提交，tracking code 必须由后端生成。

## 7. 投放建议

### 输入

- Product：名称、平台、类目、Decimal 价格、目标人群、卖点。
- 最新 ProductDiagnosis（可空）：定位、人群洞察、痛点、卖点分析、风险和建议。
- 所有 selected CreativePlan：类型、标题、结构化内容。
- 所有 approved GeneratedAsset：Context 内唯一素材别名、类型、版本、场景、评分和标签。
- 所有 active PromotionLink：名称、场景、UTM 和汇总点击数。
- 不发送数据库 ID、点击明细、IP、User-Agent、raw output、时间或 Provider 配置。

### 输出 Schema

`AdRecommendationOutput`：

- `summary: str`：策略摘要。
- `objective: str`：本轮目标。
- `audience_segments: list[AudienceSegment]`：名称、描述、依据，不含平台人群 ID。
- `budget_plan: BudgetPlan`：Decimal 总预算、币种、分配和理由；JSON 以十进制字符串保存，分配合计必须等于总额。
- `creative_tests: list[CreativeTest]`：Context 素材别名、假设和待验证成功指标。
- `bid_strategy: BidStrategy`：策略名称、理由和约束，不是平台操作指令。
- `risk_controls: list[RiskControl]`：风险及缓解方式。
- `next_steps: list[str]`：下一步动作。

### 保存、编辑与失败

- 独立 Prompt 位于 `app/ai/prompts/ad_recommendation.py`；现有 Mock 和 OpenAI-compatible Provider 通过同一 `generate_structured` 调用。
- 保存到 `ad_recommendations`，关联 `product_id`，每次生成新增历史记录，初始状态为 `pending`，并保存 Provider 元数据和白名单输入快照。
- pending 正文可人工编辑；admin/operator 可作 confirmed/rejected 最终决策，终态正文冻结。确认人来自当前 JWT 对应用户。
- 即使数据不足也可给出保守的测试框架，但必须明确缺少真实指标，不能声称既有 CTR、CVR、ROI、曝光或转化。
- Provider 或 Schema 失败发生在 ORM 创建前，不产生半条建议。系统不创建广告、扣费、修改预算或执行出价。

## 8. 投放实验计划

```text
Product + explicitly selected confirmed AdRecommendation
+ optional approved GeneratedAsset
+ optional active PromotionLink
→ AdExperimentContext 白名单映射
→ ad_experiment.py Prompt
→ existing LLMProvider
→ AdExperimentOutput strict validation
→ AdExperiment(draft)
```

- 输出包含实验名称、目标、人群、正数 Decimal 预算、成功指标定义和待验证假设。
- 输入 Recommendation 是用户明确提交的历史轮次；模型不选择数据库记录。素材和链接只使用 Context 内别名。
- 没有素材或链接仍可生成，但必须明确缺失；不得编造 CTR、CVR、ROI 或把假设写成事实。
- `MockLLMProvider` 通过 `response_schema is AdExperimentOutput` 生成确定结果，真实 Provider 继续复用原有超时、有限重试和错误边界。
- Provider/Schema 失败不落库。生成结果初始为 draft，后续状态全部由人工 API 控制，不触发任何平台执行。

## 9. 经营分析报告

### 输入

- 商品白名单字段和用户明确提交的报告周期。
- 完整落在周期内的 PerformanceRecord 先由程序汇总；跨周期记录不截断，通过 `excluded_count` 说明未纳入数量。
- `total_impressions/total_clicks/total_conversions/total_spend/total_revenue` 以及基于总量重新计算的 `overall_ctr/overall_conversion_rate/overall_roi`。
- 只对存在关联的 Experiment、GeneratedAsset、PromotionLink 提供有限分组汇总。实验包含名称、假设、成功指标和人工状态；素材、链接使用 Context 内别名，不传数据库 ID、URL 或点击明细。
- 周期内无经营数据时在 Provider 调用前返回 `no_performance_data`。

### 输出 Schema

`ReviewReportOutput`：

- `summary: str`：周期摘要。
- `insights: list[ReviewInsight]`：每项包含标题、发现和基于 Context 指标的 evidence。
- `problem_judgements: list[ProblemJudgement]`：每项包含问题、证据和 `low/medium/high` 严重程度。
- `next_actions: list[ReviewNextAction]`：每项包含动作、理由和 `high/medium/low` 优先级。

### 保存、编辑与失败

- Prompt 位于 `app/ai/prompts/review_report.py`，明确禁止模型重新计算指标、篡改财务数字或编造外部基准。
- `MockLLMProvider` 按 `response_schema is ReviewReportOutput` 返回确定性内容，并在 evidence 中引用 Context 的真实总点击、整体 CTR 和 ROI。
- 保存到 `review_reports`，关联 `product_id` 和不可编辑统计周期，并保存 Provider 元数据和白名单 `input_context_json` 快照；同周期重新生成只新增历史记录。
- 用户可以编辑摘要、洞察、问题判断和行动建议；修改不回写 PerformanceRecord，也不改变生成周期和依据。
- Provider/Schema 失败不落库；报告中的 next_actions 只是人工建议，不自动生成诊断、创意或投放对象。

## 10. 统一失败与重试策略

- Phase 4B 对 timeout、临时网络错误、HTTP 429 和 HTTP 5xx 最多执行 `LLM_MAX_RETRIES` 次额外重试，退避为 1 秒、2 秒等简单指数序列。
- 鉴权失败、配置错误：不盲目重试，提示管理员检查配置，日志不得输出密钥。
- HTTP 400 等明确参数错误不重试；401/403 不重试；JSON 解析、字段缺失和 Schema 校验失败也不重试、不自动修复。
- 普通运行日志不记录 API Key、Authorization Header、完整 Prompt 或 Context。业务追溯优先读取已保存的 `input_context_json`。
- 用户应始终看到“生成中 / 失败 / 可重试”等真实状态，不能用假结果掩盖失败。
- 图片和视频的实际生成属于 Phase 7 异步任务，不属于本文件中的文本方案同步生成流程。
