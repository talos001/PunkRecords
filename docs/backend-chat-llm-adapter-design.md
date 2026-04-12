# 后端 Chat 与 LLM 适配器设计（P0）

> 仓库内可版本化的设计说明。`docs/superpowers/` 目录被 `.gitignore` 忽略，正式协作以本文件为准。

## 范围与阶段

| 阶段 | 内容 | 与 `api-outline` 对齐 |
|------|------|----------------------|
| **P0（本设计，方案 A）** | `POST /chat`：multipart 解析 → 材料**可靠落盘**到 Material Vault → **单次** LLM 调用返回 `role: assistant` 的模型消息；`job_ids` 恒为空数组；正文中的 URL **不抓取**（可原样进入 prompt 或仅作占位说明） | P0 |
| **后续 Plan B** | 正文/附件中 URL 的抓取、与 ingest 管线对齐（`BaseAgent.ingest`、索引 Vault） | `api-outline` 3.1 说明、`P1` |
| **后续 Plan C** | ingest/建图等慢步骤异步化，返回真实 `job_ids`，实现 `GET /api/v1/jobs/{job_id}` | `api-outline` 5、`P2` |

**时间与时区**：与 `api-outline` 一致，响应中 `created_at` 使用 ISO 8601；建议实现时统一为 **UTC**（与当前 router 行为一致）。

### 架构决策（已确认）

- **2026-04-12**：实现采用 **方案 2 + 方案 3 的轻量子集**——`LLMProvider` 适配器 + 薄路由 + **`agent_id` → ChatProfile** 映射；`BaseAgent` 仍仅用于知识管线（ingest/query/lint），不与聊天补全混写。

---

## 现状与问题

- **HTTP 层**（`src/api/v1/router.py`）已完成参数校验与占位回复，缺少：落盘、LLM 调用、统一的服务边界。
- **领域模型**存在两套「Agent」命名：
  - **`agents_registry`（API）**：侧栏可选的 `agent_id`（`claude_code` / `codex` / `opencode`），面向产品与 UI。
  - **`BaseAgent` + `AgentRegistry`（`src/agent/`）**：`ingest` / `query` / `lint`，面向 Vault 与知识处理，**不是** HTTP 一键聊天的直接形状。
- **结论**：P0 应引入独立的 **LLM 适配层**（见下），避免把「聊天补全」硬塞进现有 `BaseAgent`，以免职责混杂；**Plan B** 再通过编排把 `ingest` 与聊天管线接起来。

---

## 三种架构取向

### 方案 1：路由器直调单一 LLM 客户端

- **做法**：`router` 内直接实例化 Anthropic/OpenAI 客户端并调用。
- **优点**：最少抽象，最快看到端到端。
- **缺点**：扩展多厂商时 `router` 膨胀；难以单测；与「侧栏 agent」正交性弱。

### 方案 2：仅 LLMProvider 适配器 + 薄路由（推荐基座）

- **做法**：定义协议 `LLMProvider`（如 `complete(messages) -> str` 或带 usage 的结构体），各厂商一个实现类；路由只调用 **Chat 编排函数**，编排函数选 provider 再调用。
- **优点**：隔离厂商差异，符合「adapter」诉求；路由保持 HTTP 职责。
- **缺点**：未显式表达「同一模型、不同侧栏人格」时的差异（需额外约定）。

### 方案 3：ChatProfile / Strategy（推荐在方案 2 之上）

- **做法**：`agent_id` → **ChatProfile**（系统提示、温度、可选 `provider_id`、模型名覆盖）；`LLMProvider` 只负责「给定 messages 返回文本」。
- **优点**：侧栏 Agent 与 LLM 厂商**解耦**：可同一 Anthropic 密钥、三套 system prompt；也可某 profile 指向另一厂商。
- **缺点**：多一层配置，P0 可只实现「每 agent 一条 profile 映射表」。

**推荐**：**方案 2 + 方案 3 的轻量子集**——先落地 `LLMProvider` 与一次 **Chat 编排**（命名建议：`ChatService` 或 `handle_chat_request`），用 **`agent_id` → ChatProfile** 的小表实现人格与参数差异；后续 Plan B/C 在同一编排点挂接 URL 与任务队列。

---

## P0 目标架构（组件与数据流）

