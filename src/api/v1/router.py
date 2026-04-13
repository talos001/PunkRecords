from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from src import __version__ as PKG_VERSION
from src.ingest.service import ingest_material_file

from ..auth import AuthStore, JWTService, verify_password
from ..agents_registry import AGENTS, DEFAULT_AGENT_ID, get_agent_meta
from ..chat_materials import ChatAttachmentError
from ..chat_service import run_chat, run_chat_stream
from ..deps import require_auth, require_ready_user
from ..domains_data import DEFAULT_DOMAIN_ID, domain_ids, domains_response, get_domain
from ..errors import ApiError
from ..schemas import (
    AgentOut,
    AgentsResponse,
    AuthLoginBody,
    AuthRefreshBody,
    AuthResetPasswordBody,
    AuthRegisterBody,
    AuthTokenResponse,
    BootstrapResponse,
    BootstrapUserOut,
    ChatResponse,
    DomainsResponse,
    IngestBody,
    IngestResponse,
    MaterialsPathBody,
    MaterialsPathResponse,
    SettingsAgentBody,
    SettingsAgentResponse,
    SettingsResponse,
    VersionResponse,
)
from ..state import get_current_agent_id, set_current_agent_id

router = APIRouter()


def _normalize_username(raw: str) -> str:
    name = (raw or "").strip()
    if len(name) < 3:
        raise ApiError(400, "INVALID_USERNAME", "用户名至少 3 个字符")
    return name


def _validate_password(raw: str) -> str:
    pwd = raw or ""
    if len(pwd) < 6:
        raise ApiError(400, "INVALID_PASSWORD", "密码至少 6 个字符")
    return pwd


def _effective_materials_path(request: Request, user_materials_path: str | None) -> str:
    cfg = request.app.state.config
    return user_materials_path or str(cfg.materials_vault_path)


def _resolve_custom_path(raw: str) -> str:
    p = Path(raw).expanduser().resolve()
    return str(p)


def _ensure_writable_dir(path_raw: str) -> None:
    p = Path(path_raw)
    p.mkdir(parents=True, exist_ok=True)
    probe = p / ".punkrecords-write-probe"
    probe.write_text("ok", encoding="utf-8")
    probe.unlink(missing_ok=True)


@router.post("/auth/register", response_model=AuthTokenResponse)
def auth_register(request: Request, body: AuthRegisterBody) -> AuthTokenResponse:
    store: AuthStore = request.app.state.auth_store
    jwt: JWTService = request.app.state.jwt_service
    username = _normalize_username(body.username)
    password = _validate_password(body.password)
    user = store.create_user(username=username, password=password)
    access, refresh = jwt.issue_pair(user)
    return AuthTokenResponse(access_token=access, refresh_token=refresh)


@router.post("/auth/login", response_model=AuthTokenResponse)
def auth_login(request: Request, body: AuthLoginBody) -> AuthTokenResponse:
    store: AuthStore = request.app.state.auth_store
    jwt: JWTService = request.app.state.jwt_service
    username = _normalize_username(body.username)
    password = _validate_password(body.password)
    user = store.get_user_by_username(username)
    if user is None or not verify_password(password, user.password_salt, user.password_hash):
        raise ApiError(401, "INVALID_CREDENTIALS", "账号或密码错误")
    access, refresh = jwt.issue_pair(user)
    return AuthTokenResponse(access_token=access, refresh_token=refresh)


@router.post("/auth/refresh", response_model=AuthTokenResponse)
def auth_refresh(request: Request, body: AuthRefreshBody) -> AuthTokenResponse:
    store: AuthStore = request.app.state.auth_store
    jwt: JWTService = request.app.state.jwt_service
    payload = jwt.parse_refresh(body.refresh_token)
    user = store.get_user_by_id(str(payload.get("sub") or ""))
    if user is None or int(payload.get("ver") or -1) != user.token_version:
        raise ApiError(401, "AUTH_INVALID_TOKEN", "登录态无效，请重新登录")
    access, refresh = jwt.issue_pair(user)
    return AuthTokenResponse(access_token=access, refresh_token=refresh)


