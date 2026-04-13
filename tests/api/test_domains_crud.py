from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
import sqlite3

import pytest
import yaml
from fastapi.testclient import TestClient

from src.api.app import create_app
import src.api.v1.router as v1_router

def _load_module(module_name: str, relative_path: str):
    root = Path(__file__).resolve().parents[2]
    file_path = root / relative_path
    spec = spec_from_file_location(module_name, file_path)
    assert spec is not None and spec.loader is not None
    mod = module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


_domain_store_mod = _load_module("punkrecords_domain_store", "src/api/domain_store.py")
_schemas_mod = _load_module("punkrecords_schemas", "src/api/schemas.py")
DomainStore = _domain_store_mod.DomainStore
DomainOut = _schemas_mod.DomainOut


def test_slug_generation_and_conflict_suffix_persisted(tmp_path: Path) -> None:
    db_path = tmp_path / "domains.sqlite3"
    store = DomainStore(db_path)

    d1 = store.create_domain(name="Math Basics", description="A")
    d2 = store.create_domain(name="Math Basics", description="B")

    assert d1.id == "math-basics"
    assert d2.id == "math-basics-2"

    reloaded = DomainStore(db_path)
    ids = [d.id for d in reloaded.list_domains(view="active")]
    assert ids == ["math-basics", "math-basics-2"]


def test_archive_keeps_domain_readable(tmp_path: Path) -> None:
    db_path = tmp_path / "domains.sqlite3"
    store = DomainStore(db_path)
    created = store.create_domain(name="Physics", description="C")

    archived = store.archive_domain(created.id)
    assert archived.is_archived is True
    assert archived.enabled is False
    assert archived.archived_at is not None

    active_ids = [d.id for d in store.list_domains(view="active")]
    assert created.id not in active_ids

    all_ids = [d.id for d in store.list_domains(view="archived")]
    assert created.id in all_ids

    fetched = store.get_domain(created.id)
    assert fetched is not None
    assert fetched.is_archived is True


def test_list_domains_view_semantics_active_archived_all(tmp_path: Path) -> None:
    db_path = tmp_path / "domains.sqlite3"
    store = DomainStore(db_path)
    active = store.create_domain(name="Active Domain", description="A")
    archived = store.create_domain(name="Archived Domain", description="B")
    store.archive_domain(archived.id)

    active_ids = [d.id for d in store.list_domains(view="active")]
    archived_ids = [d.id for d in store.list_domains(view="archived")]
    all_ids = [d.id for d in store.list_domains(view="all")]

    assert active.id in active_ids
    assert archived.id not in active_ids
    assert archived.id in archived_ids
    assert active.id not in archived_ids
    assert active.id in all_ids
    assert archived.id in all_ids


def test_archive_should_keep_first_archived_at(tmp_path: Path) -> None:
    db_path = tmp_path / "domains.sqlite3"
    store = DomainStore(db_path)
    created = store.create_domain(name="Repeat Archive", description="R")
    first = store.archive_domain(created.id)
    second = store.archive_domain(created.id)

    assert first.archived_at is not None
    assert second.archived_at == first.archived_at


def test_archive_missing_domain_raises_key_error(tmp_path: Path) -> None:
    store = DomainStore(tmp_path / "domains.sqlite3")
    with pytest.raises(KeyError):
        store.archive_domain("missing-domain")


def test_create_domain_retries_when_insert_unique_conflict(tmp_path: Path) -> None:
    db_path = tmp_path / "domains.sqlite3"
    store = DomainStore(db_path)

    original_insert = store._insert_domain_row
    state = {"called": False}

    def flaky_insert(conn, *, slug, name, description, emoji, variant, now):
        if not state["called"]:
            state["called"] = True
            raise sqlite3.IntegrityError("UNIQUE constraint failed: domains.id")
        return original_insert(
            conn,
            slug=slug,
            name=name,
            description=description,
            emoji=emoji,
            variant=variant,
            now=now,
        )

    store._insert_domain_row = flaky_insert
    created = store.create_domain(name="Retry Domain", description="r")
    assert created.id == "retry-domain-2"


def test_list_domains_invalid_view_raises_value_error(tmp_path: Path) -> None:
    store = DomainStore(tmp_path / "domains.sqlite3")
    with pytest.raises(ValueError, match="unknown list view"):
        store.list_domains(view="invalid")  # type: ignore[arg-type]


