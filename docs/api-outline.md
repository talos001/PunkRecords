# PunkRecords 后端接口需求说明（面向当前 Web UI）

本文档描述 **前端联调所需的后端 API 轮廓**：路径与字段为建议名，实现时可按框架（如 FastAPI）调整，但语义应对齐。

**基础约定**

- 建议前缀：`/api/v1`（或 `/v1`）。
- 请求/响应：`Content-Type: application/json`，UTF-8。
- 文件上传：`multipart/form-data`。
- 时间：ISO 8601 字符串，时区建议 **明确为服务器本地或 UTC** 并在文档中写死。
- 错误：统一 JSON 形如 `{ "error": { "code": "...", "message": "人类可读说明" } }`，HTTP 状态码 4xx/5xx。

**认证（已启用）**

- 使用 JWT：`Authorization: Bearer <access_token>`。
- 受保护接口在未登录时返回：
  - HTTP `401`
  - `{ "error": { "code": "AUTH_REQUIRED", "message": "请先登录" } }`
- 已登录但未完成材料库路径确认时返回：
  - HTTP `428`
  - `{ "error": { "code": "MATERIALS_PATH_CONFIRM_REQUIRED", "message": "...", "details": { "effective_materials_path": "..." } } }`

---

## 0. 认证与启动信息

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/v1/auth/register` | 注册并返回 token 对 |
| `POST` | `/api/v1/auth/login` | 登录并返回 token 对 |
| `POST` | `/api/v1/auth/reset-password` | 按用户名重置密码（本地开发场景） |
| `POST` | `/api/v1/auth/refresh` | 用 refresh token 换新 token 对 |
| `POST` | `/api/v1/auth/logout` | 使当前用户 token 版本失效 |
| `GET` | `/api/v1/me/bootstrap` | 返回当前用户、材料路径确认状态与当前生效路径 |
| `PUT` | `/api/v1/me/materials-path` | 确认默认路径或提交自定义路径并确认生效路径 |

`POST /api/v1/chat`、`POST /api/v1/chat/stream`、`POST /api/v1/ingest`、`GET/PUT /api/v1/settings*` 均为受保护接口。

---

## 1. 健康与版本（运维 / 前端探测）

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/health` | 存活探针，返回 `200` + `{ "ok": true }` |
| `GET` | `/api/v1/version`（可选） | 返回服务与数据格式版本，便于前端做兼容判断 |

---

## 2. 知识领域（`domain_id`）

