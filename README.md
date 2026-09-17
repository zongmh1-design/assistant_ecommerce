# E-commerce Operations Assistant

电商运营助手是面向中小电商团队的运营工作台。当前已完成 **Phase 13：完整后端演示与验收链路**。系统可以从管理员登录开始，通过现有业务 Service 初始化并核验一条完整单品运营闭环。

## Quick Start

下面步骤只依赖项目仓库、Python 3.12 和 PostgreSQL，不包含开发者本机绝对路径。

## 当前技术栈

- Python 3.12、venv、pip + `requirements.txt`
- FastAPI、Pydantic
- SQLAlchemy 2.x、Alembic、PostgreSQL
- Argon2 密码哈希、JWT Bearer Access Token
- pytest

## 1. 创建 Python 环境

在项目根目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

确认解释器版本：

```powershell
python --version
```

应为 Python 3.12。

## 2. 初始化 PostgreSQL

先在本机安装并启动 PostgreSQL。使用具备建库权限的账号进入 `psql`：

```sql
CREATE ROLE ecommerce_app LOGIN PASSWORD '<your-local-password>';
CREATE DATABASE ecommerce_assistant OWNER ecommerce_app;
```

复制环境变量示例：

```powershell
Copy-Item .env.example .env
```

生成 JWT 随机密钥：

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

将输出仅写入本地 `.env` 的 `JWT_SECRET_KEY`，并把 `DATABASE_URL` 中的示例密码替换为本地数据库密码。`.env` 已被 Git 忽略，禁止提交。

执行全部迁移：

```powershell
python -m alembic upgrade head
```

迁移会从空库创建当前全部业务表。应用代码不会通过 `create_all()` 自动建生产表。

## 3. 创建第一个管理员

迁移成功后运行交互式脚本：

```powershell
python -m scripts.create_admin --username admin --display-name "Administrator"
```

脚本会隐藏密码输入、要求二次确认并使用 Argon2 保存哈希。没有开放公网创建管理员接口。

## 4. 启动应用

```powershell
python -m uvicorn app.main:app --reload
```

可访问：

- 健康检查：`http://127.0.0.1:8000/health`
- Swagger：`http://127.0.0.1:8000/docs`
- ReDoc：`http://127.0.0.1:8000/redoc`

`/health` 是应用存活检查，不代表 PostgreSQL 一定可连接。

## 5. 登录并访问当前用户

登录请求使用 JSON：

```powershell
$loginBody = @{
    username = "admin"
    password = "<your-password>"
} | ConvertTo-Json

$loginResult = Invoke-RestMethod `
    -Method Post `
    -Uri "http://127.0.0.1:8000/api/v1/auth/login" `
    -ContentType "application/json" `
    -Body $loginBody
```

使用返回的 Access Token：

```powershell
$authHeaders = @{ Authorization = "Bearer $($loginResult.access_token)" }
Invoke-RestMethod `
    -Method Get `
    -Uri "http://127.0.0.1:8000/api/v1/auth/me" `
    -Headers $authHeaders
```

JWT 只包含 `user_id`、`role` 和 `exp`。`/auth/me` 会重新读取数据库中的用户状态和角色；用户禁用或角色变化后，旧 Token 不能继续获得原权限。

## 6. 初始化 Demo Data

保持应用正在运行，使用登录返回的管理员 Token：

```powershell
$demo = Invoke-RestMethod `
    -Method Post `
    -Uri "http://127.0.0.1:8000/api/v1/workspace/demo-data" `
    -Headers $authHeaders

$demo
```

接口只允许 `admin`，会通过现有 Service 创建或继续完成 Demo 单品闭环。重复调用返回稳定对象 ID，不会重复创建整套数据。

## 7. 运行 HTTP Smoke Test

Smoke Test 只访问正在运行的 HTTP API，不直接连接数据库：

```powershell
python -m scripts.smoke_test_demo_flow --username admin
```

脚本会安全提示输入密码，最终输出 `PASS` 或失败步骤；不会打印密码、JWT、API Key 或 Authorization Header。完整演示顺序见 `docs/DEMO.md`。

## 8. 角色权限

- `admin`：管理员专属能力和普通写操作。
- `operator`：普通写操作，不能执行管理员专属能力。
- `viewer`：只读，不能执行写操作。

业务接口通过统一的 `require_admin` 或 `require_write_access` 依赖声明权限，不在每个接口散写角色判断。

## 9. LLM Provider 配置

默认 Mock 模式不访问网络，也不需要 API Key：

```dotenv
LLM_PROVIDER=mock
```

需要人工验证一个合法的 OpenAI-compatible Chat API 时，只在本地 `.env` 中设置：

