# PostgreSQL 实际运行验收记录

验收时间：2026-09-16 18:56:56 +08:00

## 运行环境

- Docker Desktop Engine：29.2.1
- Docker Compose：v5.0.2
- PostgreSQL 镜像：`postgres:16-alpine`
- PostgreSQL Server：16.15
- 验收 Compose project：`assistant-ecommerce-phase14`
- 宿主端口：`55432`（避免占用默认 5432）
- 最终容器状态：`healthy`
- FastAPI：本机 Python venv，监听 `127.0.0.1:8014`
- LLM Provider：`mock`

验收使用独立的新 Docker volume。迁移前查询 `public` schema 的表数为 0，没有复用已有业务库。

## Migration

真实连接 PostgreSQL 执行：

- `alembic upgrade head`：从 `20260915_0001` 连续执行到 `20260916_0014`，成功。
- `alembic current`：`20260916_0014 (head)`。
- `alembic check`：`No new upgrade operations detected.`

没有新增或修改历史 Migration。

## 实际表检查

通过容器内 `psql` 查询 `information_schema.tables`，确认 `public` schema 共 20 张表（含 `alembic_version`）。业务表包括：

- `users`、`stores`、`products`
- `product_skus`、`inventory_items`、`inventory_movements`
- `competitors`、`public_link_parse_tasks`
- `product_diagnoses`、`creative_plans`
- `generation_jobs`、`generation_job_events`
- `generated_assets`
- `promotion_links`、`promotion_link_clicks`
- `ad_recommendations`、`ad_experiments`
- `performance_records`、`review_reports`

## 约束与 PostgreSQL 特性

实际查询 `pg_constraint` 与 `pg_indexes`，确认：

- 所有业务外键均为 `ON DELETE RESTRICT`。
- `uq_creative_plans_selected_product_type` 是带 `WHERE status = 'selected'` 的部分唯一索引。
- 通过 Service 切换 selected 成功；直接制造同 Product + plan_type 双 selected 时，PostgreSQL 抛 `UniqueViolation`。
- `uq_generated_assets_generation_job_id` 存在。
- `uq_generated_assets_plan_type_version` 存在；事务内插入重复版本时 PostgreSQL 拒绝，测试随后回滚。
- `uq_promotion_links_tracking_code` 是唯一索引。
- GenerationJob、Inventory、GeneratedAsset、PerformanceRecord、ReviewReport 等关键 CHECK 均实际存在。
- AdRecommendation 与 AdExperiment 的 Repository `SELECT ... FOR UPDATE` 在 PostgreSQL 事务中正常执行。

## FastAPI、管理员与 Demo

- 使用 `scripts.create_admin` 创建本地验收管理员，未执行 SQL INSERT，密码只保存 Argon2 哈希。
- FastAPI 使用 PostgreSQL DATABASE_URL 启动成功，没有 SQLite fallback。
- 第一次 HTTP Smoke 调用 Demo Data：`PASS`，`demo_status=completed`。
- 第二次 HTTP Smoke：`PASS`，相同 `product_id=1`、`review_report_id=1`，`demo_status=already_exists`。
- Demo 全链包含 Store、Product、SKU/Inventory、Competitor、Diagnosis、CreativePlan、GenerationJob、GeneratedAsset、PromotionLink、AdRecommendation、AdExperiment、PerformanceRecord 和 ReviewReport。

首次 Smoke 暴露 `httpx2 2.13.0` 对本机请求返回空 502、请求未到 FastAPI 的运行兼容问题。只将 Smoke 客户端改为 Python 标准库 HTTP 客户端；业务 API、LLM Provider 和领域流程没有改动。

## 并发与事务验证

- 两个独立 SQLAlchemy Session 并发运行同一个 pending GenerationJob。
- 最终只有一个请求成功领取并执行。
- 数据库中该 Job 的 `attempts=1`，`started` Event 只有 1 条。
- 证明当前 PostgreSQL `SELECT FOR UPDATE` 路径能够阻止重复领取；这不是大规模压力测试。

对公开 PromotionLink 发起多轮有限并发验收，其中单轮为 12 个并发 HTTP 请求：

- 最终 `promotion_links.click_count=41`。
- 对应 `promotion_link_clicks` 明细数为 41。
- 原子 `click_count = click_count + 1` 与 Click INSERT 保持一致。

## NUMERIC 与 JSON

通过现有 `PerformanceRecordService` 写入后由 PostgreSQL 回读：

- `ctr=0.050000`
- `conversion_rate=0.100000`
- `roi=0.500000`
- `pg_typeof(ctr)=numeric`

`ReviewReport.input_context_json` 回读为 JSON object，并包含 `aggregated_performance`。其中 Decimal 已由应用按现有 Context Schema 正确序列化。

## 自动化结果

- PostgreSQL integration tests：`6 passed, 1 warning`。
- 完整 SQLite 回归：`338 passed, 6 skipped, 1 warning`；6 项仅在显式配置 PostgreSQL 时运行。
- 编译检查：通过。
- `pip check`：`No broken requirements found.`
- OpenAPI：60 个 path，关键路径存在。
- 敏感信息扫描：未发现 credential-shaped secret；`.env` 仍被 Git 忽略。
- `git diff --check`：通过，仅有 Windows LF/CRLF 提示。

## 当前仍未验证

- 未使用真实 LLM API；本轮按范围使用 MockLLMProvider。
- 未验证真实电商平台、广告平台、图片/视频模型或对象存储。
- 未做高并发压力测试、故障转移、备份恢复或生产环境容量测试。
- 未把 FastAPI 容器化；本阶段有意只容器化 PostgreSQL。
- 未验证前端，因为当前后端业务已冻结且本阶段不包含前端。