@router.post("/auth/reset-password")
def auth_reset_password(request: Request, body: AuthResetPasswordBody) -> dict:
    store: AuthStore = request.app.state.auth_store
    username = _normalize_username(body.username)
    new_password = _validate_password(body.new_password)
    store.reset_password(username=username, new_password=new_password)
    return {"ok": True}


@router.post("/auth/logout")
def auth_logout(request: Request) -> dict:
    ctx = require_auth(request)
    store: AuthStore = request.app.state.auth_store
    store.bump_token_version(ctx.user.id)
    return {"ok": True}


@router.get("/me/bootstrap", response_model=BootstrapResponse)
def me_bootstrap(request: Request) -> BootstrapResponse:
    ctx = require_auth(request)
    effective = _effective_materials_path(request, ctx.user.materials_path)
    status = "configured" if ctx.user.materials_path_confirmed else "unconfigured"
    source = "user_override" if ctx.user.materials_path else "global_default"
    return BootstrapResponse(
        user=BootstrapUserOut(id=ctx.user.id, username=ctx.user.username),
        vault_config_status=status,
        effective_materials_path=effective,
        source=source,
    )


@router.put("/me/materials-path", response_model=MaterialsPathResponse)
def put_materials_path(request: Request, body: MaterialsPathBody) -> MaterialsPathResponse:
    ctx = require_auth(request)
    store: AuthStore = request.app.state.auth_store
    cfg = request.app.state.config
    mode = (body.mode or "").strip()
    if mode not in {"custom", "use_default"}:
        raise ApiError(400, "INVALID_MODE", "mode 仅支持 custom 或 use_default")

    if mode == "custom":
        custom_raw = (body.custom_path or "").strip()
        if not custom_raw:
            raise ApiError(400, "INVALID_PATH", "自定义路径不能为空")
        effective = _resolve_custom_path(custom_raw)
    else:
        effective = str(cfg.materials_vault_path)

    if effective != body.confirm_effective_path:
        raise ApiError(400, "CONFIRM_PATH_MISMATCH", "请确认当前生效路径")

    try:
        _ensure_writable_dir(effective)
    except Exception as e:
        raise ApiError(400, "INVALID_PATH", f"路径不可写：{effective}") from e

    stored_path = effective if mode == "custom" else None
    store.update_materials_path(
        ctx.user.id,
        materials_path=stored_path,
        confirmed=True,
    )
    return MaterialsPathResponse(
        effective_materials_path=effective,
        vault_config_status="configured",
    )


@router.get("/health")
def health() -> dict:
    return {"ok": True}


@router.get("/version", response_model=VersionResponse)
def version() -> VersionResponse:
    return VersionResponse(version=PKG_VERSION)


@router.get("/domains", response_model=DomainsResponse)
def get_domains() -> DomainsResponse:
    data = domains_response()
    return DomainsResponse(**data)


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: Request,
    domain_id: str = Form(..., description="知识区域 id"),
    text: Optional[str] = Form(None),
    agent_id: Optional[str] = Form(None),
    files: Optional[List[UploadFile]] = File(None),
) -> ChatResponse:
    require_ready_user(request)
    if domain_id not in domain_ids():
        raise HTTPException(
            status_code=400,
            detail="未知 domain_id",
        )

    dom = get_domain(domain_id)
    assert dom is not None
    domain_name = dom["name"]

    effective_agent = agent_id or get_current_agent_id()
    if get_agent_meta(effective_agent) is None:
        raise HTTPException(status_code=400, detail="未知 agent_id")

    text = (text or "").strip()
    upload_list = files or []
    file_names: List[str] = []
    for uf in upload_list:
        if uf.filename:
            file_names.append(uf.filename)

    if not text and not file_names:
        raise HTTPException(status_code=400, detail="text 与 files 不能同时为空")

    cfg = request.app.state.config
    registry = request.app.state.llm_registry
    try:
        return await run_chat(
            domain_id=domain_id,
            domain_name=domain_name,
            agent_id=effective_agent,
            text=text,
            files=upload_list,
            materials_root=cfg.materials_vault_path,
            registry=registry,
            config=cfg,
        )
    except ChatAttachmentError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


def _sse_event(obj: dict) -> str:
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


