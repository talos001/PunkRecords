# 后端 Chat + LLM（方案 2+3 轻量版）实现计划

依据：[backend-chat-llm-adapter-design.md](./backend-chat-llm-adapter-design.md)。

## 目标

在 **P0（方案 A）** 内：`POST /chat` 完成「校验 → 材料落盘 → 按 ChatProfile 调用 LLM → 返回 `ChatResponse`」；`job_ids` 为空；不抓取 URL、不调用 `BaseAgent.ingest`。

## 依赖

- **新增**：任选其一先打通（推荐 **Anthropic**，与默认 `agent_id=claude_code` 语义一致）：
  - `anthropic` 官方 SDK，或
  - `openai` / `httpx` 直连兼容接口（若你更熟 OpenAI 形态）。
- **已有**：`fastapi`、`python-multipart`、`httpx`（dev）、`pyyaml`。

在 `pyproject.toml` 中加入选定 SDK；CI 与无密钥环境用 **FakeLLMProvider** 跑通测试。

## 配置与进程模型

当前 `src/api/app.py` **未**加载 YAML。计划：

1. 支持环境变量 **`PUNKRECORDS_CONFIG`**：若存在且文件可读，则 `load_config()`，否则使用**仅含默认占位**的内联默认（开发易踩坑，文档需写明）。
2. 扩展 `src/config.py` 的 `Config`：
   - `materials_vault_path`（已有）
   - `llm_provider`：如 `anthropic` | `openai` | `fake`（测试/无密钥）
   - `llm_model`：默认模型 id
   - `llm_timeout_seconds`：默认 60～120
   - API Key：**优先环境变量** `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`，YAML 内 `agent_api_key` 可作为备选（与现字段对齐时注意命名，避免重复两套键）。

3. **FastAPI `lifespan` 或 `app.state`**：挂载 `ChatDependencies`（config、provider registry、material vault 根路径），`router` 通过 `Request` 或 `Depends()` 获取，避免全局单例隐式状态（测试可注入 fake）。

## 建议目录与职责

| 路径 | 职责 |
|------|------|
| `src/llm/types.py` | `Message`（role/content）、`CompletionResult`（text + 可选字段） |
| `src/llm/base.py` | `Protocol` / ABC：`LLMProvider.complete(...)` |
| `src/llm/providers/anthropic_provider.py` | Anthropic 实现（首版） |
| `src/llm/providers/fake_provider.py` | 固定返回，供单测与无密钥 CI |
| `src/llm/registry.py` | `provider_id` → 构造 `LLMProvider`（读 config + env） |
| `src/api/chat_profiles.py` | `agent_id` → `ChatProfile`（system_prompt, temperature, optional model override, optional provider_id） |
| `src/api/chat_materials.py` | 将 `text` + `UploadFile` 保存到 `{materials_vault}/{domain_id}/incoming/{yyyy-mm-dd}/{uuid}/`，文件名消毒、大小上限（可配置） |
| `src/api/chat_service.py` | `run_chat(...)`：落盘 → 拼 user 内容 → 解析 profile → `registry.get(...).complete(...)` → 组装 `ChatMessageOut` / `ChatResponse` |
| `src/api/v1/router.py` | 调用 `chat_service`，捕获 LLM 异常映射为 `502/503` + 统一 `error` JSON |

**不新增**：`BaseAgent` 改动、异步队列、URL 抓取（留待 Plan B/C）。

## 实现顺序（建议）

1. **类型与协议**（`types.py` + `base.py`）+ **FakeProvider** + **registry 骨架**（`fake` 可实例化）。
2. **扩展 Config + 示例 `config.example.yaml`**（仓库内示例，真实路径由用户填写）+ `app.state` 注入。
3. **`chat_profiles.py`**：三张 profile，与 `agents_registry` 中 id 一致；文案可中文短 system。
4. **`chat_materials.py`**：落盘 + 单元测试（临时目录 `tmp_path`）。
5. **`chat_service.py`**：串联 fake provider，测端到端消息组装与 `ChatResponse`。
6. **AnthropicProvider**（或 OpenAI）：真实 SDK + 超时；集成测试 `pytest -m integration` 可选跳过。
7. **`router.post("/chat")`**：替换占位逻辑；LLM 失败 **不**向前端泄露密钥与 traceback。

## 测试清单

- [ ] `tests/test_chat_materials.py`：空文件列表、多文件、文件名 `../` 消毒。
- [ ] `tests/test_chat_service.py`：FakeProvider 断言 `messages` 含 system + user，且 user 含正文与附件说明。
- [ ] `tests/test_chat_api.py`：`httpx.AsyncClient` 对 `POST /api/v1/chat`（app 注入 fake）返回 200 与合法 JSON。
- [ ] （可选）`tests/test_chat_integration.py`：`@pytest.mark.integration`，需环境变量密钥。

## 验收标准

- 配置有效且密钥正确时，前端 `POST /chat` 得到模型真实回复（非占位模板）。
- 无密钥时：文档说明如何用 `llm_provider: fake` 或 env 启动；测试全绿。
- `GET /api/v1/*` 现有行为不变。

## 后续（本计划不执行）

- **Plan B**：URL 抓取、`BaseAgent.ingest`、索引 Vault。
- **Plan C**：`job_ids`、任务存储、`GET /jobs/{id}`。

## 修订记录

| 日期 | 摘要 |
|------|------|
| 2026-04-12 | 初稿：依赖、配置、目录、顺序、测试、验收 |
