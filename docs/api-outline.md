# PunkRecords 后端接口需求说明（面向当前 Web UI）

本文档描述 **前端联调所需的后端 API 轮廓**：路径与字段为建议名，实现时可按框架（如 FastAPI）调整，但语义应对齐。

**基础约定**

- 建议前缀：`/api/v1`（或 `/v1`）。
- 请求/响应：`Content-Type: application/json`，UTF-8。
- 文件上传：`multipart/form-data`。
- 时间：ISO 8601 字符串，时区建议 **明确为服务器本地或 UTC** 并在文档中写死。
- 错误：统一 JSON 形如 `{ "error": { "code": "...", "message": "人类可读说明" } }`，HTTP 状态码 4xx/5xx。

**认证（按需）**

- 若仅本机单用户：可先省略，或固定 token。
- 若多用户/远程：建议 `Authorization: Bearer <token>`，下列接口在「需登录」小节标注。

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

- `id`：与后端 Vault 路由表一致，**必填**。
- `emoji` / `variant`：可选；若缺省，前端可回退到本地默认展示。
- `default_domain_id`：与产品策略一致（当前产品默认为幼儿发展）。

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