```
POST /chat (multipart)
    → 校验 domain / agent（保持现有逻辑）
    → Chat 编排
          1. 将 text + 上传文件保存到 Material Vault（按 domain 分子目录，文件名消毒）
          2. 组装 messages：system（来自 ChatProfile）+ user（用户正文 + 附件摘要说明）
          3. 调用当前选中的 LLMProvider.complete(...)
          4. 返回 ChatResponse（message + job_ids=[]）
```

- **不落库索引**：P0 **不**调用 `BaseAgent.ingest` 写索引 Vault；仅保证原材料路径稳定，便于 Plan B 接 ingest。
- **URL**：不发起 HTTP 抓取；可将原文中的 URL 字符串原样交给模型，或在 user 消息前加一句固定说明（产品可再定）。

---

## LLM 适配层（接口建议）

- **协议**（示意，实现时用具体类型名即可）：
  - `LLMProvider.complete(*, messages: list[Message], model: str | None, temperature: float | None, ...) -> CompletionResult`
  - `CompletionResult` 至少含：`text: str`；可选 `finish_reason`、usage，便于观测与计费预留。
- **注册**：`LLMProviderRegistry` 或简单 dict：`provider_id` → 工厂/实例。P0 可先支持 **一个** 厂商（如 Anthropic 或 OpenAI），第二个厂商新增一个类即可。
- **配置**：`llm_base_url`（兼容网关/代理）、`llm_api_key`、`llm_model` 三项；环境变量对应 `PUNKRECORDS_LLM_BASE_URL` / `ANTHROPIC_BASE_URL`、`PUNKRECORDS_LLM_API_KEY` / `ANTHROPIC_API_KEY`、`PUNKRECORDS_LLM_MODEL`；未填 BASE URL 时走 SDK 默认官方端点。

---

## `agent_id` 与 ChatProfile（P0）

- **语义**：HTTP 的 `agent_id` 表示 **对话策略/人设**（prompt + 生成参数 ± 指定 provider）。
- **实现**：静态映射表（代码或 YAML），例如：`claude_code` → system prompt A + 默认模型；`codex` → system prompt B；未实现某厂商前，可 **共用同一 LLMProvider**，仅切换 system prompt（与产品「先跑通」一致，后续再换真实多后端）。

---

## 错误与超时

- **校验错误**：保持现有 `400` + 统一 `error` JSON。
- **LLM 失败**：`502` 或 `503`（可区分超时 vs 上游错误），`message` 人类可读，**不向客户端泄露** API Key 或堆栈细节。
- **超时**：编排层对 `complete` 设默认超时（可配置），超时视为 503/504（择一并在实现中写死）。

---

## 测试策略（P0）

- **单元测试**：`LLMProvider` 使用 **fake/stub** 实现（固定返回字符串），测编排：落盘路径、`messages` 组装、`ChatResponse` 形状。
- **集成测试**（可选）：有密钥时跑单测标记为 integration；CI 默认跳过。

---

## 与既有文档的关系

- 本设计是 **`docs/api-outline.md`** 与高层架构说明在「HTTP Chat + LLM 多后端」上的**落地补充**；不重复描述 Vault 三层全貌。
- **Plan B**：在「编排步骤 1 与 2 之间」插入 URL 解析、抓取、落盘、调用 `BaseAgent.ingest`；必要时返回非空 `job_ids`。
- **Plan C**：将慢步骤拆到 worker，`POST /chat` 快速返回 `202` 或同步返回 + `job_ids`（与 `api-outline` 最终语义对齐时再定）。

---

## 自检

- **占位符**：阶段划分明确；P0 不含 B/C。
- **一致性**：与现有 `BaseAgent` 分工清晰；侧栏 `agent_id` 有明确落点（ChatProfile）。
- **范围**：单实现计划可覆盖「编排 + 一厂商 Provider + 落盘 + 测试」。
- **歧义**：`created_at` 建议 UTC；若前端要强依赖时区，在实现 PR 中与 `api-outline` 修订同步。

---

## 修订记录

| 日期 | 摘要 |
|------|------|
| 2026-04-12 | 初稿：P0 方案 A、LLM 适配器 + Chat 编排、ChatProfile、B/C 后续计划 |
| 2026-04-12 | 确认采用方案 2+3 轻量版（见上文「架构决策」） |
