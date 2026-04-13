# F-2 Dynamic Domains Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement full-stack dynamic domain management with backend-persisted domains, auto-generated slug IDs, restricted deletion (archive-first), and consistent Vault path resolution.

**Architecture:** Replace static `domains_data` reads with a domain service backed by persisted JSON data. Expose CRUD-style domain APIs and enforce business rules in one place. Update frontend to manage domains via API and keep chat domain selector in sync with active domains only.

**Tech Stack:** FastAPI + Pydantic + pytest (backend), React + TypeScript + Vite (frontend), JSON file persistence under `var/`.

---

## File Structure

- Modify: `src/api/schemas.py` (new request/response models for domain CRUD)
- Create: `src/api/domain_store.py` (persisted domain repository + slug generator)
- Modify: `src/api/domains_data.py` (compatibility wrapper to store-backed reads)
- Modify: `src/api/v1/router.py` (add POST/PATCH/DELETE `/domains`, switch validations to active-domain checks)
- Modify: `src/vaults/factory.py` (path fallback logic for dynamic domains)
- Create: `tests/api/test_domains_crud.py` (domain CRUD business rules)
- Modify: `tests/api/test_v1.py` (existing `/domains` behavior and compatibility)
- Modify: `frontend/src/api/domains.ts` (domain CRUD API client)
- Modify: `frontend/src/domains.ts` (types/helpers for archived and selector filtering)
- Modify: `frontend/src/App.tsx` (domain manager UI + create/edit/archive flows)
- Modify: `frontend/src/App.css` (domain manager styles)
- Modify: `docs/api-outline.md` (new domain API contracts and error codes)
- Modify: `docs/ui_design.md` (domain management interaction and copy)
- Modify: `docs/function_plan.md` (F-2 status update)

---

### Task 1: Backend Domain Store and Schema Contracts

**Files:**
- Create: `src/api/domain_store.py`
- Modify: `src/api/schemas.py`
- Test: `tests/api/test_domains_crud.py`

- [ ] **Step 1: Write failing tests for slug generation and persistence**

```python
# tests/api/test_domains_crud.py
from src.api.domain_store import DomainStore


def test_create_domain_generates_slug_and_suffix(tmp_path):
    store = DomainStore(tmp_path / "domains.json")
    d1 = store.create_domain(name="数学拓展", description="x", emoji="📐")
    d2 = store.create_domain(name="数学拓展", description="y", emoji="📊")

    assert d1.id == "shu-xue-tuo-zhan"
    assert d2.id == "shu-xue-tuo-zhan-2"


def test_archive_domain_keeps_record(tmp_path):
    store = DomainStore(tmp_path / "domains.json")
    d = store.create_domain(name="历史", description="", emoji="🏛️")
    store.archive_domain(d.id)
    loaded = store.get_domain(d.id, include_archived=True)
    assert loaded is not None
    assert loaded.status == "archived"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run pytest tests/api/test_domains_crud.py -k "slug or archive" -v`  
Expected: FAIL with import or attribute errors for `DomainStore`.

- [ ] **Step 3: Implement minimal domain store and schema models**

```python
# src/api/domain_store.py
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Literal

from slugify import slugify

DomainStatus = Literal["active", "archived"]


@dataclass
class DomainRecord:
    id: str
    name: str
    description: str
    emoji: str
    variant: str
    enabled: bool
    status: DomainStatus
    created_at: str
    updated_at: str


class DomainStore:
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def _load_all(self) -> list[DomainRecord]:
        if not self.file_path.exists():
            return []
        payload = json.loads(self.file_path.read_text(encoding="utf-8"))
        return [DomainRecord(**item) for item in payload]

    def _save_all(self, rows: list[DomainRecord]) -> None:
        self.file_path.write_text(
            json.dumps([asdict(r) for r in rows], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def create_domain(self, name: str, description: str, emoji: str) -> DomainRecord:
        now = datetime.now(timezone.utc).isoformat()
        rows = self._load_all()
        base = slugify(name, lowercase=True) or "domain"
        existing = {r.id for r in rows}
        candidate = base
        idx = 2
        while candidate in existing:
            candidate = f"{base}-{idx}"
            idx += 1
        rec = DomainRecord(
            id=candidate,
            name=name.strip(),
            description=description.strip(),
            emoji=emoji or "📁",
            variant="coral",
            enabled=True,
            status="active",
            created_at=now,
            updated_at=now,
        )
        rows.append(rec)
        self._save_all(rows)
        return rec
```
```python
# src/api/schemas.py (add)
class DomainCreateBody(BaseModel):
    name: str
    description: str = ""
    emoji: str = "📁"
    variant: str = "coral"


class DomainUpdateBody(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    emoji: Optional[str] = None
    variant: Optional[str] = None
    status: Optional[str] = None
```