前端当前在 `frontend/src/domains.ts` 写死列表；**上线后建议由服务端下发**，便于与 Vault 映射、上下线领域一致。

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/domains` | 返回领域列表（见下） |
| `POST` | `/api/v1/domains` | 新增领域（名称、描述、图标与可选路径覆盖） |
| `PATCH` | `/api/v1/domains/{id}` | 编辑领域元数据（名称、描述、图标等） |
| `DELETE` | `/api/v1/domains/{id}` | 归档领域（软删除，保留历史数据） |

**响应示例**

```json
{
  "domains": [
    {
      "id": "early-childhood",
      "name": "幼儿发展",
      "description": "育儿、早教与儿童发展相关",
      "emoji": "🌱",
      "variant": "coral",
      "enabled": true
    }
  ],
  "default_domain_id": "early-childhood"
}
```

- `id`：由后端基于名称自动生成 slug 并下发给前端。
- `emoji` / `variant`：可选；若缺省，前端可回退到本地默认展示。
- `default_domain_id`：与产品策略一致（当前产品默认为幼儿发展）。

### 2.1 创建领域（`POST /api/v1/domains`）

**请求：`application/json`**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 用户可见名称 |
| `description` | string | 否 | 领域描述 |
| `emoji` | string | 否 | 领域图标 |
| `variant` | string | 否 | 前端展示色板 |
| `material_path` | string | 否 | 领域材料目录覆盖；不传时走 fallback |
| `index_path` | string | 否 | 领域索引目录覆盖；不传时走 fallback |

> 说明：当前实现中客户端无需传 `id`，服务端会自动生成唯一 slug（冲突时自动追加后缀）。

**fallback 语义**

- 当 `material_path` / `index_path` 未传或为空时，服务端按配置的默认目录策略自动推导该领域路径并创建目录。
- 已配置 `domain_*_paths[domain_id]` 显式映射时，显式映射优先；未命中时才走默认 fallback 目录策略。

### 2.2 编辑领域（`PATCH /api/v1/domains/{id}`）

- 允许更新 `name`、`description`、`emoji`、`variant` 及可选路径覆盖字段。
- 路径字段省略时保持原值，不会触发重置为默认 fallback。

### 2.3 归档领域（`DELETE /api/v1/domains/{id}`）

- 语义为归档（soft delete），用于 UI 的「归档」操作；不建议物理删除已写入材料与索引。
- 成功后该领域不再出现在默认 `GET /domains` 列表中。
- 为避免误操作，服务端会保证至少保留一个 active domain；当删除最后一个 active domain 时返回 `409`。

### 2.4 领域接口错误码

| HTTP | `error.code` | 场景 |
|------|--------------|------|
| `400` | `INVALID_DOMAIN_PAYLOAD` | 字段非法（空名称、非法 id、路径无效等） |
| `404` | `DOMAIN_NOT_FOUND` | 目标领域不存在 |
| `409` | `DOMAIN_LAST_ACTIVE` | 删除会导致 active domain 数量变为 0 |
| `409` | `DOMAIN_NOT_EMPTY` | 领域已有材料或索引数据，禁止归档/删除 |
| `422` | `DOMAIN_PATH_INVALID` | 路径校验失败或不可写 |
| `500` | `DOMAIN_PERSISTENCE_FAILED` | 持久化失败 |

---

## 3. 对话（核心：替换前端占位回复）

用户操作：选择领域 → 在输入框输入文字、粘贴 URL、粘贴/拖入/回形针选择文件 → 发送。

### 3.1 同步一问一答（最小可用）

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/v1/chat` | 单次问答 + 材料入库管线由后端执行 |

**请求：`multipart/form-data`**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `domain_id` | string | 是 | 如 `early-childhood`、`chinese` |
| `text` | string | 否 | 用户输入正文；可与文件二选一或组合 |
| `files` | file[] | 否 | 零个或多个；支持 `pdf`、`markdown` 等（与产品约定一致） |

**说明**

- 正文中的 **URL** 由后端解析、抓取、再 ingest（前端不单独传 `url` 字段也可；若你希望显式字段，可增加可选 `urls` JSON 数组）。
- `domain_id` → 解析到 **材料 Vault / 索引 Vault** 的逻辑全部在后端（参见 `docs/ui_design.md`）。

**响应示例**

```json
{
  "message": {
    "id": "msg_uuid",
    "role": "assistant",
    "content": "模型侧回复正文（纯文本或 Markdown；对话角色为毕达哥拉斯）",
    "created_at": "2026-04-12T10:00:00+08:00"
  },
  "job_ids": []
}
```

- `job_ids`（可选）：若 ingest / 建索引异步，可返回任务 id，供「任务状态」接口轮询（见下）。

### 3.2 流式输出（SSE）

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/v1/chat/stream` | 与 3.1 相同 `multipart/form-data` 入参；响应 **`Content-Type: text/event-stream`**，UTF-8，**SSE** 行：`data: <JSON>\n\n` |

**事件类型（`data` 内 JSON 的 `type` 字段）**

| `type` | 含义 |
|--------|------|
| `start` | 首包；含 `id`（本条模型消息 id）、`created_at`（ISO8601 Z） |
| `delta` | 正文增量；含 `text`（字符串片段，前端拼接） |
| `done` | 结束；含与 `start` 一致的 `id`、`job_ids`（可为 `[]`） |
| `error` | 失败；含 `message`（人类可读） |

前端应用 `fetch` 读 body 流并按 `\n\n` 解析 `data:` 行；首字未到时可展示「等待/生成中」提示。

### 3.3 单文件摄取（索引 Vault，与 CLI 等价）

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/v1/ingest` | 将材料 Vault 内**已有**文件写入指定领域的 graph/wiki 索引 |

