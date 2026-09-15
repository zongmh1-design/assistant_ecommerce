# 技术与业务决定

本文件记录已经确认、会影响后续实现的重要决定。未确认事项不得写成既定事实。

## 已确认

### D-001：第一版采用简单单体架构

- **状态**：已确认
- **原因**：项目强调业务清晰、可运行、可演示和本人可解释。
- **结果**：采用 `API → Service → Repository → Database` 分层；AI 与外部平台通过接口适配；不引入微服务。

### D-002：按阶段创建数据库表和代码模块

- **状态**：已确认
- **原因**：一次性建立全部表会增加理解和修改成本，也无法逐阶段验证业务。
- **结果**：表分四批设计，并在对应 Phase 到来时才创建 ORM 和迁移。

### D-003：第一版以单个商品闭环为主线

- **状态**：已确认
- **原因**：确保核心运营过程可以完整演示。
- **结果**：`Product` 是诊断、方案、任务、素材、投放、经营数据和报告的中心归属对象；`Store 1:N Product` 仍保留自然扩展能力。

### D-004：外部平台能力明确 Mock 或不接入

- **状态**：已确认
- **原因**：优先验证自身业务系统，并遵守授权、安全和平台规则。
- **结果**：真实电商授权、商品 API 使用 Mock；竞品使用手工、Mock 或示例数据；图片/视频生成允许 Mock；广告平台不真实接入。

### D-005：AI 输出结构化且允许人工修改

- **状态**：已确认
- **原因**：业务结果需要校验、保存、追溯和人工负责。
- **结果**：优先使用 Pydantic Schema；模型适配与业务 Service 分离；失败不能伪装成成功内容。

### D-006：Phase 1 后端技术栈

- **状态**：已确认
- **结果**：Python 3.12、venv、pip + `requirements.txt`、FastAPI、SQLAlchemy 2.x、Alembic、PostgreSQL、REST、Pydantic 和 pytest。Phase 1 不开发前端。

### D-007：认证和权限方式

- **状态**：已确认
- **结果**：密码使用 Argon2 安全哈希；登录签发 JWT Bearer Access Token，包含 `user_id`、`role`、`exp`；Phase 1 不实现 Refresh Token。访问时重新读取用户状态和角色，旧 Token 在用户禁用或角色变化后失效。

### D-008：全局数据约定

- **状态**：已确认
- **结果**：数据库主键使用整数自增 ID；时间以带时区 `datetime` 按 UTC 存储；金额使用 Python `Decimal` 和数据库 `NUMERIC/DECIMAL`；第一版不做全局软删除，有历史保留要求时优先使用状态字段。

### D-009：平台字段与 Store 删除边界

- **状态**：已确认
- **原因**：第一版平台集合很小，不值得建立复杂平台系统；商品属于店铺且后续会产生历史数据。
- **结果**：Store/Product 平台使用 Python Enum 和数据库 `VARCHAR + CHECK`，不使用 PostgreSQL 原生 ENUM。新增平台需要新迁移调整 CHECK。`products.store_id` 使用非空外键和 `ON DELETE RESTRICT`，不使用 CASCADE DELETE；Phase 2A 不提供删除接口。

### D-010：库存初始化、停用写入与并发边界

- **状态**：已确认
- **原因**：库存必须同时具备当前状态和可追溯流水，但培训项目暂不需要复杂仓储或并发框架。
- **结果**：创建 SKU 时在同一事务中生成零库存 `InventoryItem` 和 `initial` 流水；库存调整在同一事务中修改库存并新增流水。inactive SKU 允许读历史但禁止库存写入。Phase 2B 不加行锁或乐观锁，因此并发调整仍可能发生 lost update；真实并发出现时优先在 PostgreSQL 库存读取处使用 `SELECT ... FOR UPDATE`，或在需要无锁冲突检测时增加 optimistic locking 版本字段。

### D-011：公开链接解析结果必须人工确认

- **状态**：已确认
- **原因**：公开页面数据可能缺失、过时或解析错误，未经确认写入正式竞品会污染后续商品诊断输入。
- **结果**：`PublicLinkParseTask` 只保存解析预览和错误信息。仅 succeeded 任务可以由 admin/operator 明确确认；确认时以 PostgreSQL 行锁读取任务，创建 `Competitor` 与写入 `confirmed_competitor_id` 在同一事务中完成，避免重复确认。业务 Service 只依赖 `PublicLinkParser` 接口，当前注入不访问网络且明确标记为 `mock_demo` 的实现。

## 待确认

- Phase 2 开始前确认商品 URL、图片列表等字段的具体输入边界。
- 前端框架在进入前端开发阶段前确认。