- [ ] **Step 4: Run tests to verify pass**

Run: `poetry run pytest tests/api/test_domains_crud.py -k "slug or archive" -v`  
Expected: PASS for created test cases.

- [ ] **Step 5: Commit**

```bash
git add src/api/domain_store.py src/api/schemas.py tests/api/test_domains_crud.py
git commit -m "feat: 增加动态领域存储与基础模型"
```

---

### Task 2: Domain APIs and Restricted Deletion Rules

**Files:**
- Modify: `src/api/v1/router.py`
- Modify: `src/api/domains_data.py`
- Test: `tests/api/test_domains_crud.py`
- Test: `tests/api/test_v1.py`

- [ ] **Step 1: Write failing API tests for create/edit/archive flow**

```python
# tests/api/test_domains_crud.py
def test_post_domains_creates_and_returns_slug(client):
    r = client.post("/api/v1/domains", json={"name": "英语写作", "description": "写作", "emoji": "✍️"})
    assert r.status_code == 200
    data = r.json()
    assert data["id"].startswith("ying-yu-xie-zuo")
    assert data["status"] == "active"


def test_delete_domain_with_data_returns_not_empty(client):
    created = client.post("/api/v1/domains", json={"name": "历史专题"}).json()
    cfg = client.app.state.config
    domain_dir = cfg.materials_vault_path / created["id"] / "incoming" / "2026-04-13" / "seed"
    domain_dir.mkdir(parents=True, exist_ok=True)
    (domain_dir / "a.md").write_text("# seeded", encoding="utf-8")
    r = client.delete(f"/api/v1/domains/{created['id']}")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "DOMAIN_NOT_EMPTY"
```

- [ ] **Step 2: Run tests to verify fail**

Run: `poetry run pytest tests/api/test_domains_crud.py -k "post_domains or not_empty" -v`  
Expected: FAIL with `405/404` or missing route handlers.

- [ ] **Step 3: Implement router endpoints and rule checks**

```python
# src/api/v1/router.py (add handlers)
@router.post("/domains", response_model=DomainOut)
def post_domain(request: Request, body: DomainCreateBody) -> DomainOut:
    require_ready_user(request)
    rec = request.app.state.domain_store.create_domain(
        name=body.name, description=body.description, emoji=body.emoji
    )
    return DomainOut(**rec)


@router.patch("/domains/{domain_id}", response_model=DomainOut)
def patch_domain(request: Request, domain_id: str, body: DomainUpdateBody) -> DomainOut:
    require_ready_user(request)
    rec = request.app.state.domain_store.update_domain(domain_id, body.model_dump(exclude_none=True))
    return DomainOut(**rec)


@router.delete("/domains/{domain_id}")
def delete_domain(request: Request, domain_id: str) -> dict:
    require_ready_user(request)
    if _domain_has_materials_or_index(request.app.state.config, domain_id):
        raise ApiError(409, "DOMAIN_NOT_EMPTY", "该领域已有材料，不能删除，可归档")
    request.app.state.domain_store.archive_domain(domain_id)
    return {"ok": True}
```
```python
# src/api/domains_data.py (replace static helper internals)
def domains_response() -> dict[str, Any]:
    store = get_domain_store()
    domains = store.list_domains(include_archived=False)
    return {"domains": [d.to_dict() for d in domains], "default_domain_id": _resolve_default(domains)}
```

- [ ] **Step 4: Run API tests**

Run: `poetry run pytest tests/api/test_domains_crud.py tests/api/test_v1.py -k "domains" -v`  
Expected: PASS for CRUD tests and existing `/domains` read tests.

- [ ] **Step 5: Commit**

```bash
git add src/api/v1/router.py src/api/domains_data.py tests/api/test_domains_crud.py tests/api/test_v1.py
git commit -m "feat: 增加领域增删改接口与受限删除规则"
```

---

### Task 3: Dynamic Domain Path Resolution in Vault Flow

