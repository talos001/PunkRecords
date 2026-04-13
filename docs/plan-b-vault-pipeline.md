# Plan B：Vault 与摄取管线递进顺序（1 → 2 → 3）

本文约定 **Plan B**（URL、ingest、索引 Vault 等）在工程上的落地顺序，避免**先堆 HTTP API 再反推磁盘布局**。

依据：`docs/superpowers/specs/backend-chat-llm-adapter-design.md`（P0 已完成）、`docs/api-outline.md`。

---

## 原则

1. **先定「盘上长什么样」**，再让代码与 API 服从布局与配置。
2. **单一入口读写材料根**：业务层通过同一抽象（`MaterialVault` 或薄封装）访问 `materials_vault_path`，避免一半裸 `Path`、一半类方法。
3. **索引与材料分离**：`domain_id` → `IndexVault` 路径优先使用 `domain_index_paths` 显式配置；未命中时按默认 fallback 根目录策略解析，写入前约定 JSON 形态与引用规则。
4. **API 是最后一层**：在 1、2 的契约稳定后，再把 `POST /chat` 扩展为触发 ingest、或增加 CLI/任务接口。

---

## 阶段 1：统一材料层（Material Vault）

**目标**：所有「往材料 Vault 写 / 从材料 Vault 读」的路径策略一致，可测、可文档化。

| 要做 | 说明 |
|------|------|
| 明确目录约定 | 例如保留现有 `{domain}/incoming/{date}/{batch}/` 作为聊天上传子树；是否在材料根下另有 `notes/` 等由文档写死。 |
| 收敛实现 | `chat_materials` 改为基于 `MaterialVault`（或共享模块）完成落盘与相对路径计算，避免与 `MaterialVault` 类脱节。 |
| 配置 | `materials_vault_path` 仍为唯一材料根；启动时保证根存在（与现 `app` lifespan 行为一致）。 |
| 测试 | 落盘、相对路径、忽略规则（如 `.` 目录）与现有一致或显式变更并更新测试。 |

**不做**：不要求此阶段就写 `IndexVault` 或开放新 REST 路由。

**已实施（代码）**：`MaterialVault.allocate_chat_incoming_batch_dir`、`safe_upload_filename`、`validate_domain_segment`；`api/chat_materials.save_chat_uploads` 仅通过 `MaterialVault` 落盘并计算相对路径。

---

## 阶段 2：领域索引 Vault + 摄取写回（Index + Ingest）

**目标**：`config.domain_index_paths[domain_id]` 被真实使用；ingest 产出进入对应 `IndexVault`（graph/wiki JSON），并与 `BaseAgent.ingest` 或 graphify 输出格式对齐。

| 要做 | 说明 |
|------|------|
| 配置必填路径 | 每个启用领域在 YAML 中有索引 Vault 根路径；缺失时行为明确（启动失败或该领域不可用）。 |
| 封装 | 提供 `get_index_vault(domain_id) -> IndexVault`（或等价工厂），集中校验路径存在。 |
| 摄取管线 | CLI `ingest` 或内部函数：`MaterialVault` 读源 → `BaseAgent.ingest` / 图谱构建 → `IndexVault.save_graph_index` / `save_wiki_index`（具体字段在实现时定稿）。 |
| 与 Chat 的关系 | 聊天落盘的新文件**何时**触发 ingest（同步 / 异步）在阶段 2 末或阶段 3 初定稿，但**磁盘引用格式**须在阶段 2 先稳定。 |

**不做**：不要求此阶段就实现 URL 抓取或 `job_ids` 全链路（可留给阶段 3）。

**已实施（代码）**：`vaults/factory.py`（`resolve_index_vault_path`、`open_index_vault`）；`ingest/service.ingest_material_file`（材料路径校验 → `BaseAgent.ingest` → 合并 `graph_index` / `wiki_index`）；CLI `punkrecords ingest -d <domain> <相对路径>`；配置示例见 `config.example.yaml` 的 `domain_index_paths`。

---

## 阶段 3：产品化能力（URL、异步任务、图谱入口）

**目标**：在 1、2 的契约之上增加 `api-outline` 中的 P1/P2 能力。

| 内容 | 说明 |
|------|------|
| URL 抓取 | 正文内 URL → 拉取 → 落盘材料 → 走阶段 2 的 ingest。 |
| 异步 | 慢 ingest / 建图 → `job_ids` + `GET /jobs/{id}`（Plan C 可与部分条目合并实现）。 |
| 图谱 / Obsidian | `GET /graph/open`、插件深链等，依赖索引路径与 URI 方案已定。 |

**已部分实施**：`POST /api/v1/ingest`（与 CLI 等价）；配置 `chat_auto_ingest` 与聊天落盘后自动摄取（需 `domain_index_paths`）。

**尚未实现**（排期见 [`backlog.md`](backlog.md)）：正文 URL 抓取、`job_ids` 与 `GET /jobs/{id}`、`GET /graph/open`、会话 CRUD、`BaseAgent.ingest` 真实实体抽取等。

---

## 反模式（避免）

- 先加 `POST /ingest` 或扩展 `POST /chat` 的字段，再讨论文件写到哪里。
- 在 `domain_index_paths` 未配置时静默写全局临时目录，导致与 Obsidian 实际 Vault 脱节。
- 多处硬编码相对路径，不经过 `MaterialVault` / `IndexVault` 或单一 path 模块。

---

## 修订记录

| 日期 | 摘要 |
|------|------|
| 2026-04-12 | 初稿：Plan B 按 1→2→3 递进，反模式说明 |
| 2026-04-12 | 阶段 1 落地：`MaterialVault` 统一聊天上传路径与文件名；`chat_materials` 已接入 |
| 2026-04-12 | 阶段 2 落地：`domain_index_paths`、摄取管线、`punkrecords ingest`、graph/wiki 索引合并 |
| 2026-04-12 | 阶段 3 部分：`POST /ingest`、`chat_auto_ingest` |
| 2026-04-12 | 待办项迁至 `backlog.md` |
| 2026-04-12 | 依据文档路径改为 `docs/superpowers/specs/backend-chat-llm-adapter-design.md` |
