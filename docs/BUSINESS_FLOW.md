# 核心业务流程

## 1. 主流程

```text
创建店铺
→ 创建商品
→ SKU / 库存
→ 竞品
→ 商品诊断
→ 主图方案
→ 视频脚本
→ 素材生成任务
→ 素材审核
→ 推广链接建议与创建
→ 投放建议
→ 人工确认
→ 实验计划
→ 经营数据
→ 经营分析报告
→ 返回下一轮商品诊断或方案优化
```

第一版以 `Product` 为业务主轴。除用户、店铺和平台账号外，后续运营结果必须能够追溯到具体商品。

当前 Phase 11B 已落地经营数据 CSV/XLSX 模板、预览和部分成功导入：Parser 只处理格式与基础类型，所有业务规则和派生指标仍由 Phase 11A Service 负责。经营分析报告仍未实现。

## 2. 分步说明

| 步骤 | 输入 | 输出 | 核心数据对象 | 下一步 |
| --- | --- | --- | --- | --- |
| 1. 创建店铺 | 店铺名称、受控平台值、负责人、外部店铺标识、备注 | 可承载商品的 `Store` 记录 | `Store`；`PlatformAccount` 尚未实现 | 创建商品 |
| 2. 创建商品 | 已存在的 `store_id`、名称、平台、类目、Decimal 价格/成本、目标用户、卖点和图片 URL | 状态为 `draft/active/inactive` 且归属 Store 的商品 | `Product`；`PlatformProductMapping` 尚未实现 | 维护 SKU 和库存 |
| 3. SKU / 库存 | 已存在商品、商品内唯一 SKU 编码、规格、Decimal 价格/成本；库存变化量和原因 | SKU；自动初始化的当前库存；每次调整的前后数量和原因流水 | `ProductSku`、`InventoryItem`、`InventoryMovement` | 补充竞品 |
| 4. 竞品 | 商品、手工竞品资料，或合法公开链接 | 正式竞品；或明确标记为 Mock 的解析预览，经人工确认后转为正式竞品 | `Competitor`、`PublicLinkParseTask`；定时监控未实现 | 商品诊断 |
| 5. 商品诊断 | 商品名称、平台、类目、价格/成本、目标用户、卖点；竞品名称、平台、价格、标题、销量提示、卖点和评论关键词 | 经过严格 Schema 校验、保存输入快照且可人工编辑的结构化诊断 | `ProductDiagnosis`、`LLMProvider`、`MockLLMProvider` | 生成主图方案 |
| 6. 主图方案 | 商品白名单字段；最新一条商品诊断（可无） | 严格生成 3 个可编辑主图方向，每个方向为独立草稿 | `CreativePlan(plan_type=main_image)` | 生成视频脚本或选择方案 |
| 7. 视频脚本 | 商品白名单字段；最新一条商品诊断（可无） | 严格生成 3 个可编辑视频脚本，每条脚本为独立草稿 | `CreativePlan(plan_type=video_script)` | 选择方案；后续阶段才创建生成任务 |
| 8. 素材生成任务 | 已选择且类型匹配的 CreativePlan | 任务状态、Mock `result_json` 或错误，以及完整事件时间线 | `GenerationJob`、`GenerationJobEvent`、`MediaGenerator` | 成功结果在下一阶段进入素材库；失败/超时可按次数重试 |
| 9. 素材审核 | succeeded Job 的严格结果、系统版本；人工填写审核状态、使用场景、评分、标签和备注 | 可追溯来源 Job、可查询且可改判的正式素材记录 | `GeneratedAsset` | 生成推广链接参数建议 |
| 10. 推广链接 | 商品、可选 selected 方案、可选 approved 素材；用户提交 target URL | UTM 建议；active/inactive 链接；公开跳转、点击明细和汇总计数 | `PromotionLink`、`PromotionLinkClick` | 后续投放建议或人工分享 |
| 11. 投放建议 | 商品、诊断、创意方案、已审核素材、预算约束 | 可编辑的结构化目标、人群、预算、测试和风控建议 | `AdRecommendation` | 人工确认或驳回 |
| 12. 人工确认 | 投放建议、确认人、意见 | `confirmed` 或 `rejected` 的审计结果 | `AdRecommendation` | 已确认则创建实验计划；驳回则返回修改 |
| 13. 实验计划 | 已确认建议、素材、推广链接、预算和成功指标 | 状态为 `draft` 的实验计划，后续由人工更新状态和结果 | `AdExperiment`、`PromotionLink` | 录入实验期经营数据 |
| 14. 经营数据 | 商品、统计周期、曝光、点击、转化、花费、收入 | 校验后的经营记录及系统计算的 CTR、Conversion Rate、ROI | `PerformanceRecord` | 文件导入或经营分析报告 |
| 15. 经营分析报告 | 商品、统计周期、方案、素材、实验和经营数据 | 可编辑的周期摘要、核心发现、问题判断和下一步动作 | `ReviewReport` | 返回诊断或方案环节进入下一轮 |