**Files:**
- Modify: `src/vaults/factory.py`
- Modify: `src/api/v1/router.py` (ingest/chat domain checks)
- Test: `tests/api/test_ingest_api.py`

- [ ] **Step 1: Write failing test for fallback path behavior**

```python
# tests/api/test_ingest_api.py
def test_ingest_active_dynamic_domain_uses_fallback_index_path(client_ingest):
    r = client_ingest.post("/api/v1/domains", json={"name": "新领域"})
    domain_id = r.json()["id"]
    # no explicit domain_index_paths[domain_id] configured
    ingest = client_ingest.post("/api/v1/ingest", json={"domain_id": domain_id, "relative_path": "n.md"})
    assert ingest.status_code == 200
    assert ingest.json()["success"] is True
```

- [ ] **Step 2: Run test to verify fail**

Run: `poetry run pytest tests/api/test_ingest_api.py -k "fallback_index_path" -v`  
Expected: FAIL with missing `domain_index_paths` config error.

- [ ] **Step 3: Implement dynamic fallback and active-domain checks**

```python
# src/vaults/factory.py
def resolve_index_vault_path(config: Config, domain_id: str) -> Path:
    raw = config.domain_index_paths.get(domain_id)
    if raw:
        return Path(raw).expanduser().resolve()
    fallback_root = Path(config.materials_vault_path).expanduser().resolve() / ".domain_indexes"
    fallback_root.mkdir(parents=True, exist_ok=True)
    return (fallback_root / domain_id).resolve()
```
```python
# src/api/v1/router.py (replace checks)
if not request.app.state.domain_store.is_active_domain(body.domain_id):
    raise ApiError(400, "DOMAIN_NOT_FOUND", "未知或已归档的领域")
```

- [ ] **Step 4: Run related tests**

Run: `poetry run pytest tests/api/test_ingest_api.py tests/api/test_v1.py -k "ingest or chat_bad_domain" -v`  
Expected: PASS with dynamic domain ingest supported and invalid domain still rejected.

- [ ] **Step 5: Commit**

```bash
git add src/vaults/factory.py src/api/v1/router.py tests/api/test_ingest_api.py
git commit -m "feat: 支持动态领域索引路径回退策略"
```

---

### Task 4: Frontend Domain API Client and State Types

**Files:**
- Modify: `frontend/src/api/domains.ts`
- Modify: `frontend/src/domains.ts`
- Test: `frontend` build check

- [ ] **Step 1: Add type-level assertions via compile-time usage (failing build first)**

```ts
// frontend/src/api/domains.ts (temporary usage in same file)
const _x: DomainMutationPayload = { name: "x" };
// ensure compiler knows create/update payload and response include status
```

- [ ] **Step 2: Run build to verify fail before API additions**

Run: `cd frontend && npm run build`  
Expected: FAIL due to missing `DomainMutationPayload` / mutation methods.

- [ ] **Step 3: Implement domain CRUD client and local mapping**

```ts
export type DomainMutationPayload = {
  name?: string;
  description?: string;
  emoji?: string;
  variant?: DomainVariant;
  status?: "active" | "archived";
};

export async function createDomain(baseUrl: string, body: Required<Pick<DomainMutationPayload, "name">> & DomainMutationPayload) {
  const r = await fetch(`${baseUrl}/api/v1/domains`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`domains:create:${r.status}`);
  return (await r.json()) as DomainApiItem;
}
```
```ts
// frontend/src/domains.ts
export type Domain = {
  id: string;
  name: string;
  description: string;
  emoji: string;
  variant: DomainVariant;
  status?: "active" | "archived";
};

export function activeDomains(domains: Domain[]): Domain[] {
  return domains.filter((d) => (d.status ?? "active") === "active");
}
```

- [ ] **Step 4: Run build to verify pass**

Run: `cd frontend && npm run build`  
Expected: PASS (TypeScript compile and Vite build succeed).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/domains.ts frontend/src/domains.ts
git commit -m "feat: 增加前端领域管理API与状态模型"
```

---

### Task 5: Frontend Domain Management UI and Archive Flow

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.css`
- Test: `frontend` build + manual smoke test

- [ ] **Step 1: Add failing UI integration checks (build-time references)**

```tsx
// frontend/src/App.tsx (temporary to force missing symbols)
<button onClick={() => openCreateDomainModal()}>新增领域</button>
```

- [ ] **Step 2: Run build to verify fail**

