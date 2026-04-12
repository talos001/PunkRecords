import io

import pytest
from fastapi.testclient import TestClient

from src.api.app import app


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("PUNKRECORDS_MATERIALS_VAULT", str(tmp_path))
    monkeypatch.setenv("PUNKRECORDS_LLM_PROVIDER", "fake")
    with TestClient(app) as c:
        yield c


def test_health(client) -> None:
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_version(client) -> None:
    r = client.get("/api/v1/version")
    assert r.status_code == 200
    data = r.json()
    assert data["service"] == "punkrecords"
    assert "version" in data


def test_domains(client) -> None:
    r = client.get("/api/v1/domains")
    assert r.status_code == 200
    data = r.json()
    assert data["default_domain_id"] == "early-childhood"
    ids = {d["id"] for d in data["domains"]}
    assert "chinese" in ids and "history" in ids


def test_chat_text_only(client) -> None:
    r = client.post(
        "/api/v1/chat",
        data={"domain_id": "early-childhood", "text": "你好"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["message"]["role"] == "assistant"
    assert "[fake-llm]" in body["message"]["content"]
    assert "你好" in body["message"]["content"]


def test_chat_bad_domain(client) -> None:
    r = client.post(
        "/api/v1/chat",
        data={"domain_id": "nope", "text": "x"},
    )
    assert r.status_code == 400
    assert "error" in r.json()


def test_chat_with_file(client) -> None:
    r = client.post(
        "/api/v1/chat",
        data={"domain_id": "math", "text": ""},
        files={"files": ("note.md", io.BytesIO(b"# hi"), "text/markdown")},
    )
    assert r.status_code == 200
    content = r.json()["message"]["content"]
    assert "[fake-llm]" in content
    assert "incoming" in content


def test_agents(client) -> None:
    r = client.get("/api/v1/agents")
    assert r.status_code == 200
    data = r.json()
    assert any(a["id"] == "claude_code" for a in data["agents"])


def test_settings_agent_put(client) -> None:
    r = client.put("/api/v1/settings/agent", json={"agent_id": "codex"})
    assert r.status_code == 200
    assert r.json()["agent_id"] == "codex"
    assert client.get("/api/v1/settings/agent").json()["agent_id"] == "codex"