## 3. 关键状态与分支

### 商品

```text
draft → active → inactive
```

只有满足后续阶段约定的必要资料后，商品才进入对应生成流程；具体校验规则在各阶段实现时补充。

### 公开链接解析与人工确认

```text
创建任务(pending)
→ 手工触发运行(running, attempts + 1)
→ PublicLinkParser
→ succeeded(result_json) | failed(error_message)
→ succeeded 结果由用户确认
→ 同一事务创建 Competitor 并记录 confirmed_competitor_id
```

当前实现使用确定性的 `MockPublicLinkParser`，不访问网络。解析结果不会自动进入正式竞品数据，避免不完整或错误的外部信息污染后续商品诊断输入。

### 商品诊断生成与编辑

```text
Product + Competitors
→ 白名单 ProductDiagnosisContext
→ 独立 Prompt
→ LLMProvider（当前 Mock）
→ ProductDiagnosisOutput 严格校验
→ 保存输入快照、结构化列和 raw_output
→ 用户 PATCH 结构化业务字段
```

没有竞品时仍允许生成，Context 中使用空数组，Prompt 明确要求说明竞品依据不足。Provider 调用失败或输出 Schema 非法时，在创建 ORM 记录之前返回明确错误，因此不会留下损坏诊断。

### 创意方案

```text
Product + Latest ProductDiagnosis（可空）
→ 白名单 CreativePlanContext
→ Main Image 或 Video Script Prompt
→ 现有 LLMProvider
→ 对应批量输出 Schema 严格校验（必须正好 3 条）
→ 同一事务保存 3 条独立 CreativePlan(draft)
→ 用户编辑或选择

draft → selected | archived
selected → archived
archived（终态）
```

主图方案和视频脚本共用 `CreativePlan`，通过 `plan_type` 区分，避免重复的数据结构和业务逻辑。没有诊断时仍允许仅根据已知商品信息生成，Context 中明确使用 `diagnosis=null`。同一商品同一 `plan_type` 最多一个 `selected`；选择新方案时，Service 在同一事务中归档旧方案。主图和视频的选择互不影响。

Provider 失败、输出非法或少于 3 条时，在创建 ORM 记录前终止；数据库批量写入任一失败则整个事务回滚。`CreativePlan` 只代表文字创意方向，不是 `GeneratedAsset`，也不会触发真实图片或视频生成。

### 素材生成任务

```text
pending → running → succeeded
                  ↘ failed → retry → pending
                  ↘ timeout → retry → pending
pending → cancelled
```

只有 `selected` CreativePlan 能创建任务，且 `main_image` 只能创建 image Job、`video_script` 只能创建 video Job。创建 Job 和 created Event 在同一事务中提交。

run 使用两个短事务：第一个事务通过 PostgreSQL 行锁确认 pending，保存 running、attempts、锁信息和 started Event 后提交；随后才调用 Generator；第二个事务保存 succeeded/result 或 failed/error 以及对应 Event。这样外部调用期间其他请求能看到 running，且状态和终态事件不会出现一半成功。

retry 只允许 failed/timeout 回到 pending，不增加或重置 attempts，并清空当前错误和运行字段；旧错误保留在事件中。running 不支持 cancel，因为当前同步执行器无法真正中断正在运行的 Python 调用。管理员通过独立 sweep 接口标记超时，不在 GET 请求中顺带扫描。

当前 Mock Generator 不访问网络、不创建文件，只产生确定性 `mock://` result_json。即使使用 Mock，也真实记录状态迁移和事件时间线；`result_json` 不是正式素材。

### Job 结果同步与素材审核

```text
Product 下 succeeded GenerationJob
→ generation_job_id 幂等检查
→ 按 job_kind 选择严格 Result Schema
→ 校验 asset_type、URL、图片尺寸或视频时长
→ 锁定 CreativePlan 并计算下一版本
→ 单 Job 事务创建 GeneratedAsset(pending)
→ 人工 approved / rejected，可后续改判
```

sync 逐 Job 独立提交：坏 result 或单条数据库失败会记录安全 failure detail，并继续同步其他合法 Job。再次同步已有来源 Job时返回 skipped，不增加版本。Job 的 succeeded 表示生成步骤完成，Asset 表示结果已经达到正式素材库的数据要求，两者职责不混淆。

### 推广建议、链接与点击

```text
Product + optional selected CreativePlan + optional approved GeneratedAsset
→ 白名单 Context → Prompt → 现有 LLMProvider
→ PromotionLinkSuggestion 严格校验（不落库）
→ 用户提交 target_url → 后端生成 tracking_code → PromotionLink(active)
→ 公开 GET /r/{tracking_code}
→ 同一事务：写 PromotionLinkClick + 原子增加 click_count
→ 302 跳转 target_url
```

AI 不生成 tracking code，也不猜 target URL。inactive 链接不跳转、不计数。302 用于普通 GET 跟踪跳转，兼容性清晰且不暗示目标永久不变。

