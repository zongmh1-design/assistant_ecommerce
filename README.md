# E-commerce Operations Assistant

电商运营助手是一个面向中小电商团队的运营工作台。第一版以单个商品为主线，逐步打通店铺、商品、SKU 与库存、竞品、AI 运营方案、素材、投放建议、经营数据和复盘报告。

当前仓库处于 **Phase 0：项目初始化**。本阶段只完成范围、业务流程、数据模型、架构和 AI 边界设计，不包含可运行 API、数据库表、前端页面或真实模型调用。

## 当前内容

- `AGENTS.md`：项目开发与协作规则
- `background_requirement.md`：原始业务需求
- `docs/PROJECT_SCOPE.md`：第一版范围与 Mock 边界
- `docs/BUSINESS_FLOW.md`：单品运营主流程
- `docs/DATA_MODEL.md`：数据表分批设计与关系
- `docs/ARCHITECTURE.md`：简单单体架构
- `docs/AI_DESIGN.md`：AI 功能输入、输出、保存与失败处理
- `docs/PROGRESS.md`：Phase 0–12 开发计划与进度
- `docs/DECISIONS.md`：已确认的重要设计决定

## 业务主线

```text
店铺 → 商品 → SKU / 库存 → 竞品 → 商品诊断 → 主图方案 / 视频脚本
→ 素材生成任务 → 素材审核 → 投放建议 → 人工确认 → 实验计划
→ 经营数据 → 经营分析报告 → 下一轮优化
```

## 开发原则

- 每次只实现一个可验证的小阶段，完成后停止。
- 选择简单、清晰、可解释的单体架构，不引入微服务。
- AI 输出使用结构化 Schema，并允许人工修改后保存。
- 外部电商、素材生成和广告平台在第一版使用 Mock 或不接入。
- 不保存明文平台密码、Token、Cookie 或其他密钥。

## 开始开发前

Phase 1 的技术栈、数据库和认证方式仍需由项目负责人确认。确认后再补充依赖管理、运行命令和环境初始化说明。

详细计划见 `docs/PROGRESS.md`。