```dotenv
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=https://example.com/v1
LLM_API_KEY=
LLM_MODEL=your-model
LLM_TIMEOUT_SECONDS=30
LLM_MAX_RETRIES=2
```

`example.com`、空 Key 和 `your-model` 都是占位值，不能直接调用真实模型。把真实 Key 只写入已被 Git 忽略的本地 `.env`，不要写入代码、README、测试或提交记录。

配置完成后先执行最小人工连通验证：

```powershell
python -m scripts.test_llm_provider
```

脚本只打印成功状态、Provider 和模型名称，不打印 API Key、Authorization Header、Prompt 或原始响应。验证成功后，原有诊断 API 无需改变：

```text
POST /api/v1/products/{product_id}/diagnoses/generate
```

配置错误会明确失败，不会静默回退 Mock。

## 10. Real LLM Provider Validation

只在本地 `.env` 配置合法的 OpenAI-compatible endpoint、API Key 和模型：

```dotenv
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=https://example.com/v1
LLM_API_KEY=
LLM_MODEL=your-model
```

然后主动执行：

```powershell
python -m scripts.test_llm_provider
```

脚本会明确显示 `REAL NETWORK VALIDATION`，并验证 HTTP、JSON 解析和 Pydantic Schema；不会打印 API Key、Authorization Header、完整 Prompt 或原始响应。该操作会产生真实网络请求，具体 endpoint 可能产生费用。没有合法配置时脚本明确退出，不会回退 Mock。

实际验证范围和结果见 `docs/LLM_PROVIDER_VALIDATION.md`。

## 11. 运行测试

```powershell
python -m pytest -q
```

测试使用隔离的内存 SQLite 作为 Repository/HTTP 行为测试替身，不会连接或修改本地 PostgreSQL。正式迁移仍以 PostgreSQL 方言定义，并应在本地 PostgreSQL 空库执行一次。

## 12. Local PostgreSQL Verification

下面只把 PostgreSQL 放入 Docker；FastAPI 仍在本机 Python `venv` 中运行，便于定位连接、迁移和应用问题。

1. 启动 PostgreSQL 16，并等待状态变为 `healthy`：

```powershell
docker compose up -d postgres
docker compose ps
```

2. 从 `.env.example` 复制本地 `.env`，至少替换 `JWT_SECRET_KEY`。默认 Compose 占位账号仅适用于本地开发，生产环境禁止照搬：

```dotenv
DATABASE_URL=postgresql+psycopg://ecommerce_app:local-dev-password-change-me@localhost:5432/ecommerce_assistant
JWT_SECRET_KEY=replace-with-a-private-random-value-at-least-32-characters
LLM_PROVIDER=mock
```

3. 在真实 PostgreSQL 空库执行完整迁移并核对迁移状态：

```powershell
python -m alembic upgrade head
python -m alembic current
python -m alembic check
```

4. 使用现有安全脚本创建管理员，再启动连接 PostgreSQL 的 FastAPI：

```powershell
python -m scripts.create_admin --username admin --display-name "Administrator"
python -m uvicorn app.main:app
```

5. 在另一个终端登录后调用 `POST /api/v1/workspace/demo-data`，再运行真实 HTTP Smoke Test：

```powershell
python -m scripts.smoke_test_demo_flow --username admin
```

重复执行 Smoke Test 会再次调用 Demo Data API，并验证其返回同一套 Demo 根对象而不是复制整套数据。

6. 可选 PostgreSQL integration tests 默认跳过。仅对已迁移且可丢弃的本地验收库显式运行：

```powershell
$env:TEST_POSTGRES_DATABASE_URL = $env:DATABASE_URL
$env:TEST_API_BASE_URL = "http://127.0.0.1:8000"
python -m pytest tests/integration/test_postgres_runtime.py -q
```

测试会检查实际 catalog、部分唯一索引、`SELECT FOR UPDATE`、并发 Job 领取、原子点击计数和 NUMERIC/JSON 行为，并会向验收库增加少量测试数据。

无需在 Windows 主机安装 `psql`；可使用容器内客户端：

```powershell
docker compose exec postgres psql -U ecommerce_app -d ecommerce_assistant
```

停止容器：

```powershell
docker compose down
```

仅在确认这是本地开发数据后，才使用下面命令删除本项目 Docker volume 并从空库重验：

```powershell
docker compose down -v
docker compose up -d postgres
python -m alembic upgrade head
```

实际验收结果见 `docs/POSTGRES_VALIDATION.md`。

## 13. 当前范围与 Mock 边界

已实现：

