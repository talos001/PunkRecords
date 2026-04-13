"""POST /api/v1/ingest"""

from pathlib import Path
import uuid

import pytest
import yaml
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.auth import AuthStore, JWTService


@pytest.fixture
def client_ingest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    mat = tmp_path / "mat"
    idx = tmp_path / "idx"
    mat.mkdir()
    idx.mkdir()
    (mat / "n.md").write_text("# Title\n", encoding="utf-8")
    cfg = {
        "materials_vault_path": str(mat),
        "domain_index_paths": {"math": str(idx)},
        "default_agent_backend": "claude_code",
        "llm_provider": "fake",
        "llm_model": "x",
        "llm_timeout_seconds": 60,
    }
    cfg_path = tmp_path / "cfg.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    monkeypatch.setenv("PUNKRECORDS_CONFIG", str(cfg_path))
    app = create_app()
    with TestClient(app) as c:
        auth_store: AuthStore = app.state.auth_store
        jwt_svc: JWTService = app.state.jwt_service
        user = auth_store.create_user(f"ingest-user-{uuid.uuid4().hex[:8]}", "123456")
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
        yield c, tmp_path, headers


def test_post_ingest_ok(client_ingest) -> None:
    client, _, headers = client_ingest
    r = client.post(
        "/api/v1/ingest",
        headers=headers,
        json={"domain_id": "math", "relative_path": "n.md"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert "entity_count" in data


def test_post_ingest_bad_domain(client_ingest) -> None:
    client, _, headers = client_ingest
    r = client.post(
        "/api/v1/ingest",
        headers=headers,
        json={"domain_id": "unknown-domain-xyz", "relative_path": "n.md"},
    )
    assert r.status_code == 400
    assert "error" in r.json()


def test_post_ingest_fallback_to_default_index_root_when_domain_not_configured(
    client_ingest,
) -> None:
    client, tmp_path, headers = client_ingest
    r = client.post(
        "/api/v1/ingest",
        headers=headers,
        json={"domain_id": "early-childhood", "relative_path": "n.md"},
    )
    assert r.status_code == 200
    fallback_graph = (
        tmp_path / "index_vaults" / "early-childhood" / ".punkrecords" / "graph_index.json"
    )
    assert fallback_graph.exists()