def test_create_domain_raises_runtime_error_when_retry_exhausted(tmp_path: Path) -> None:
    db_path = tmp_path / "domains.sqlite3"
    store = DomainStore(db_path)

    def always_conflict(conn, *, slug, name, description, emoji, variant, now):
        raise sqlite3.IntegrityError("UNIQUE constraint failed: domains.id")

    store._insert_domain_row = always_conflict
    with pytest.raises(RuntimeError, match="failed to allocate slug"):
        store.create_domain(name="Always Conflict", description="x")


def test_create_domain_does_not_retry_non_domain_id_integrity_error(tmp_path: Path) -> None:
    db_path = tmp_path / "domains.sqlite3"
    store = DomainStore(db_path)
    attempts = {"count": 0}

    def other_integrity_error(conn, *, slug, name, description, emoji, variant, now):
        attempts["count"] += 1
        raise sqlite3.IntegrityError("UNIQUE constraint failed: domains.name")

    store._insert_domain_row = other_integrity_error
    with pytest.raises(sqlite3.IntegrityError, match="domains.name"):
        store.create_domain(name="No Retry For Other Error", description="x")
    assert attempts["count"] == 1


def test_domain_schema_supports_archive_contract() -> None:
    out = DomainOut(
        id="physics",
        name="Physics",
        description="desc",
        emoji="",
        variant="coral",
        enabled=False,
        is_archived=True,
        archived_at="2026-04-13T08:00:00Z",
    )
    data = out.model_dump()
    assert data["is_archived"] is True
    assert data["archived_at"] == "2026-04-13T08:00:00Z"


@pytest.fixture
def domains_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    materials_root = tmp_path / "materials"
    index_root = tmp_path / "index" / "chemistry"
    materials_root.mkdir(parents=True, exist_ok=True)
    index_root.mkdir(parents=True, exist_ok=True)
    cfg = {
        "materials_vault_path": str(materials_root),
        "domain_index_paths": {"chemistry": str(index_root)},
        "default_agent_backend": "claude_code",
        "llm_provider": "fake",
        "llm_model": "x",
        "llm_timeout_seconds": 60,
    }
    cfg_path = tmp_path / "cfg.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PUNKRECORDS_CONFIG", str(cfg_path))
    monkeypatch.setattr(v1_router, "require_ready_user", lambda request: None)
    app = create_app()
    with TestClient(app) as client:
        yield client


def test_domains_crud_happy_path(domains_client: TestClient, tmp_path: Path) -> None:
    created = domains_client.post(
        "/api/v1/domains",
        json={"name": "Physics", "description": "first"},
    )
    assert created.status_code == 201
    created_domain = created.json()["domain"]
    assert created_domain["id"] == "physics"
    assert created_domain["name"] == "Physics"

    patched = domains_client.patch(
        "/api/v1/domains/physics",
        json={"description": "updated"},
    )
    assert patched.status_code == 200
    assert patched.json()["domain"]["description"] == "updated"

    deleted = domains_client.delete("/api/v1/domains/physics")
    assert deleted.status_code == 200
    assert deleted.json()["ok"] is True


def test_delete_domain_returns_409_when_materials_or_index_not_empty(
    domains_client: TestClient, tmp_path: Path
) -> None:
    created = domains_client.post(
        "/api/v1/domains",
        json={"name": "Chemistry", "description": "with data"},
    )
    assert created.status_code == 201

    # 材料目录非空：应禁止删除
    material_file = tmp_path / "materials" / "chemistry" / "incoming" / "a.md"
    material_file.parent.mkdir(parents=True, exist_ok=True)
    material_file.write_text("# note", encoding="utf-8")
    blocked_by_material = domains_client.delete("/api/v1/domains/chemistry")
    assert blocked_by_material.status_code == 409
    assert blocked_by_material.json()["error"]["code"] == "DOMAIN_NOT_EMPTY"

    material_file.unlink()
    # 索引数据非空：应禁止删除
    graph_index = tmp_path / "index" / "chemistry" / ".punkrecords" / "graph_index.json"
    graph_index.parent.mkdir(parents=True, exist_ok=True)
    graph_index.write_text('{"nodes":[{"id":"n1"}]}', encoding="utf-8")
    blocked_by_index = domains_client.delete("/api/v1/domains/chemistry")
    assert blocked_by_index.status_code == 409
    assert blocked_by_index.json()["error"]["code"] == "DOMAIN_NOT_EMPTY"
