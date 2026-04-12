"""POST /api/v1/ingest"""

from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from src.api.app import create_app


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
        yield c


def test_post_ingest_ok(client_ingest) -> None:
    r = client_ingest.post(
        "/api/v1/ingest",
        json={"domain_id": "math", "relative_path": "n.md"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert "entity_count" in data


def test_post_ingest_bad_domain(client_ingest) -> None:
    r = client_ingest.post(
        "/api/v1/ingest",
        json={"domain_id": "unknown-domain-xyz", "relative_path": "n.md"},
    )
    assert r.status_code == 400
    assert "error" in r.json()
