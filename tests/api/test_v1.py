import io

import pytest
from fastapi.testclient import TestClient

from src.api.app import app

client = TestClient(app)


def test_health() -> None:
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_version() -> None:
    r = client.get("/api/v1/version")
    assert r.status_code == 200
    data = r.json()
    assert data["service"] == "punkrecords"
    assert "version" in data


def test_domains() -> None:
    r = client.get("/api/v1/domains")
    assert r.status_code == 200
    data = r.json()
    assert data["default_domain_id"] == "early-childhood"
    ids = {d["id"] for d in data["domains"]}
    assert "chinese" in ids and "history" in ids


def test_chat_text_only() -> None:
    r = client.post(
        "/api/v1/chat",
        data={"domain_id": "early-childhood", "text": "你好"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["message"]["role"] == "assistant"
    assert "幼儿发展" in body["message"]["content"]


def test_chat_bad_domain() -> None:
    r = client.post(
        "/api/v1/chat",
        data={"domain_id": "nope", "text": "x"},
    )
    assert r.status_code == 400
    assert "error" in r.json()


def test_chat_with_file() -> None:
    r = client.post(
        "/api/v1/chat",
        data={"domain_id": "math", "text": ""},
        files={"files": ("note.md", io.BytesIO(b"# hi"), "text/markdown")},
    )
    assert r.status_code == 200
    assert "note.md" in r.json()["message"]["content"]


def test_agents() -> None:
    r = client.get("/api/v1/agents")
    assert r.status_code == 200
    data = r.json()
    assert any(a["id"] == "claude_code" for a in data["agents"])


def test_settings_agent_put() -> None:
    r = client.put("/api/v1/settings/agent", json={"agent_id": "codex"})
    assert r.status_code == 200
    assert r.json()["agent_id"] == "codex"
    assert client.get("/api/v1/settings/agent").json()["agent_id"] == "codex"