@router.post("/chat/stream")
async def chat_stream(
    request: Request,
    domain_id: str = Form(..., description="知识区域 id"),
    text: Optional[str] = Form(None),
    agent_id: Optional[str] = Form(None),
    files: Optional[List[UploadFile]] = File(None),
) -> StreamingResponse:
    require_ready_user(request)
    if domain_id not in domain_ids():
        raise HTTPException(status_code=400, detail="未知 domain_id")

    dom = get_domain(domain_id)
    assert dom is not None
    domain_name = dom["name"]

    effective_agent = agent_id or get_current_agent_id()
    if get_agent_meta(effective_agent) is None:
        raise HTTPException(status_code=400, detail="未知 agent_id")

    text = (text or "").strip()
    upload_list = files or []
    file_names: List[str] = []
    for uf in upload_list:
        if uf.filename:
            file_names.append(uf.filename)

    if not text and not file_names:
        raise HTTPException(status_code=400, detail="text 与 files 不能同时为空")

    cfg = request.app.state.config
    registry = request.app.state.llm_registry

    async def event_gen():
        msg_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        created = now.isoformat().replace("+00:00", "Z")
        yield _sse_event({"type": "start", "id": msg_id, "created_at": created})
        try:
            async for chunk in run_chat_stream(
                domain_id=domain_id,
                domain_name=domain_name,
                agent_id=effective_agent,
                text=text,
                files=upload_list,
                materials_root=cfg.materials_vault_path,
                registry=registry,
                config=cfg,
            ):
                yield _sse_event({"type": "delta", "text": chunk})
            yield _sse_event({"type": "done", "id": msg_id, "job_ids": []})
        except ChatAttachmentError as e:
            yield _sse_event({"type": "error", "message": str(e)})
        except ValueError as e:
            yield _sse_event({"type": "error", "message": str(e)})
        except RuntimeError as e:
            yield _sse_event({"type": "error", "message": str(e)})
        except Exception as e:
            # 防止未捕获异常导致 SSE 中断、前端一直停在「正在生成」
            yield _sse_event(
                {
                    "type": "error",
                    "message": str(e) or "流式对话失败",
                }
            )

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/agents", response_model=AgentsResponse)
def list_agents() -> AgentsResponse:
    agents = [
        AgentOut(
            id=a.id,
            label=a.label,
            description=a.description,
            is_default=a.is_default,
        )
        for a in AGENTS
    ]
    return AgentsResponse(agents=agents, default_agent_id=DEFAULT_AGENT_ID)


@router.get("/settings/agent", response_model=SettingsAgentResponse)
def get_settings_agent(request: Request) -> SettingsAgentResponse:
    require_ready_user(request)
    return SettingsAgentResponse(agent_id=get_current_agent_id())


@router.put("/settings/agent", response_model=SettingsAgentResponse)
def put_settings_agent(request: Request, body: SettingsAgentBody) -> SettingsAgentResponse:
    require_ready_user(request)
    if get_agent_meta(body.agent_id) is None:
        raise HTTPException(status_code=400, detail="未知 agent_id")
    set_current_agent_id(body.agent_id)
    return SettingsAgentResponse(agent_id=body.agent_id)


@router.get("/settings", response_model=SettingsResponse)
def get_settings(request: Request) -> SettingsResponse:
    require_ready_user(request)
    return SettingsResponse(
        default_domain_id=DEFAULT_DOMAIN_ID,
        theme="light",
        language="zh-CN",
    )


@router.post("/ingest", response_model=IngestResponse)
def post_ingest(request: Request, body: IngestBody) -> IngestResponse:
    """将材料 Vault 内单个文件摄取到指定领域的索引 Vault（与 CLI ``ingest`` 等价）。"""
    require_ready_user(request)
    if body.domain_id not in domain_ids():
        raise HTTPException(status_code=400, detail="未知 domain_id")
    cfg = request.app.state.config
    try:
        result = ingest_material_file(
            cfg,
            body.domain_id,
            body.relative_path,
            agent_backend=body.agent_id,
        )
        return IngestResponse(
            success=result.success,
            entity_count=len(result.entities),
            relation_count=len(result.relations),
            error_message=result.error_message,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
