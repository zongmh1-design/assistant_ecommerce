# OpenAI-compatible LLM Provider 实际验证记录

验证日期：2026-09-16

## 依赖身份

- requirements 包名：`httpx2==2.13.0`
- Python import：`import httpx2`
- 已安装版本：2.13.0
- 项目使用位置：`OpenAICompatibleLLMProvider`、集中 Provider factory 和 HTTP Fake tests
- 选型记录：Phase 4B 将其作为不引入 AI Framework 的轻量 HTTP 客户端

`httpx2` 是 PyPI 上独立发布的包，由 Pydantic 维护并声明为原 HTTPX 工作的延续；它不是通常所说、以 `import httpx` 使用的传统 `httpx` 包。当前项目没有安装传统 `httpx`。

## 实际网络结果

Provider type：`openai_compatible`

HTTP client：`httpx2 2.13.0`

- `httpx2` 请求外部 HTTPS 测试地址：HTTP 200，HTTP/1.1，响应体非空。
- Python 标准库请求同一地址：HTTP 200。
- 现有 Provider 请求 OpenAI 官方 Chat Completions endpoint，使用明确无效的测试密钥：稳定映射为 `LLMAuthenticationError`。
- 未向真实 endpoint 发送 invalid model 请求；当前没有合法认证配置。现有 MockTransport 的 HTTP 400 测试确认该路径映射为 `LLMProviderError` 且不重试。
- 请求和异常输出没有打印 API Key、Authorization Header、Prompt 或响应正文。

结论：`httpx2` 的外部 HTTPS、TLS 和 Provider 401/403 映射路径可以工作。Phase 14 的 localhost 空 502 风险仍然存在，但没有在外部 HTTPS 请求中复现，因此本阶段暂不迁移到传统 `httpx`。

## Structured Output

本机当前没有 `.env`，以下配置均未提供：

- `LLM_PROVIDER`
- `LLM_BASE_URL`
- `LLM_API_KEY`
- `LLM_MODEL`
- `LLM_TIMEOUT_SECONDS`
- `LLM_MAX_RETRIES`

因此没有来源可靠且经授权的真实模型可调用。本轮没有伪造：

- HTTP 200 的模型响应
- 纯 JSON 或 Markdown fenced JSON 类型
- 真实 Pydantic structured output 成功
- usage metadata

现有自动测试继续覆盖纯 JSON、Markdown fenced JSON、非法 JSON、缺少 Schema 字段、401/403/429/5xx、timeout、network error 和有限重试。

自动化结果：

- Provider 专项：`23 passed, 1 warning`
- 完整项目：`338 passed, 6 skipped, 1 warning`
- 编译检查与 `pip check`：通过
- 敏感信息扫描：未发现 credential-shaped secret

## ProductDiagnosis

状态：未执行真实模型验证。

原因：缺少合法 endpoint、API Key 和 model。没有调用来源不明的公共 API，也没有把 Mock 结果写成真实 Provider 成功。

待具备本地合法配置后，验证顺序为：

1. 运行 `python -m scripts.test_llm_provider`。
2. 确认 request、JSON parse、Pydantic validation 均成功。
3. 只对 Demo Product 调用一次 ProductDiagnosis 生成 API。
4. 核对 `source_type=ai`、`provider_name=openai_compatible`、实际 `model_name` 和可选 `usage_json`。

## 当前结论

- Provider 外部网络和认证错误映射：成功。
- 真实模型 structured output：未验证。
- ProductDiagnosis 真实落库：未验证。
- httpx2：暂时保留。
- 业务架构、数据库和 Migration：未修改。
