# 待实现清单（Backlog）

## 本文档定位（项目约束）

| 属性 | 说明 |
|------|------|
| **性质** | 收录 **已经计划实施** 的能力条目，可与版本/迭代排期挂钩，作为开发落地的依据之一。 |
| **与 [`function_plan.md`](function_plan.md) 的区别** | `function_plan.md` 为 **讨论中、待定** 的方案与议题，**不考虑实施**、不构成排期承诺；**仅当**某条从讨论定稿并决定开发后，才应 **迁入本 backlog**（或直接在 issue/里程碑中跟踪并在此留档）。 |

与 [`api-outline.md`](api-outline.md)、[`plan-b-vault-pipeline.md`](plan-b-vault-pipeline.md) 对齐；**当前已实现**的聊天、Vault 摄取、`POST /ingest`、流式 SSE 等不在此重复。

---

## 正文 URL 抓取与 ingest 串联

- **需求**：用户消息中的 URL 由后端抓取、转 Markdown/文本、落盘到材料 Vault，再进入摄取管线（见 `api-outline` 3.1 说明）。
- **依赖**：HTTP 客户端、速率限制、失败策略；与 Plan B 阶段 3「URL 抓取」一致。

## 异步任务（Plan C）

- `**job_ids` 非空**：慢 ingest / 建图时返回任务 id，由前端轮询。
- `**GET /api/v1/jobs/{job_id}`**：状态 `pending | running | success | failed` 与简要日志。

## 会话与历史（可选）

- `POST/GET /api/v1/conversations`、`GET/POST .../messages`（见 `api-outline` 第 4 节）。

## 图谱 / Obsidian 入口

- `**GET /api/v1/graph/open?domain_id=...**`：返回自定义 URI 或 Obsidian 插件深链（见 `api-outline` 第 8 节）。

## 模型侧能力深化

- `**BaseAgent.ingest` 真实抽取**：当前多为占位空实体；接入 LLM/规则后写入 `graph_index` 才有业务价值。
- **CLI `query` / `lint`**：`main.py` 仍为 TODO。

## 修订记录


| 日期 | 摘要 |
|------|------|
| 2026-04-12 | 初稿：记录尚未实现能力，便于后续排期 |
| 2026-04-12 | 明确：本文件为已计划实施项；与 `function_plan.md`（讨论稿、非实施依据）分工 |