### 投放建议与人工决策

```text
Product + Latest Diagnosis（可空）
+ selected CreativePlans
+ approved GeneratedAssets
+ active PromotionLinks
→ 白名单 AdRecommendationContext
→ Prompt → 现有 LLMProvider → AdRecommendationOutput
→ 严格校验后新增 AdRecommendation(pending)
→ 人工编辑 pending 正文
→ pending → confirmed | rejected（终态）
```

没有素材、链接或点击仍允许生成，但 Prompt 和 Mock 都明确数据不足，不得编造 CTR、CVR、ROI 或收益。`confirmed_by` 来自当前登录用户而非请求体。人工确认只表示可作为下一阶段实验计划输入，不会创建或启动任何真实广告活动。

### 实验计划生成与状态

```text
specified AdRecommendation(confirmed)
+ optional GeneratedAsset(approved, same Product)
+ optional PromotionLink(active, same Product)
→ whitelist AdExperimentContext
→ Prompt → existing LLMProvider → AdExperimentOutput
→ AdExperiment(draft)
→ 人工编辑
→ draft → confirmed → running → finished
         ↘ cancelled  ↘ cancelled
```

创建时必须显式提交 recommendation_id，避免多轮历史建议来源不清。draft 后正文冻结；如果确认后发现内容需要修改，应取消旧实验并生成新实验。`running` 与 `finished` 都是运营人员对外部执行情况的人工记录，没有 Campaign、预算、出价或扣费调用。

### 经营数据手工录入与文件导入

```text
POST /products/{product_id}/performance-records
→ JWT + write permission
→ PerformanceRecordService
→ Product + optional relation ownership checks
→ Experiment status check (running/finished)
→ validate raw metrics and period
→ Decimal calculation of CTR / Conversion Rate / ROI
→ PerformanceRecordRepository
→ Database
```

- 原始指标为 impressions、clicks、conversions、spend、revenue，均由用户明确录入；本阶段不调用 LLM。
- 更新任一原始指标或周期后，Service 对合并后的完整数据重新校验并重算全部派生指标。
- `spend=0` 时 ROI 没有定义，保存 NULL；零曝光和零点击对应比例保存 0，避免除零。
- 推广链接累计 click_count 不自动成为周期经营 clicks，两者统计周期和业务口径不同。

```text
CSV/XLSX upload
→ PerformanceRecordFileParser（格式、表头、行号、基础类型）
→ PerformanceRecordCreate
→ PerformanceRecordService.validate_and_prepare（Preview，无写入）
→ 或 PerformanceRecordService.create（Import，每行独立 commit）
→ PreviewResult / PartialImportResult
```

- Preview 不持久化临时状态、不写 PerformanceRecord；正式 Import 重新上传、重新解析并重新检查数据库关联状态。
- 空白行跳过；错误保留原始文件行号。合法行与非法行互不阻塞。
- CSV 只接受 UTF-8/UTF-8 BOM；XLSX 只读取第一张工作表；不使用 pandas、LLM 或智能纠错。

### 经营复盘报告

```text
Product + explicit report period
→ 只查询完整落在周期内的 PerformanceRecord
→ 汇总 impressions/clicks/conversions/spend/revenue
→ 基于总量重新计算 CTR/CVR/ROI
→ 按 Experiment / Asset / PromotionLink 做有限分组
→ whitelist ReviewReportContext
→ existing LLMProvider → ReviewReportOutput
→ ReviewReport history
→ human edit
```

- 周期必须由用户明确提交；跨周期记录不截断、不纳入，并在 Context 记录 `excluded_count`。
- 周期内没有合法 PerformanceRecord 时返回 `no_performance_data`，不会调用 LLM。
- LLM 只解释系统给出的指标并提出下一步建议，不能重算数字、修改 PerformanceRecord 或自动创建下一轮诊断/创意/投放。
- 同商品同周期重新生成会新增报告，保留旧报告及当时的输入快照。

### Demo 单品闭环

```text
admin login
→ POST /workspace/demo-data
→ Store → Product → SKU/Inventory Movement → Competitors
→ Diagnosis → 3 Main Images + 3 Video Scripts → selected
→ image/video Job → Mock run → Asset sync → approved
→ PromotionLink + Clicks
→ AdRecommendation confirmed
→ AdExperiment draft → confirmed → running
→ 3 PerformanceRecords → finished
→ ReviewReport
```

固定 Demo 店铺名只用于查找根对象和恢复进度，不增加数据库字段。初始化失败保留已提交阶段并返回失败步骤；重复调用不会复制完整业务图。Smoke 脚本随后通过真实 HTTP 查询验证每个关键状态。

## 4. 数据回流

经营分析报告不是流程终点。报告中的问题判断和下一步动作由运营人员确认后，可以触发下一轮商品资料修正、竞品补充、商品诊断、创意方案或实验计划。第一版保存轮次关联所需的时间、商品和来源记录，但不引入复杂工作流引擎。
