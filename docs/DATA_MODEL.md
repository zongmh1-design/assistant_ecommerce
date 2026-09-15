# 数据模型设计

## 1. 设计原则

- 当前只做概念设计，不创建 ORM Model、迁移或数据库表。
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

说明：Phase 1 只创建 `users`；Phase 2 再增加 `stores`、`products`。同属第一批不代表在同一次迁移中全部创建。

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

### 第三批 AI 和素材表（Phase 5–8）

进入 AI 方案和素材任务开发后增加。

| 表 | 主要职责 | 主要关系 |
| --- | --- | --- |
| `product_diagnoses` | 保存商品诊断输入来源、结构化结果和编辑后版本 | 多次诊断归属一个商品 |
| `creative_plans` | 统一保存主图方案和视频脚本 | 多个方案归属一个商品，可引用某次诊断 |
| `generation_jobs` | 图片/视频异步生成任务、状态、尝试次数和结果 | 归属商品，并关联一个创意方案 |
| `generation_job_events` | 任务状态变化和错误时间线 | 多个事件归属一个生成任务 |
| `generated_assets` | 成功生成的图片/视频及人工审核信息 | 归属商品和创意方案，可追溯到生成任务 |

`creative_plans.plan_type` 区分 `main_image` 与 `video_script`；不分别建立两套高度重复的方案表。

### 第四批投放和经营分析表（Phase 9–11）

素材能力稳定后，再增加推广、投放实验、经营数据和复盘。

| 表 | 主要职责 | 主要关系 |
| --- | --- | --- |
| `promotion_links` | 目标链接、追踪码、场景和点击汇总 | 多个链接归属一个商品 |
| `promotion_link_clicks` | 单次点击的时间及有限客户端信息 | 多条点击归属一个推广链接 |
| `ad_recommendations` | 结构化投放建议及人工确认记录 | 多次建议归属一个商品，确认人关联用户 |
| `ad_experiments` | 已确认建议对应的实验计划与状态 | 归属商品，可关联建议、素材和推广链接 |
| `performance_records` | 商品在某周期的曝光、点击、转化、花费和收入 | 归属商品，可选关联方案、素材、链接和实验 |
| `review_reports` | 某周期的结构化经营分析和下一步动作 | 归属商品，基于一组经营记录和关联运营数据 |

## 3. Store、Product、ProductSku 重点关系

```text
Store 1 ──────< Product 1 ──────< ProductSku
  │                 │                  │
  │                 │                  ├── 1 InventoryItem
  │                 │                  └── N InventoryMovement
  │                 └── N 后续运营对象
  └── N PlatformAccount
```

### Store → Product

- 一个 `Store` 可以拥有多个 `Product`。
- 一个 `Product` 必须且只属于一个 `Store`，通过 `products.store_id` 关联。
- 删除策略在实现前单独确认；默认不做物理级联删除，优先使用状态停用，避免丢失运营历史。

### Product → ProductSku

- 一个 `Product` 可以拥有多个 `ProductSku`。
- 一个 `ProductSku` 必须且只属于一个 `Product`，通过 `product_skus.product_id` 关联。
- `Product.price/cost` 表示商品展示或默认值；SKU 可保存自己的实际价格和成本。存在 SKU 时，交易与库存计算优先使用 SKU 值。
- `sku_code` 建议在商品范围内唯一；是否需要店铺级唯一约束在 Phase 3 确认。

### ProductSku → Inventory

- 第一版一个 SKU 对应一个 `InventoryItem` 汇总当前库存，不提前支持多仓。
- 每次调整库存都同时新增一条 `InventoryMovement`，记录 `before_qty`、`change_qty`、`after_qty`、原因和业务来源。
- `available_qty` 建议由 `stock_qty - locked_qty` 计算，不重复持久化，避免值不一致。

## 4. 其他关键关系

- `Product 1:N Competitor`：竞品只在其对标商品上下文中有意义。
- `Product 1:N ProductDiagnosis`：保留历史诊断，不覆盖旧记录。
- `Product 1:N CreativePlan`：同一商品有多轮、多类型方案。
- `CreativePlan 1:N GenerationJob`：允许同一方案重试或生成多个版本。
- `GenerationJob 1:N GenerationJobEvent`：事件构成任务审计时间线。
- `GenerationJob 1:N GeneratedAsset`：一个任务可产生多个素材；素材同时关联商品和方案便于查询。
- `Product 1:N AdRecommendation`：建议保留历史；状态记录人工确认结果。
- `AdRecommendation 1:N AdExperiment`：只允许从已确认建议创建实验计划。
- `Product 1:N PerformanceRecord` 与 `Product 1:N ReviewReport`：按周期积累经营数据和分析结果。

## 5. 待实现阶段确认的约束

- 主键类型使用自增整数还是 UUID。
- 第一版使用 SQLite 还是 PostgreSQL。
- 软删除策略以及哪些对象只允许停用/归档。
- 金额、比例、时区字段的数据库精度和统一约定。
- AI 输入快照、Schema 版本和人工编辑版本的具体字段。
- 导入批次是否需要独立 `import_batches` / `import_row_results` 表；应在 Phase 10 根据实际审计需求决定，而不是现在提前创建。
