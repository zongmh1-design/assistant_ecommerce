# 完整单品业务演示

前置条件：PostgreSQL 已迁移到 head、管理员已创建、FastAPI 已启动，默认 `LLM_PROVIDER=mock`。

可先调用 `POST /api/v1/workspace/demo-data` 创建或恢复整套 Demo 数据，再按返回的 ID 演示以下页面和接口。所有 Demo 平台、竞品、素材 URL 和经营数字均为 Mock。

## 1 登录

- API：`POST /api/v1/auth/login`、`GET /api/v1/auth/me`
- 作用：管理员取得 JWT，并验证当前用户和角色。
- 应看到：`role=admin`；密码和 Token 不写入日志或演示文档。

## 2 店铺 / 商品

- API：`GET /api/v1/stores/{store_id}`、`GET /api/v1/products/{product_id}`
- 作用：展示 “Demo 数码店” 和 “轻量磁吸移动电源”。
- 应看到：完整品类、Decimal 价格/成本、目标人群、卖点和 Demo/Mock 标识。

## 3 SKU / 库存

- API：`GET /api/v1/products/{product_id}/skus`、`GET /api/v1/skus/{sku_id}/inventory`、`GET .../movements`
- 作用：展示 5000mAh、10000mAh 两个 SKU 的当前库存和历史变化。
- 应看到：库存通过入库调整产生，流水包含 before/change/after，不是直接覆盖数量。

## 4 竞品

- API：`GET /api/v1/products/{product_id}/competitors`
- 作用：展示两个手工 Demo 竞品样本。
- 应看到：名称、价格、卖点、评论关键词均明确为示例数据，不是平台抓取结果。

## 5 商品诊断

- API：`GET /api/v1/products/{product_id}/diagnoses`
- 作用：展示 Product + Competitors 经 Mock LLM 生成的结构化诊断。
- 应看到：定位、价格带、人群、痛点、风险和建议；`source_type=mock_ai`。

## 6 创意方案

- API：`GET /api/v1/products/{product_id}/creative-plans`
- 作用：展示 3 个主图方向和 3 个视频脚本。
- 应看到：主图、视频各恰好一个 `selected`，其他方案保留为 draft。

## 7 Generation Job

- API：`GET /api/v1/products/{product_id}/generation-jobs/{job_id}`
- 作用：展示 selected 方案对应的图片、视频任务和事件时间线。
- 应看到：`pending → running → succeeded`、`attempts=1` 和 Mock result URL。

## 8 素材审核

- API：`GET /api/v1/products/{product_id}/assets/{asset_id}`
- 作用：展示成功 Job 经过严格结果校验后同步到素材库。
- 应看到：一个 image、一个 video，均为 `approved`，带版本、场景、评分和 Demo/Mock 标签。

## 9 Promotion Link

- API：`GET /api/v1/products/{product_id}/promotion-links/{link_id}`、`GET /api/v1/r/{tracking_code}`
- 作用：展示服务端 tracking code、公开 302 跳转和点击计数。
- 应看到：active 链接；每次公开跳转新增 Click 并原子增加 `click_count`。

## 10 Ad Recommendation

- API：`GET /api/v1/products/{product_id}/ad-recommendations/{recommendation_id}`
- 作用：展示基于现有数据生成、由管理员人工确认的投放建议。
- 应看到：`confirm_status=confirmed` 和合法 `confirmed_by`；确认不代表真实广告已投放。

## 11 Ad Experiment

- API：`GET /api/v1/products/{product_id}/ad-experiments/{experiment_id}`
- 作用：展示从 confirmed Recommendation 生成并人工推进的实验计划。
- 应看到：绑定 approved Asset 和 active Link，最终状态 `finished`；运行状态仅是业务记录。

## 12 Performance Record

- API：`GET /api/v1/products/{product_id}/performance-records`
- 作用：展示三个 Demo 周期的曝光、点击、转化、支出和收入。
- 应看到：CTR、CVR、ROI 由系统使用 Decimal 计算，不从推广累计点击或请求体复制。

## 13 Review Report

- API：`GET /api/v1/products/{product_id}/review-reports/{report_id}`
- 作用：展示程序聚合经营数据后由 Mock LLM 解释的结构化复盘。
- 应看到：摘要、数据证据、问题判断、下一步动作和可追溯输入快照；不会自动开始下一轮业务。

## 自动 Smoke Test

```powershell
python -m scripts.smoke_test_demo_flow --username admin
```

输出 `PASS` 表示以上关键对象和状态均通过真实 HTTP API 验证。该脚本不直连数据库；是否使用 PostgreSQL 取决于正在运行的 FastAPI 配置。
