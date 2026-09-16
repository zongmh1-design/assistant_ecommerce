# 项目需求实现对照表

| 需求 | 实现模块 | 主要 API | 状态 |
|---|---|---|---|
| 登录与三角色权限 | User / Auth | `POST /auth/login`、`GET /auth/me` | 已完成 |
| 店铺与商品 | Store / Product | `/stores`、`/products` | 已完成 |
| SKU 与库存流水 | ProductSku / InventoryItem / InventoryMovement | `/products/{id}/skus`、`/skus/{id}/inventory/adjust` | 已完成 |
| 竞品手工维护 | Competitor | `/products/{id}/competitors` | 已完成 |
| 公开链接解析 | PublicLinkParseTask / PublicLinkParser | `POST /products/{id}/competitors/import-url-tasks` | Mock Parser |
| 商品诊断 | ProductDiagnosis | `POST /products/{id}/diagnoses/generate` | 已完成；默认 Mock LLM |
| 主图方向与视频脚本 | CreativePlan | `POST .../main-images/generate`、`POST .../video-scripts/generate` | 已完成；默认 Mock LLM |
| 图片/视频生成任务 | GenerationJob / Event | `POST .../images/generate`、`POST .../videos/generate`、`POST .../run` | 已完成；Mock Generator |
| 素材库与审核 | GeneratedAsset | `POST /products/{id}/assets/sync`、`PATCH /assets/{id}` | 已完成；Mock URL |
| 推广链接与点击 | PromotionLink / Click | `/promotion-links`、`GET /r/{tracking_code}` | 已完成 |
| 投放建议与人工确认 | AdRecommendation | `POST .../ad-recommendations/generate`、`PATCH .../confirmation` | 已完成；建议不执行广告 |
| 投放实验计划 | AdExperiment | `POST .../ad-experiments/generate`、`PATCH .../status` | 已完成；人工状态记录 |
| 经营数据手工录入 | PerformanceRecord | `POST /products/{id}/performance-records` | 已完成 |
| CSV/XLSX 导入 | PerformanceRecord Import | `/performance-records/import/preview`、`/import` | 已完成 |
| 经营分析报告 | ReviewReport | `POST .../review-reports/generate` | 已完成；默认 Mock LLM |
| Demo 完整闭环 | DemoDataService / HTTP Smoke | `POST /workspace/demo-data`、`scripts.smoke_test_demo_flow` | 已完成 |
| OpenAI-compatible LLM | OpenAICompatibleLLMProvider | 复用所有结构化 AI API | 已实现；需用户本地配置验证 |
| 真实电商平台授权与同步 | External Integration 预留 | 无真实 API | 未接入 |
| 真实图片/视频模型 | MediaGenerator 抽象 | 无真实模型调用 | 未接入 |
| 真实广告平台执行 | 明确排除 | 无执行 API | 未接入 |
| 对象存储与生产 Worker | 明确排除 | 无 | 未接入 |
| 前端 | 独立后续阶段 | 无 | 未实现 |

说明：表中省略了统一前缀 `/api/v1`。Mock 能力不会被描述成真实平台或真实模型接入。
