---

## title: "F-1 用户认证与首登路径确认设计"
type: spec
status: draft
owner: "agent"
created: 2026-04-13
updated: 2026-04-13
related_docs:
  - docs/function_plan.md
  - docs/ui_design.md
  - docs/api-outline.md

# F-1 用户认证与首登路径确认设计

## 1. 背景与目标

`docs/function_plan.md` 中 F-1 议题要求引入用户登录，并在首登时引导确认材料库路径。该能力需要与现有单页聊天主壳保持一致，不引入面向用户的实现术语，同时保证未登录和未完成路径确认用户无法使用受保护功能。

本设计聚焦 F-1，覆盖认证、拦截、首登向导、接口契约、错误处理与验收标准，不包含 F-2/F-3/F-4 的完整实施。

## 2. 范围与非范围

### 2.1 范围

- 认证采用 JWT。
- 未登录访问受保护功能时，使用登录模态框拦截，不跳转独立页面。
- 登录后若用户未完成材料库路径确认，展示首登向导。
- 首登向导允许跳过自定义路径，但必须显示并确认“当前生效路径”后才可进入主功能。
- 后端为未登录与未完成确认提供统一状态码兜底，前端据此回退到对应模态。

### 2.2 非范围

- OIDC/SAML 等第三方登录。
- 多租户权限模型与组织管理。
- 领域动态增删（F-2）。
- LLM 参数设置与路径设置页扩展（F-3/F-4），但本设计提供可复用接口方向。

## 3. 方案选择

对比过三种方案：路由守卫优先、前端状态机网关、纯后端错误码驱动。最终采用：

- 主方案：前端统一状态机网关（体验一致、拦截集中）。
- 兜底方案：后端 `401/428` 保证不可绕过。

该组合既覆盖单页应用中的按钮级行为，也确保前端 bug 不会导致权限和前置条件被绕过。

## 4. 架构与状态流

### 4.1 用户状态机

定义三个状态：

- `anonymous`：未登录。
- `authenticated_unconfigured`：已登录但未完成材料库路径确认。
- `authenticated_ready`：已登录且完成路径确认，可使用所有受保护功能。

### 4.2 统一网关函数

前端所有受保护动作都经 `ensureReady(action)`：

- 当状态为 `anonymous`：弹出登录模态并中断动作。
- 当状态为 `authenticated_unconfigured`：弹出路径确认向导并中断动作。
- 当状态为 `authenticated_ready`：执行动作。

受保护动作至少包括：发送消息、附加文件/链接、打开设置、管理领域。

### 4.3 被中断动作恢复

网关在拦截时缓存 `pendingAction`。用户进入 `authenticated_ready` 后自动重放一次：

- 若成功：清理 `pendingAction`。
- 若失败：保留上下文并提示可重试。

消息草稿和附件引用必须在拦截期间保留，避免重复输入和重复上传。

## 5. 交互设计

### 5.1 登录模态（第一层）

- 保持当前页面，不跳页。
- 表单项：账号、密码、提交按钮、错误提示区。
- 成功后立即调用 `GET /api/v1/me/bootstrap` 决定进入 `authenticated_unconfigured` 或 `authenticated_ready`。
- 失败时模态不关闭，提示“账号或密码错误”或“网络异常，请稍后重试”。

### 5.2 路径确认向导（第二层）

三步式向导：

1. 说明“材料将保存到哪里”与后续影响（用户可理解文案）。
2. 选择模式：
  - 使用默认路径（显示默认路径值）。
  - 自定义路径（输入并校验）。
3. 确认页（必经）：
  - 显示“当前生效路径”。
  - 用户点击“确认并继续”后，状态转为 `authenticated_ready`。

满足已确认策略：允许跳过自定义，但不能跳过最终确认。

### 5.3 文案约束

- 面向用户文案使用“知识区域”“材料库位置”“当前保存位置”等表达。
- 不在用户界面暴露 ingest/query/Vault 等实现术语。
- 角色称谓继续使用“毕达哥拉斯（Pythagoras）”，不使用“助手”泛称。

## 6. 接口契约（建议）

### 6.1 认证

- `POST /api/v1/auth/login`
  - 请求：账号、密码。
  - 响应：`access_token`（短时）；`refresh_token`（建议 httpOnly Cookie 或等价安全机制）。
- `POST /api/v1/auth/refresh`
  - 响应：新的 `access_token`。
- `POST /api/v1/auth/logout`
  - 使会话失效（refresh 失效或版本号递增）。

### 6.2 启动信息

- `GET /api/v1/me/bootstrap`
  - 返回：
    - `user`：基础用户信息。
    - `vault_config_status`：`configured | unconfigured`。
    - `effective_materials_path`：当前生效路径。
    - `source`：`user_override | global_default`。

### 6.3 路径确认与设置

- `PUT /api/v1/me/materials-path`
  - 请求：
    - `mode`: `custom | use_default`
    - `custom_path`（当 `mode=custom`）
    - `confirm_effective_path`
  - 响应：最新 `effective_materials_path`、`vault_config_status=configured`。

## 7. 错误语义与恢复

### 7.1 状态码规范

- `401 AUTH_REQUIRED`：未登录。
- `428 MATERIALS_PATH_CONFIRM_REQUIRED`：已登录但未完成路径确认（返回 `effective_materials_path`）。

### 7.2 前端恢复动作

- 收到 `401`：回到登录模态，保留当前触发动作上下文。
- 收到 `428`：回到路径确认向导，保留当前触发动作上下文。
- refresh 失败：清理会话并进入 `anonymous`。

## 8. 安全约束

- `access_token` 短生命周期（例如 15 分钟）。
- `refresh_token` 长生命周期（例如 7 天）并建议使用 httpOnly Cookie 存储。
- 前端不长期明文持久化敏感字段（与文档约束保持一致）。

## 9. 测试与验收标准

### 9.1 状态流

- 未登录点击受保护功能时，始终弹登录模态。
- 登录成功但未确认路径时，始终进入向导。
- 路径确认后自动恢复一次被中断动作。

### 9.2 接口语义

- 所有受保护接口在未登录时统一返回 `401/AUTH_REQUIRED`。
- 所有受保护接口在未完成路径确认时统一返回 `428/MATERIALS_PATH_CONFIRM_REQUIRED`。
- 前端对 401/428 的处理一致，不出现静默失败。

### 9.3 路径策略

- 可选默认路径或自定义路径。
- 无论是否自定义，最终都必须确认当前生效路径。
- 路径不可写或非法时，给出明确错误并允许继续修改。

### 9.4 回归要求

- 不破坏现有领域切换后清空会话行为。
- 不引入用户可见实现术语。
- 模态样式与现有白底简洁 UI 风格一致。

## 10. 风险与后续演进

- 风险：前后端状态定义不一致导致反复弹窗。
  - 对策：统一枚举值和错误码，在 `api-outline.md` 固化契约。
- 风险：路径检查逻辑分散在多个接口。
  - 对策：封装统一前置校验中间件，确保受保护接口行为一致。
- 风险：后续 F-4 与首登向导逻辑重复。
  - 对策：将路径校验与持久化 API 设计为可复用服务，设置页直接复用。

## 11. 与文档同步要求

进入实现前，需同步更新：

- `docs/ui_design.md`：补充登录模态与路径向导交互规范。
- `docs/api-outline.md`：补充认证、bootstrap、路径确认接口与 401/428 语义。
- `docs/integration-handbook.md`：补充 JWT 与联调流程说明。

