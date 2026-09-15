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
→ 投放建议
→ 人工确认
→ 实验计划
→ 经营数据
→ 经营分析报告
→ 返回下一轮商品诊断或方案优化
```

第一版以 `Product` 为业务主轴。除用户、店铺和平台账号外，后续运营结果必须能够追溯到具体商品。

当前 Phase 3A 已落地前四步：Store、Product、ProductSku、当前库存、库存流水及竞品。商品诊断及后续步骤尚未实现。

## 2. 分步说明

| 步骤 | 输入 | 输出 | 核心数据对象 | 下一步 |
| --- | --- | --- | --- | --- |
| 1. 创建店铺 | 店铺名称、受控平台值、负责人、外部店铺标识、备注 | 可承载商品的 `Store` 记录 | `Store`；`PlatformAccount` 尚未实现 | 创建商品 |
| 2. 创建商品 | 已存在的 `store_id`、名称、平台、类目、Decimal 价格/成本、目标用户、卖点和图片 URL | 状态为 `draft/active/inactive` 且归属 Store 的商品 | `Product`；`PlatformProductMapping` 尚未实现 | 维护 SKU 和库存 |
| 3. SKU / 库存 | 已存在商品、商品内唯一 SKU 编码、规格、Decimal 价格/成本；库存变化量和原因 | SKU；自动初始化的当前库存；每次调整的前后数量和原因流水 | `ProductSku`、`InventoryItem`、`InventoryMovement` | 补充竞品 |
| 4. 竞品 | 商品、手工竞品资料，或合法公开链接 | 正式竞品；或明确标记为 Mock 的解析预览，经人工确认后转为正式竞品 | `Competitor`、`PublicLinkParseTask`；定时监控未实现 | 商品诊断 |
| 5. 商品诊断 | 商品、SKU、价格、目标用户、卖点、竞品 | 可编辑的结构化定位、痛点、风险和优化建议 | `ProductDiagnosis` | 生成主图方案 |
| 6. 主图方案 | 商品诊断、卖点、目标用户、素材约束 | 至少 3 个可编辑主图方向 | `CreativePlan(plan_type=main_image)` | 生成视频脚本 |
| 7. 视频脚本 | 商品诊断、卖点、目标用户、投放场景 | 至少 3 个可编辑视频脚本 | `CreativePlan(plan_type=video_script)` | 选择方案并创建生成任务 |
| 8. 素材生成任务 | 已选择的创意方案、生成参数 | 异步任务及状态事件；成功时产生结果 | `GenerationJob`、`GenerationJobEvent` | 成功进入素材库；失败则重试/取消 |
| 9. 素材审核 | 生成结果、版本、使用场景、评分、标签、备注 | `approved/rejected/pending` 等人工审核结果 | `GeneratedAsset` | 使用通过审核的素材生成投放建议 |
| 10. 投放建议 | 商品、诊断、创意方案、已审核素材、预算约束 | 可编辑的结构化目标、人群、预算、测试和风控建议 | `AdRecommendation` | 人工确认或驳回 |
| 11. 人工确认 | 投放建议、确认人、意见 | `confirmed` 或 `rejected` 的审计结果 | `AdRecommendation` | 已确认则创建实验计划；驳回则返回修改 |
| 12. 实验计划 | 已确认建议、素材、推广链接、预算和成功指标 | 状态为 `draft` 的实验计划，后续由人工更新状态和结果 | `AdExperiment`、`PromotionLink` | 录入实验期经营数据 |
| 13. 经营数据 | 商品、统计周期、曝光、点击、转化、花费、收入；或 CSV / Excel | 校验后的经营记录及逐行导入结果 | `PerformanceRecord` | 生成经营分析报告 |
| 14. 经营分析报告 | 商品、统计周期、方案、素材、实验和经营数据 | 可编辑的周期摘要、核心发现、问题判断和下一步动作 | `ReviewReport` | 返回诊断或方案环节进入下一轮 |

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

### 创意方案

```text
draft → selected
draft/selected → archived
```

主图方案和视频脚本共用 `CreativePlan`，通过 `plan_type` 区分，避免重复的数据结构和业务逻辑。

### 素材生成任务

```text
pending → running → succeeded
                  ↘ failed → retry → pending
                  ↘ timeout → retry → pending
pending/running → cancelled
```

即使使用 Mock Generator，也必须真实记录状态迁移和事件时间线。

### 投放建议与实验

```text
AdRecommendation: pending → confirmed | rejected
AdExperiment: draft → confirmed → running → finished
                         ↘ cancelled
```

投放建议不能绕过人工确认直接创建或启动真实广告活动。

## 4. 数据回流

经营分析报告不是流程终点。报告中的问题判断和下一步动作由运营人员确认后，可以触发下一轮商品资料修正、竞品补充、商品诊断、创意方案或实验计划。第一版保存轮次关联所需的时间、商品和来源记录，但不引入复杂工作流引擎。
