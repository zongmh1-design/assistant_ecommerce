# AI 模块规划

## 1. 总体原则

- Phase 0 只定义边界和 Schema，不调用真实模型。
- 业务 Service 依赖统一 `AIProvider` 接口，不直接依赖某家模型 SDK。
- 所有重要结果必须通过 Pydantic Schema 校验后保存，不能只保存一段不可解析文本。
- 保存生成时的输入来源或快照、Schema 版本、结构化输出和必要的原始输出，便于追溯。
- AI 生成结果都是草稿；用户可以修改并保存，关键决策必须由人确认。
- 超时、API 错误、JSON 解析失败、字段缺失和 Schema 校验失败都返回明确错误，不保存为成功结果。

## 2. 通用调用流程

```text
Service 收集业务数据
→ 构造已版本化输入
→ AIProvider（Phase 0 不执行；后续可先 Mock）
→ 解析 JSON
→ Pydantic Schema 校验
→ 保存结构化结果和生成元数据
→ 用户编辑并保存
```

建议所有 AI 结果记录至少保留：`product_id`、输入来源/快照、`schema_version`、`provider`、`model_name`、结构化内容、生成状态、错误摘要、创建时间和更新时间。具体字段在对应阶段建表前确认。

## 3. 商品诊断

### 输入

- 商品名称、类目、价格、成本、目标用户、卖点和状态。
- SKU 规格、价格区间和库存摘要。
- 与该商品关联的竞品价格、卖点、评价关键词及来源说明。

### 输出 Schema

`ProductDiagnosisOutput`：

- `positioning: str`：商品定位。
- `price_band: str`：价格带分析。
- `target_audience: list[str]`：目标人群洞察。
- `pain_points: list[str]`：用户痛点。
- `selling_point_analysis: list[str]`：卖点分析。
- `risks: list[str]`：风险点。
- `recommendations: list[str]`：优化建议。

### 保存、编辑与失败

- 保存到 `product_diagnoses`，关联 `product_id`，保留输入快照和原始输出。
- 用户可以修改全部业务内容并保存；历史诊断不直接覆盖。
- 超时或输出无效时本次生成失败，不创建成功诊断；记录脱敏错误并允许有限重试。

## 4. 主图方案

### 输入

- 商品信息、商品诊断、目标用户、核心卖点、使用场景和文案限制。

### 输出 Schema

`MainImagePlanBatchOutput` 包含至少 3 个 `MainImagePlanOutput`：

- `title: str`：方案标题。
- `visual_structure: list[str]`：画面结构。
- `core_copy: list[str]`：核心文案。
- `highlighted_selling_points: list[str]`：突出卖点。
- `rationale: str`：方案理由。

### 保存、编辑与失败

- 每个方向保存为一条 `creative_plans`，`plan_type=main_image`，关联 `product_id`。
- 用户可以修改方案并切换 `draft/selected/archived`。
- 少于 3 个合法方案、字段缺失或 Schema 校验失败时整批视为失败，避免展示不完整批次；可按统一重试策略重试。

## 5. 视频脚本

### 输入

- 商品信息、诊断、目标用户、卖点、视频时长、渠道场景和转化目标。

### 输出 Schema

`VideoScriptBatchOutput` 包含至少 3 个 `VideoScriptOutput`：

- `title: str`：脚本标题。
- `opening_hook: str`：开头钩子。
- `shots: list[ShotOutput]`：镜头分镜；每项包含镜头序号、画面、口播/字幕和预计时长。
- `voiceover: list[str]`：口播文案。
- `call_to_action: str`：转化引导。

### 保存、编辑与失败

- 每条脚本保存为 `creative_plans`，`plan_type=video_script`，关联 `product_id`。
- 用户可以修改脚本和方案状态。
- 少于 3 条、时长或字段不合法时生成失败；记录错误，允许重试，不保存半成品为正式方案。

## 6. 投放建议

### 输入

- 商品与诊断、已选择方案、通过审核的素材、推广链接、可用预算、实验目标和已有经营数据（如有）。

### 输出 Schema

`AdRecommendationOutput`：

- `summary: str`：策略摘要。
- `objective: str`：本轮目标。
- `audience_segments: list[str]`：人群建议。
- `budget_plan: list[BudgetItem]`：预算建议，不代表自动修改预算。
- `creative_tests: list[CreativeTestItem]`：素材测试建议。
- `bid_strategy: str`：出价建议。
- `risk_controls: list[str]`：风险控制。
- `next_steps: list[str]`：下一步动作。

### 保存、编辑与失败

- 保存到 `ad_recommendations`，关联 `product_id`，初始确认状态为 `pending`。
- 用户可以修改内容；有权限人员必须明确 `confirmed` 或 `rejected`。
- 失败时不产生可确认建议。系统绝不因为 AI 输出而直接创建真实广告、扣费或修改预算。

## 7. 经营分析报告

### 输入

- 商品及报告周期。
- 期间使用的诊断、方案、素材、推广链接和实验计划。
- 原始经营指标：曝光、点击、CTR、转化、转化率、花费、收入和 ROI。
- 系统校验或计算后的指标摘要；确定性计算由业务代码完成，不交给 LLM 猜测。

### 输出 Schema

`ReviewReportOutput`：

- `period_summary: str`：周期摘要。
- `key_findings: list[FindingItem]`：核心发现及对应数据依据。
- `problem_judgements: list[JudgementItem]`：问题判断、证据和置信说明。
- `next_actions: list[ActionItem]`：下一步动作、优先级和预期观察指标。

### 保存、编辑与失败

- 保存到 `review_reports`，关联 `product_id` 和统计周期，并保留本次报告使用的数据快照或稳定引用。
- 用户可以编辑结论和行动建议；修改不回写原始经营数据。
- 数据为空、周期不一致或 Schema 校验失败时不生成成功报告，并明确指出是输入不足还是模型错误。

## 8. 统一失败与重试策略

- 调用超时、限流、临时网络/API 错误：按阶段设定少量重试和退避；超过上限后返回失败。
- 鉴权失败、配置错误：不盲目重试，提示管理员检查配置，日志不得输出密钥。
- JSON 解析、字段缺失、Schema 校验失败：可执行一次受控修复或重试；仍失败则保留错误摘要，不把原始文本当成有效业务结果。
- 用户应始终看到“生成中 / 失败 / 可重试”等真实状态，不能用假结果掩盖失败。
- 图片和视频的实际生成属于 Phase 7 异步任务，不属于本文件中的文本方案同步生成流程。