Run: `cd frontend && npm run build`  
Expected: FAIL because domain manager handlers/state are not implemented.

- [ ] **Step 3: Implement minimal domain manager panel and archive UX**

```tsx
// frontend/src/App.tsx (core additions)
const [isDomainModalOpen, setDomainModalOpen] = useState(false);
const [domainDraft, setDomainDraft] = useState({ name: "", description: "", emoji: "📁" });

async function onCreateDomainSubmit() {
  const created = await createDomain(API_BASE_URL, { ...domainDraft, name: domainDraft.name.trim() });
  setDomainsList((prev) => [...prev, apiDomainToLocal(created)]);
  setDomainId(created.id);
  setDomainModalOpen(false);
}

async function onArchiveDomain(id: string) {
  try {
    await deleteDomain(API_BASE_URL, id);
  } catch (e) {
    if (String(e).includes("409")) {
      await updateDomain(API_BASE_URL, id, { status: "archived" });
    } else {
      throw e;
    }
  }
  await reloadDomains();
}
```
```css
/* frontend/src/App.css */
.domain-manager { display: grid; gap: 12px; padding: 12px; border: 1px solid #e9e9ee; border-radius: 12px; }
.domain-manager__row { display: flex; justify-content: space-between; align-items: center; }
.domain-manager__actions { display: inline-flex; gap: 8px; }
```

- [ ] **Step 4: Verify with build and smoke run**

Run: `cd frontend && npm run build`  
Expected: PASS.

Run: `poetry run pytest tests/api/test_domains_crud.py -v`  
Expected: PASS for backend contract consumed by UI.

Manual smoke:
- 登录后打开设置的领域管理区
- 新增领域成功后出现在选择器
- 归档领域后默认从选择器隐藏

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.tsx frontend/src/App.css
git commit -m "feat: 增加领域管理面板与归档交互"
```

---

### Task 6: Documentation Sync and Final Regression

**Files:**
- Modify: `docs/api-outline.md`
- Modify: `docs/ui_design.md`
- Modify: `docs/function_plan.md`

- [ ] **Step 1: Update API contract doc**

```md
## Domains API
- POST /api/v1/domains
- PATCH /api/v1/domains/{id}
- DELETE /api/v1/domains/{id}
- Error: DOMAIN_NAME_CONFLICT / DOMAIN_NOT_EMPTY / DOMAIN_NOT_FOUND
```

- [ ] **Step 2: Update UI design doc**

```md
新增“领域管理”区块：支持新增、编辑、归档；删除受限时给出“已有材料，改为归档”提示。
```

- [ ] **Step 3: Update function plan status**

```md
| F-2 | 领域动态增删（UI）；Vault 目录与默认路径策略 | 高 | ✅ 已定稿并进入实现（2026-04-13） | 见 docs/superpowers/specs/2026-04-13-f2-dynamic-domains-and-vault-path-design.md |
```

- [ ] **Step 4: Run full regression checks**

Run: `poetry run pytest tests/api/test_v1.py tests/api/test_domains_crud.py tests/api/test_ingest_api.py -v`  
Expected: PASS.

Run: `cd frontend && npm run build`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add docs/api-outline.md docs/ui_design.md docs/function_plan.md
git commit -m "docs: 同步F-2领域动态管理设计与接口说明"
```

---

## Self-Review Checklist

### 1) Spec coverage
- Dynamic create/edit/archive domain flow: covered in Tasks 1, 2, 5.
- Auto slug generation with suffix conflict handling: covered in Task 1.
- Restricted deletion with not-empty guard: covered in Task 2.
- Path priority and runtime fallback behavior: covered in Task 3.
- Frontend management UX and selector consistency: covered in Tasks 4, 5.
- Docs synchronization requirements: covered in Task 6.

### 2) Placeholder scan
- No `TODO/TBD/implement later` markers remain in task steps.
- Each code-changing step includes concrete code snippets.
- Every verification step has explicit command + expected result.

### 3) Type/signature consistency
- Domain status uses `active|archived` consistently across backend and frontend.
- API naming keeps `/api/v1/domains` and `domain_id` compatibility where required.
- Delete flow uses `409 DOMAIN_NOT_EMPTY` consistently for archive guidance.

---

Plan complete and saved to `docs/superpowers/plans/2026-04-13-f2-dynamic-domains-implementation-plan.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