- FastAPI 应用入口、配置、数据库 Session、SQLAlchemy Base、全局业务异常结构。
- `/health`、`POST /api/v1/auth/login`、`GET /api/v1/auth/me`。
- `User`、三角色、用户状态、Argon2 密码哈希、JWT Access Token。
- Store 创建、分页查询、详情和局部更新。
- Product 创建、分页查询、详情和局部更新，以及 `store_id/platform/status` 筛选。
- `Store 1:N Product` 非空外键关系；禁止数据库级级联删除。
- ProductSku 创建、查询和修改，以及商品内唯一 SKU 编码。
- 创建 SKU 自动初始化 InventoryItem 和 initial 流水。
- 库存调整、库存设置、available_qty 计算和分页流水查询。
- Competitor 手工录入、分页查询、详情和局部更新。
- PublicLinkParseTask 创建、同步运行、结果查询和人工确认。
- 可替换 `PublicLinkParser` 接口及明确标记为演示数据的 Mock 实现。
- Product + Competitors 白名单诊断 Context、独立 Prompt 和严格输出 Schema。
- 可替换 `LLMProvider`、确定性 `MockLLMProvider`、历史诊断查询和人工编辑。
- 可配置 `OpenAICompatibleLLMProvider`、明确超时、有限重试、JSON/fenced JSON 解析和稳定错误边界。
- 诊断保存 Provider、模型名称和可选 Token usage 元数据。
- 统一 `CreativePlan` 保存主图方案和视频脚本；每次严格生成 3 条独立草稿。
- 创意方案白名单输入 Context、Provider/模型/用量元数据和生成输入快照。
- 创意方案分页筛选、详情、人工编辑，以及同商品同类型最多一个 `selected` 的状态规则。
- GenerationJob 创建、手工执行、失败、重试、pending 取消、超时扫描和事件时间线。
- 可替换 `MediaGenerator` 接口及不访问网络、不创建文件的 Mock 图片/视频实现。
- succeeded Job 到 GeneratedAsset 的显式、幂等、逐 Job 同步和严格结果校验。
- 素材分页筛选、详情、人工审核、版本、0–100 评分、有序去重标签、使用场景和备注。
- 推广参数建议、服务端随机 tracking code、推广链接 CRUD、公开 302 跳转和基础点击明细。
- 结构化 AdRecommendation 历史、Decimal 预算建议、人工编辑，以及不可逆的 confirmed/rejected 决策。
- 从 confirmed Recommendation 生成可追溯 AdExperiment，支持 draft 编辑和受控人工状态流转。
- PerformanceRecord 手工创建、修改、查询和筛选；关联对象归属校验及 running/finished Experiment 约束。
- CTR、Conversion Rate、ROI 的 Decimal 派生计算，`spend=0` 时 ROI 保存为 `NULL`。
- PerformanceRecord XLSX 模板下载、CSV/XLSX 预览、行级校验和逐行独立提交的部分成功导入。
- ReviewReport 确定性指标汇总、结构化 AI 复盘、人工编辑和历史查询。
- admin-only Demo Data 初始化、HTTP-only Smoke Test 和完整单品链路一致性验证。
- 十四份连续 Alembic 迁移、交互式初始管理员脚本和真实 Provider 人工验证脚本。

真实实现：登录与角色权限、数据库持久化、库存流水、业务状态流转、点击跟踪、经营指标计算、文件导入、AI Provider 抽象和完整业务编排。

当前 Mock：默认 LLM、竞品公开链接 Parser、图片 Generator、视频 Generator。Demo 中所有平台、竞品、素材和经营数值均明确标记为 Demo/Mock。

当前未接入：Diagnosis/Creative/Asset 等后续业务前端、真实电商平台授权与同步、真实广告执行、真实图片/视频模型、对象存储、Production Worker、Celery/Redis、定时任务。

完整阶段计划见 `docs/PROGRESS.md`，需求对应关系见 `docs/REQUIREMENT_TRACEABILITY.md`。

## 14. Frontend Development

Phase 16A 前端使用 React、TypeScript、Vite、React Router 和 Ant Design。当前包含登录、权限状态、Store/Product 基础页面与 Product Workbench 导航框架。

```powershell
cd frontend
npm install
Copy-Item .env.example .env.local
npm run dev
```

默认 `VITE_API_BASE_URL=/api/v1`，开发服务器会把 `/api` 代理到 `http://127.0.0.1:8000`。如果前后端分别部署，可在本地 `.env.local` 中改为完整 API 地址，例如：

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

不要在前端环境文件中保存 JWT、密码或任何 API Key。Access Token 只保存在当前浏览器标签会话的 `sessionStorage`；后端仍是权限判断的最终边界。

测试与生产构建：

```powershell
npm test
npm run build
```
