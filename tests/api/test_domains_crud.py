from pathlib import Path
import sqlite3

import pytest
import yaml
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.auth import AuthStore, JWTService
from src.api.domain_store import DomainStore
from src.api.domains_data import configure_domain_store
from src.api.schemas import DomainOut


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
    configure_domain_store(tmp_path / "var" / "domains" / "domains.sqlite3")
    app = create_app()
    with TestClient(app) as client:
        auth_store: AuthStore = app.state.auth_store
        jwt_svc: JWTService = app.state.jwt_service
        user = auth_store.create_user("domains-user", "123456")
        auth_store.bump_token_version(user.id)
        refreshed = auth_store.get_user_by_id(user.id)
        assert refreshed is not None
        auth_store.update_materials_path(
            refreshed.id,
            materials_path=None,
            confirmed=True,
        )
        access_token, _ = jwt_svc.issue_pair(refreshed)
        headers = {"Authorization": f"Bearer {access_token}"}
        yield client, headers


def test_domains_crud_happy_path(domains_client, tmp_path: Path) -> None:
    client, headers = domains_client
    created = client.post(
        "/api/v1/domains",
        headers=headers,
        json={"name": "Physics", "description": "first"},
    )
    assert created.status_code == 201
    created_domain = created.json()["domain"]
    assert created_domain["id"] == "physics"
    assert created_domain["name"] == "Physics"

    patched = client.patch(
        "/api/v1/domains/physics",
        headers=headers,
        json={"description": "updated"},
    )
    assert patched.status_code == 200
    assert patched.json()["domain"]["description"] == "updated"

    deleted = client.delete("/api/v1/domains/physics", headers=headers)
    assert deleted.status_code == 200
    assert deleted.json()["ok"] is True
    assert deleted.json()["domain"]["id"] == "physics"
    assert deleted.json()["domain"]["enabled"] is False
    assert deleted.json()["domain"]["is_archived"] is True


def test_delete_domain_returns_409_when_materials_or_index_not_empty(
    domains_client, tmp_path: Path
) -> None:
    client, headers = domains_client
    created = client.post(
        "/api/v1/domains",
        headers=headers,
        json={"name": "Chemistry", "description": "with data"},
    )
    assert created.status_code == 201

    # 材料目录非空：应禁止删除
    material_file = tmp_path / "materials" / "chemistry" / "incoming" / "a.md"
    material_file.parent.mkdir(parents=True, exist_ok=True)
    material_file.write_text("# note", encoding="utf-8")
    blocked_by_material = client.delete("/api/v1/domains/chemistry", headers=headers)
    assert blocked_by_material.status_code == 409
    assert blocked_by_material.json()["error"]["code"] == "DOMAIN_NOT_EMPTY"

    material_file.unlink()
    # 索引数据非空：应禁止删除
    graph_index = tmp_path / "index" / "chemistry" / ".punkrecords" / "graph_index.json"
    graph_index.parent.mkdir(parents=True, exist_ok=True)
    graph_index.write_text('{"nodes":[{"id":"n1"}]}', encoding="utf-8")
    blocked_by_index = client.delete("/api/v1/domains/chemistry", headers=headers)
    assert blocked_by_index.status_code == 409
    assert blocked_by_index.json()["error"]["code"] == "DOMAIN_NOT_EMPTY"


def test_delete_missing_domain_returns_404_even_if_data_exists(domains_client, tmp_path: Path) -> None:
    client, headers = domains_client
    material_file = tmp_path / "materials" / "ghost-domain" / "incoming" / "a.md"
    material_file.parent.mkdir(parents=True, exist_ok=True)
    material_file.write_text("# note", encoding="utf-8")
    resp = client.delete("/api/v1/domains/ghost-domain", headers=headers)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "DOMAIN_NOT_FOUND"


def test_delete_last_active_domain_returns_409(domains_client: tuple[TestClient, dict[str, str]]) -> None:
    client, headers = domains_client
    listing = client.get("/api/v1/domains")
    assert listing.status_code == 200
    active_ids = [d["id"] for d in listing.json()["domains"]]

    # 先归档除一个外的所有活跃领域，触发最后一个活跃领域保护。
    for domain_id in active_ids[1:]:
        resp = client.delete(f"/api/v1/domains/{domain_id}", headers=headers)
        assert resp.status_code == 200

    blocked = client.delete(f"/api/v1/domains/{active_ids[0]}", headers=headers)
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "DOMAIN_LAST_ACTIVE"
