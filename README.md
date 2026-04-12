<p align="center">
  <img src="docs/punkrecords_logo.png" width="240" alt="PunkRecords Logo" />
</p>
<h3 align="center">PunkRecords · 班克记录</h3>
<p align="center">
  <em>像贝加庞克一样</em>，将你的大脑外化为无限的智慧仓库。<br />
  <br />
  <strong>贝加庞克（Vegapunk）</strong>的智慧分身<strong>毕达哥拉斯（Pythagoras）</strong>担当你的知识存储与数据分析的助手，让零散的笔记与灵感在此汇聚、碰撞、重生，这是属于你的「班克记录」。
</p>

---

## 特性

- 🤖 **多 AI 代理支持** - 兼容 Claude Code、Codex、OpenCode 等多种 AI 编码代理
- 📊 **知识图谱构建** - 内置 graphify 将输入内容自动转化为结构化知识图谱
- 🔗 **Obsidian 原生集成** - 提供 Obsidian 插件直接打开关系图谱可视化
- 💬 **交互式对话** - 通过聊天界面与你的知识库进行交互查询
- 📁 **分层知识组织** - 原材料与索引分离，支持多领域知识独立管理
- 🔍 **智能知识处理** - AI 代理自动完成知识摄取、查询和整理

## 文档

- **[UI 设计规范](docs/ui_design.md)**：客户端界面、交互与文案原则；**后续所有 UI 相关设计均须在该文件中维护与更新**（单一事实来源）。
- **[API 接口需求](docs/api-outline.md)**：前后端联调所需的 REST/文件上传/可选流式与 Agent、设置等接口轮廓。
- **[Chat + LLM 实现计划](docs/backend-chat-llm-implementation-plan.md)**：`POST /chat` 落盘、LLM 适配器与 ChatProfile（P0）的分步落地顺序与测试清单。
- **[Plan B：Vault 管线递进](docs/plan-b-vault-pipeline.md)**：材料层统一 → 索引与 ingest → URL/异步/图谱（1→2→3），避免先堆 API 再反推磁盘布局。

## 架构概览

PunkRecords 采用清晰的三层架构设计：

### 第一层：UI 层
- **交互式聊天界面** - 用户与 AI 代理进行自然语言交互
- **Obsidian 插件** - 直接打开 Obsidian Vault 查看知识关系图谱

### 第二层：LLM 代理层
- **AI 代理核心** - 支持多种 LLM 代理（Claude Code、Codex、OpenCode 等），负责知识摄取、查询和整理
- **graphify** - 开源组件，将内容转化为知识图谱
- **LLM Wiki** - 可选组件，提供额外的维基组织能力

### 第三层：Obsidian Vaults 层
- **本地知识库原材料 Vault** - 存储原始知识材料，按领域分类目录组织
- **领域知识索引 Vaults** - 每个领域独立一个 Vault，仅存储 Wiki 索引和图谱索引数据，索引中引用原材料 Vault 的原始数据

## 核心理念

PunkRecords 相信：
- **你的知识已经存在** - 不需要迁移，基于你现有的 Obsidian 笔记工作流
- **AI 是协作伙伴** - 帮助你整理、连接和发现知识间的关联
- **分层存储** - 原材料与索引分离，兼顾灵活性和性能
- **开放架构** - 支持多种 AI 后端，不绑定特定服务商

## 开始使用

### HTTP API（FastAPI）

可选环境变量（`POST /chat` 与材料落盘）：

- `PUNKRECORDS_CONFIG`：YAML 路径，见仓库内 [`config.example.yaml`](config.example.yaml)（推荐在 YAML 中配置 **BASE URL / API Key / model** 三项：`llm_base_url`、`llm_api_key`、`llm_model`）。
- **未设置 `PUNKRECORDS_CONFIG` 时**：若你在**启动命令的当前工作目录**下放了 `config.yaml`（例如在仓库根目录执行 `poetry run punkrecords serve`），会自动加载该文件；否则走下方环境变量默认。
- `PUNKRECORDS_MATERIALS_VAULT`：未指定配置文件时，材料 Vault 根目录（默认 `./var/materials_vault`，启动时会创建）。
- `PUNKRECORDS_LLM_PROVIDER`：仅在**未通过上述 YAML 加载到配置**时生效；`fake`（默认，占位回复）或 `anthropic`。若你以为改了 `config.yaml` 却仍走真实 API，多半是未加载到该文件（请确认 `PUNKRECORDS_CONFIG` 或从含 `config.yaml` 的目录启动），或 shell 里仍导出着本变量。
- **LLM 三项（与 YAML 等价，便于本机调试）**：`PUNKRECORDS_LLM_BASE_URL`（或 `ANTHROPIC_BASE_URL`）、`PUNKRECORDS_LLM_API_KEY`（或 `ANTHROPIC_API_KEY`）、`PUNKRECORDS_LLM_MODEL`。

```bash
poetry install
poetry run punkrecords serve --host 127.0.0.1 --port 8765
# 或
poetry run punkrecords-serve --port 8765
```

接口说明见 [`docs/api-outline.md`](docs/api-outline.md)。健康检查：`GET http://127.0.0.1:8765/api/v1/health`。

### Web 前端

```bash
cd frontend && npm install && npm run dev
```

联调后端时，在 `frontend/.env.local` 中设置：

```bash
VITE_API_BASE_URL=http://127.0.0.1:8765
```

详见 [`frontend/README.md`](frontend/README.md)。产品/交互规范见 [`docs/ui_design.md`](docs/ui_design.md)。

## 路线图

- [x] HTTP API 骨架（health / domains / chat / agents / settings）
- [x] Chat：`LLMProvider` 适配器 + 材料落盘（`fake` / Anthropic，见 `docs/backend-chat-llm-adapter-design.md`）
- [ ] graphify 知识图谱构建集成
- [ ] Obsidian 插件开发
- [ ] 多 Vault 知识索引管理
- [x] 交互式聊天界面（Web，可联调 API）
- [ ] 支持多种 AI 代理后端（端到端）

