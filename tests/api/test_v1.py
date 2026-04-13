import io

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.api.auth import AuthStore, JWTService
from src.api.domains_data import configure_domain_store


@pytest.fixture
def client(monkeypatch, tmp_path):
    # 避免 pytest 在仓库根目录运行时误读项目内 config.yaml，导致 llm_provider 非 fake
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PUNKRECORDS_MATERIALS_VAULT", str(tmp_path))
    monkeypatch.setenv("PUNKRECORDS_LLM_PROVIDER", "fake")
    configure_domain_store(tmp_path / "var" / "domains" / "domains.sqlite3")
    with TestClient(app) as c:
        yield c


@pytest.fixture
def ready_auth_headers(client):
    auth_store: AuthStore = app.state.auth_store
    jwt_svc: JWTService = app.state.jwt_service
    user = auth_store.create_user("v1-user", "123456")
    auth_store.bump_token_version(user.id)
    refreshed = auth_store.get_user_by_id(user.id)
    assert refreshed is not None
    auth_store.update_materials_path(
        refreshed.id,
        materials_path=None,
        confirmed=True,
    )
    access_token, _ = jwt_svc.issue_pair(refreshed)
    return {"Authorization": f"Bearer {access_token}"}


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
    first = data["domains"][0]
    assert {"id", "name", "description", "emoji", "variant", "enabled"}.issubset(
        set(first.keys())
    )


def test_domains_write_requires_ready_user(client) -> None:
    r = client.post("/api/v1/domains", json={"name": "Physics"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "AUTH_REQUIRED"


def test_chat_text_only(client, ready_auth_headers) -> None:
    r = client.post(
        "/api/v1/chat",
        headers=ready_auth_headers,
        data={"domain_id": "early-childhood", "text": "你好"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["message"]["role"] == "assistant"
    assert "毕达哥拉斯" in body["message"]["content"]
    assert "你好" in body["message"]["content"]


def test_chat_bad_domain(client, ready_auth_headers) -> None:
    r = client.post(
        "/api/v1/chat",
        headers=ready_auth_headers,
        data={"domain_id": "nope", "text": "x"},
    )
    assert r.status_code == 400
    assert "error" in r.json()


def test_chat_rejects_archived_domain(client, ready_auth_headers) -> None:
    archive = client.patch(
        "/api/v1/domains/math",
        headers=ready_auth_headers,
        json={"enabled": False},
    )
    assert archive.status_code == 200
    assert archive.json()["domain"]["enabled"] is False
    r = client.post(
        "/api/v1/chat",
        headers=ready_auth_headers,
        data={"domain_id": "math", "text": "x"},
    )
    assert r.status_code == 400
    assert "error" in r.json()


def test_chat_stream_sse(client, ready_auth_headers) -> None:
    with client.stream(
        "POST",
        "/api/v1/chat/stream",
        headers=ready_auth_headers,
        data={"domain_id": "early-childhood", "text": "hi"},
    ) as r:
        assert r.status_code == 200
        assert "text/event-stream" in r.headers.get("content-type", "")
        raw_bytes = b"".join(r.iter_bytes())
    raw = raw_bytes.decode("utf-8")
    assert "data:" in raw
    assert "start" in raw and "delta" in raw and "done" in raw
    # 流式按短块切分，中文可能跨多个 delta，故只断言角色名首字出现在 SSE 正文中
    assert "毕" in raw


def test_chat_with_file(client, ready_auth_headers) -> None:
    r = client.post(
        "/api/v1/chat",
        headers=ready_auth_headers,
        data={"domain_id": "math", "text": ""},
        files={"files": ("note.md", io.BytesIO(b"# hi"), "text/markdown")},
    )
    assert r.status_code == 200
    content = r.json()["message"]["content"]
    assert "毕达哥拉斯" in content
    assert "incoming" in content


def test_agents(client) -> None:
    r = client.get("/api/v1/agents")
    assert r.status_code == 200
    data = r.json()
    assert any(a["id"] == "claude_code" for a in data["agents"])


def test_settings_agent_put(client, ready_auth_headers) -> None:
    r = client.put(
        "/api/v1/settings/agent",
        headers=ready_auth_headers,
        json={"agent_id": "codex"},
    )
    assert r.status_code == 200
    assert r.json()["agent_id"] == "codex"
    assert (
        client.get("/api/v1/settings/agent", headers=ready_auth_headers).json()["agent_id"]
        == "codex"
    )
