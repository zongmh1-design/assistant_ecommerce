# E-commerce Operations Assistant

电商运营助手是面向中小电商团队的运营工作台。当前已完成 **Phase 3A：Competitor + Public Link Parse Task**，包含认证权限、店铺、商品、SKU、库存、竞品和公开链接 Mock 解析预览；尚未开发商品诊断、AI 或前端。

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

执行第一份迁移：

```powershell
python -m alembic upgrade head
```

该迁移创建 `users` 和 Alembic 版本表。应用代码不会通过 `create_all()` 自动建生产表。

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

## 6. 角色权限

- `admin`：管理员专属能力和普通写操作。
- `operator`：普通写操作，不能执行管理员专属能力。
- `viewer`：只读，不能执行写操作。

业务接口通过统一的 `require_admin` 或 `require_write_access` 依赖声明权限，不在每个接口散写角色判断。

## 7. 运行测试

```powershell
python -m pytest -q
```

测试使用隔离的内存 SQLite 作为 Repository/HTTP 行为测试替身，不会连接或修改本地 PostgreSQL。正式迁移仍以 PostgreSQL 方言定义，并应在本地 PostgreSQL 空库执行一次。

## 8. 当前范围

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
- 四份连续 Alembic 迁移和交互式初始管理员脚本。

未实现：Refresh Token、用户管理 API、前端、PlatformAccount、PlatformProductMapping、真实爬虫、竞品定时监控、AI、图片/视频生成和广告能力。

完整阶段计划见 `docs/PROGRESS.md`。
