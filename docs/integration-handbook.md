# 前后端联调手册（当前已实现能力）

面向：**本地**同时启动 FastAPI 与 Vite 前端，验证认证、聊天、材料落盘、摄取与流式接口。

---

## 1. 前置条件

- Python：`poetry install`（仓库根目录）。
- Node：`cd frontend && npm install`。
- 联调真实 LLM 时：在配置中填写 **`llm_api_key`**（或环境变量），**`llm_provider: anthropic`**（或你使用的 provider）。仅用占位模型时可 **`llm_provider: fake`**。

---

## 2. 配置文件（推荐）

复制 [`config.example.yaml`](../config.example.yaml) 为本地路径（例如 `./config.yaml`），至少确认：

| 项 | 说明 |
|----|------|
| `materials_vault_path` | 材料根目录（会创建子目录 `/{domain}/incoming/...`） |
| `domain_index_paths` | 各 `domain_id` → 索引 Vault 根目录（**联调 ingest / chat_auto_ingest 必填**） |
| `llm_*` | 模型与密钥 |
| `chat_auto_ingest` | 若需「发附件聊天后自动写索引」设为 `true` |

**启动后端时**任选其一，确保进程能加载到该 YAML：

- 设置环境变量：`export PUNKRECORDS_CONFIG=/绝对路径/config.yaml`
- 或在**启动命令的工作目录**下放 `config.yaml`（`load_app_config` 会读当前目录）。

---

## 3. 启动服务

**终端 A — 后端**

```bash
cd /path/to/PunkRecords
export PUNKRECORDS_CONFIG=/path/to/config.yaml   # 若不用 cwd 的 config.yaml
poetry run punkrecords-serve --port 8765
```

**终端 B — 前端**

```bash
cd /path/to/PunkRecords/frontend
echo 'VITE_API_BASE_URL=http://127.0.0.1:8765' > .env.local
npm run dev
```

浏览器打开 Vite 提示的本地地址（通常为 `http://127.0.0.1:5173`）。

---

## 4. 快速自检（curl）

在**未启动前端**时也可验证 API：

```bash
# 健康检查
curl -s http://127.0.0.1:8765/api/v1/health

# 领域列表
curl -s http://127.0.0.1:8765/api/v1/domains | head -c 400
```

**注册并登录（获取 token）**

```bash
TOKENS=$(curl -s -X POST http://127.0.0.1:8765/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"demo-user","password":"demo-pass-123"}')

ACCESS_TOKEN=$(echo "$TOKENS" | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
```

**聊天（multipart，文本）**

```bash
curl -s -X POST http://127.0.0.1:8765/api/v1/chat \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F 'domain_id=math' \
  -F 'text=你好，联调测试'
```

**单文件摄取（需材料根下已存在该相对路径）**

```bash
# 先将测试文件放入 materials_vault_path 下，例如 math/hello.md
curl -s -X POST http://127.0.0.1:8765/api/v1/ingest \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{"domain_id":"math","relative_path":"hello.md"}'
```

**流式（SSE）**：浏览器或前端用 `fetch` 读流；curl 示例：

```bash
curl -N -X POST http://127.0.0.1:8765/api/v1/chat/stream \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F 'domain_id=math' \
  -F 'text=流式测试'
```

**首登路径确认（未确认会收到 428）**

```bash
curl -s -X PUT http://127.0.0.1:8765/api/v1/me/materials-path \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"mode":"use_default","confirm_effective_path":"/your/materials/path"}'
```

---

## 5. 前端侧关注点

- **`VITE_API_BASE_URL`** 必须与浏览器能访问的后端地址一致（本机联调一般为 `http://127.0.0.1:8765`，勿省略端口）。
- CORS：后端已允许 `5173`/`4173`；若你改了 Vite 端口，需在 `src/api/app.py` 的 CORS 中增加对应 origin。
- 聊天带附件：使用 multipart 的 `files` 字段；落盘路径见材料 Vault 下 `domain/incoming/日期/批次/`。

---

## 6. 常见问题

| 现象 | 排查 |
|------|------|
| 仍走 fake / 无真实回复 | 是否加载到含 `llm_provider: anthropic` 的 YAML；或环境变量仍强制 `PUNKRECORDS_LLM_PROVIDER=fake` |
| `POST /ingest` 400「缺少 domain_index_paths」 | 配置中为该 `domain_id` 配置索引路径 |
| 自动摄取无效果 | `chat_auto_ingest: true` 且本次请求**有附件**；查看后端日志是否有 `聊天后自动摄取失败` |
| 前端跨域错误 | 核对 `VITE_API_BASE_URL` 与后端 host/port、CORS 列表 |

---

## 7. 相关文档

- 接口字段：[`api-outline.md`](api-outline.md)
- **已计划实施** 的能力（勿与本次联调混淆）：[`backlog.md`](backlog.md)
- **讨论中、非实施依据** 的议题：[`function_plan.md`](function_plan.md)（与 `backlog.md` 分工见该文件 §1）

## 修订记录

| 日期 | 摘要 |
|------|------|
| 2026-04-12 | 初稿：联调步骤与 curl 自检 |
| 2026-04-12 | 相关文档：区分 `backlog.md`（已计划实施）与 `function_plan.md`（讨论稿） |
| 2026-04-13 | 增加 JWT 登录、受保护接口 Authorization 头与首登路径确认联调示例 |