**请求：`application/json`**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `domain_id` | string | 是 | active domain；索引路径优先使用 `domain_index_paths[domain_id]`，缺省走默认 fallback 目录策略 |
| `relative_path` | string | 是 | 相对材料 Vault 根的路径（POSIX） |
| `agent_id` | string | 否 | 覆盖 `default_agent_backend`，作为摄取后端 |

**响应示例**

```json
{
  "success": true,
  "entity_count": 0,
  "relation_count": 0,
  "error_message": null
}
```

**说明**：`POST /chat` 上传附件后，若服务端配置 `chat_auto_ingest: true`，可在对话完成后自动对新材料执行摄取（索引路径优先用 `domain_index_paths` 显式映射，缺省走 fallback 目录；失败时仅记录日志，不阻断回复）。

---

## 4. 会话与历史（可选，用于「有消息后的列表 / 上下文」）

若需要刷新页面后保留对话，可增加：

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/v1/conversations` | 创建空会话，返回 `conversation_id` |
| `GET` | `/api/v1/conversations` | 分页列出会话摘要 |
| `GET` | `/api/v1/conversations/{id}/messages` | 拉取某会话消息列表 |
| `POST` | `/api/v1/conversations/{id}/messages` | 与 3.1 类似，但消息挂到指定会话 |

**最小策略**：首版可不实现，前端仅用内存；第二版再接。

---

## 5. 异步任务（可选）

当 ingest、图谱构建较慢时：

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/jobs/{job_id}` | 返回 `pending \| running \| success \| failed` 与简要日志或进度 |

---

## 6. Agent（侧栏「选择 Agent」）

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/agents` | 返回可选 Agent 列表（名称、id、是否默认、说明） |
| `GET` | `/api/v1/settings/agent`（可选） | 当前用户选中的 `agent_id` |
| `PUT` | `/api/v1/settings/agent` |  body: `{ "agent_id": "claude-code" }` |

**`POST /api/v1/chat` 可增可选字段** `agent_id`：不传则用服务端默认。

---

## 7. 设置（侧栏「设置」）

按需拆分，首版可合并为一个对象：

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/settings` | 语言、主题、默认领域覆盖、Obsidian 路径提示等（**勿**把敏感路径暴露给未授权客户端） |
| `PATCH` | `/api/v1/settings` | 部分更新 |

本地单机场景下，部分项可只写本地配置文件，不暴露 HTTP。

---

## 8. 与 Obsidian / 图谱（非聊天主链，可选）

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/graph/open?domain_id=...`（可选） | 返回自定义 URI 或插件深链，由前端打开「在 Obsidian 中查看**」** |

---

## 9. 前端对接优先级（建议）

1. **P0**：`GET /health`、`POST /chat`（multipart + `domain_id` + `text` + `files`）、（建议）`GET /domains`。
2. **P1**：`GET/PUT /agents` 与 `agent_id` 传入 chat；流式 `chat/stream`。
3. **P2**：会话 CRUD、`GET /jobs/{id}`、图谱深链。

---

## 10. 修订记录

| 日期 | 摘要 |
|------|------|
| 2026-04-12 | 初稿：健康、领域、对话、可选会话/任务/Agent/设置/图谱 |
| 2026-04-12 | 已实现 P0：`GET /health`、`GET /version`、`GET /domains`、`POST /chat`、`GET /agents`、`GET|PUT /settings/agent`、`GET /settings`（见 `src/api/`） |
| 2026-04-12 | 已实现：`POST /chat/stream`（SSE）、`POST /ingest`、配置项 `chat_auto_ingest` |
| 2026-04-13 | 新增 `POST /auth/reset-password`，用于本地开发场景下按用户名重置密码 |
| 2026-04-13 | 更新 ingest 文档契约：`domain_index_paths` 显式映射优先，未命中时走默认 fallback 索引目录 |
| 2026-04-13 | 新增 domains CRUD 轮廓、领域接口错误码与路径 fallback 语义（含 409 冲突约定） |
