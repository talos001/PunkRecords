from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from pathlib import Path

from fastapi import APIRouter, Body, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from src import __version__ as PKG_VERSION
from src.ingest.service import ingest_material_file

from ..auth import AuthStore, JWTService, verify_password
from ..agents_registry import AGENTS, DEFAULT_AGENT_ID, get_agent_meta
from ..chat_materials import ChatAttachmentError
from ..chat_service import run_chat, run_chat_stream
from ..deps import require_auth, require_ready_user
from ..domains_data import (
    DEFAULT_DOMAIN_ID,
    active_domain_count,
    archive_domain,
    create_domain,
    domain_exists,
    domains_response,
    get_domain,
    has_index_data,
    has_materials_data,
    update_domain,
)
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
    DomainCreateBody,
    DomainsResponse,
    IngestBody,
    IngestResponse,
    MaterialsPathBody,
    MaterialsPathResponse,
    SettingsAgentBody,
    SettingsAgentResponse,
    SettingsDomainsPatchBody,
    SettingsDomainsResponse,
    SettingsLlmPatchBody,
    SettingsLlmResponse,
    SettingsPatchBody,
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


def _mask_secret(secret: str) -> str:
    if not secret:
        return ""
    if len(secret) <= 8:
        return "*" * len(secret)
    return f"{secret[:2]}***{secret[-2:]}"


def _effective_domain_material_paths(
    request: Request, user_materials_path: str | None, stored: dict[str, str]
) -> dict[str, str]:
    base = Path(_effective_materials_path(request, user_materials_path))
    out: dict[str, str] = {}
    for dom in domains_response().get("domains", []):
        domain_id = str(dom.get("id") or "").strip()
        if not domain_id:
            continue
        out[domain_id] = stored.get(domain_id) or str((base / domain_id).resolve())
    return out


def _require_active_domain(domain_id: str) -> dict:
    dom = get_domain(domain_id)
    if dom is None:
        raise HTTPException(status_code=400, detail="domain 不存在或已归档")
    return dom


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
    # NOTE: 当前 Web 前端未使用（主要供运维探活与脚本调用）
    return {"ok": True}


@router.get("/version", response_model=VersionResponse)
def version() -> VersionResponse:
    # NOTE: 当前 Web 前端未使用（主要供诊断/脚本查询）
    return VersionResponse(version=PKG_VERSION)


@router.get("/domains", response_model=DomainsResponse)
def get_domains() -> DomainsResponse:
    data = domains_response()
    return DomainsResponse(**data)


@router.post("/domains", status_code=201)
def post_domain(request: Request, body: DomainCreateBody) -> dict:
    require_ready_user(request)
    try:
        domain = create_domain(
            name=body.name,
            description=body.description,
            emoji=body.emoji,
            variant=body.variant,
        )
    except ValueError as e:
        raise ApiError(400, "INVALID_DOMAIN", str(e)) from e
    return {"domain": domain}


@router.patch("/domains/{domain_id}")
def patch_domain(request: Request, domain_id: str, body: dict = Body(...)) -> dict:
    require_ready_user(request)
    if not isinstance(body, dict):
        raise ApiError(400, "INVALID_DOMAIN", "请求体必须是对象")
    try:
        updated = update_domain(domain_id, body)
    except ValueError as e:
        raise ApiError(400, "INVALID_DOMAIN", str(e)) from e
    if updated is None:
        raise ApiError(404, "DOMAIN_NOT_FOUND", "领域不存在")
    return {"domain": updated}


@router.delete("/domains/{domain_id}")
def remove_domain(request: Request, domain_id: str) -> dict:
    require_ready_user(request)
    cfg = request.app.state.config
    if not domain_exists(domain_id):
        raise ApiError(404, "DOMAIN_NOT_FOUND", "领域不存在")
    if has_materials_data(cfg.materials_vault_path, domain_id):
        raise ApiError(409, "DOMAIN_NOT_EMPTY", "该领域已有材料或索引数据，无法删除")
    index_root = cfg.domain_index_paths.get(domain_id)
    if index_root and has_index_data(index_root):
        raise ApiError(409, "DOMAIN_NOT_EMPTY", "该领域已有材料或索引数据，无法删除")
    target = get_domain(domain_id)
    if target is not None and active_domain_count() <= 1:
        raise ApiError(409, "DOMAIN_LAST_ACTIVE", "至少保留一个活跃领域")
    archived = archive_domain(domain_id)
    if archived is None:
        raise ApiError(404, "DOMAIN_NOT_FOUND", "领域不存在")
    return {"ok": True, "domain": archived}


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: Request,
    domain_id: str = Form(..., description="知识区域 id"),
    text: Optional[str] = Form(None),
    agent_id: Optional[str] = Form(None),
    files: Optional[List[UploadFile]] = File(None),
) -> ChatResponse:
    require_ready_user(request)
    dom = _require_active_domain(domain_id)
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
    dom = _require_active_domain(domain_id)
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
    # NOTE: 当前 Web 前端未使用（保留给 Agent 切换扩展）
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
    # NOTE: 当前 Web 前端未使用（保留给 Agent 设定扩展）
    require_ready_user(request)
    return SettingsAgentResponse(agent_id=get_current_agent_id())


@router.put("/settings/agent", response_model=SettingsAgentResponse)
def put_settings_agent(request: Request, body: SettingsAgentBody) -> SettingsAgentResponse:
    # NOTE: 当前 Web 前端未使用（保留给 Agent 设定扩展）
    require_ready_user(request)
    if get_agent_meta(body.agent_id) is None:
        raise HTTPException(status_code=400, detail="未知 agent_id")
    set_current_agent_id(body.agent_id)
    return SettingsAgentResponse(agent_id=body.agent_id)


@router.get("/settings", response_model=SettingsResponse)
def get_settings(request: Request) -> SettingsResponse:
    # DEPRECATED: 已由 /settings/llm 与 /settings/domains 拆分替代；前端不再调用
    ctx = require_ready_user(request)
    return SettingsResponse(
        default_domain_id=DEFAULT_DOMAIN_ID,
        theme="light",
        language="zh-CN",
        llm_provider=ctx.user.llm_provider or "fake",
        llm_model=ctx.user.llm_model or "",
        llm_base_url=ctx.user.llm_base_url or "",
        masked_llm_api_key=_mask_secret(ctx.user.llm_api_key or ""),
        materials_vault_path=_effective_materials_path(request, ctx.user.materials_path),
        domain_material_paths=ctx.user.domain_material_paths or {},
    )


@router.get("/settings/llm", response_model=SettingsLlmResponse)
def get_settings_llm(request: Request) -> SettingsLlmResponse:
    ctx = require_ready_user(request)
    return SettingsLlmResponse(
        llm_provider=ctx.user.llm_provider or "fake",
        llm_model=ctx.user.llm_model or "",
        llm_base_url=ctx.user.llm_base_url or "",
        masked_llm_api_key=_mask_secret(ctx.user.llm_api_key or ""),
    )


@router.get("/settings/domains", response_model=SettingsDomainsResponse)
def get_settings_domains(request: Request) -> SettingsDomainsResponse:
    ctx = require_ready_user(request)
    return SettingsDomainsResponse(
        materials_vault_path=_effective_materials_path(request, ctx.user.materials_path),
        domain_material_paths=_effective_domain_material_paths(
            request, ctx.user.materials_path, ctx.user.domain_material_paths or {}
        ),
    )


@router.patch("/settings/llm", response_model=SettingsLlmResponse)
def patch_settings_llm(request: Request, body: SettingsLlmPatchBody) -> SettingsLlmResponse:
    ctx = require_ready_user(request)
    store: AuthStore = request.app.state.auth_store
    provider = body.llm_provider.strip() if body.llm_provider is not None else None
    model = body.llm_model.strip() if body.llm_model is not None else None
    base_url = body.llm_base_url.strip() if body.llm_base_url is not None else None
    api_key = body.llm_api_key.strip() if body.llm_api_key is not None else None
    updated = store.update_user_settings(
        ctx.user.id,
        llm_provider=provider,
        llm_model=model,
        llm_base_url=base_url,
        llm_api_key=api_key if api_key is not None and api_key != "" else None,
    )
    return SettingsLlmResponse(
        llm_provider=updated.llm_provider or "fake",
        llm_model=updated.llm_model or "",
        llm_base_url=updated.llm_base_url or "",
        masked_llm_api_key=_mask_secret(updated.llm_api_key or ""),
    )


@router.patch("/settings/domains", response_model=SettingsDomainsResponse)
def patch_settings_domains(
    request: Request, body: SettingsDomainsPatchBody
) -> SettingsDomainsResponse:
    ctx = require_ready_user(request)
    store: AuthStore = request.app.state.auth_store
    cfg = request.app.state.config
    materials_path: str | None = None
    update_materials = False
    if body.materials_vault_path is not None:
        update_materials = True
        p = body.materials_vault_path.strip()
        if p:
            resolved = _resolve_custom_path(p)
            try:
                _ensure_writable_dir(resolved)
            except Exception as e:
                raise ApiError(400, "INVALID_PATH", f"路径不可写：{resolved}") from e
            materials_path = resolved
        else:
            materials_path = None
    if body.domain_material_paths is not None:
        raise ApiError(
            400,
            "UNSUPPORTED_FIELD",
            "domain_material_paths 不支持前端直接修改，仅用于回显",
        )
    updated = store.update_user_settings(
        ctx.user.id,
        materials_path=materials_path,
        update_materials_path=update_materials,
        # 全局路径变化后由后端自动重算领域路径，用户侧不再维护覆盖值。
        domain_material_paths={}
        if update_materials
        else (ctx.user.domain_material_paths or {}),
    )
    effective = updated.materials_path or str(cfg.materials_vault_path)
    return SettingsDomainsResponse(
        materials_vault_path=effective,
        domain_material_paths=_effective_domain_material_paths(
            request, updated.materials_path, updated.domain_material_paths or {}
        ),
    )


@router.patch("/settings", response_model=SettingsResponse)
def patch_settings(request: Request, body: SettingsPatchBody) -> SettingsResponse:
    # DEPRECATED: 已由 /settings/llm 与 /settings/domains 拆分替代；前端不再调用
    ctx = require_ready_user(request)
    store: AuthStore = request.app.state.auth_store
    cfg = request.app.state.config

    provider = body.llm_provider.strip() if body.llm_provider is not None else None
    model = body.llm_model.strip() if body.llm_model is not None else None
    base_url = body.llm_base_url.strip() if body.llm_base_url is not None else None
    api_key = body.llm_api_key.strip() if body.llm_api_key is not None else None

    materials_path: str | None = None
    update_materials = False
    if body.materials_vault_path is not None:
        update_materials = True
        p = body.materials_vault_path.strip()
        if p:
            resolved = _resolve_custom_path(p)
            try:
                _ensure_writable_dir(resolved)
            except Exception as e:
                raise ApiError(400, "INVALID_PATH", f"路径不可写：{resolved}") from e
            materials_path = resolved
        else:
            materials_path = None

    domain_paths: dict[str, str] | None = None
    if body.domain_material_paths is not None:
        domain_paths = {}
        for domain_id, raw in body.domain_material_paths.items():
            if not domain_exists(domain_id):
                raise ApiError(400, "INVALID_DOMAIN", f"未知领域：{domain_id}")
            val = (raw or "").strip()
            if not val:
                continue
            resolved = _resolve_custom_path(val)
            try:
                _ensure_writable_dir(resolved)
            except Exception as e:
                raise ApiError(400, "INVALID_PATH", f"路径不可写：{resolved}") from e
            domain_paths[domain_id] = resolved

    updated = store.update_user_settings(
        ctx.user.id,
        llm_provider=provider,
        llm_model=model,
        llm_base_url=base_url,
        llm_api_key=api_key if api_key is not None and api_key != "" else None,
        materials_path=materials_path,
        update_materials_path=update_materials,
        domain_material_paths=domain_paths,
    )
    effective = updated.materials_path or str(cfg.materials_vault_path)
    return SettingsResponse(
        default_domain_id=DEFAULT_DOMAIN_ID,
        theme="light",
        language="zh-CN",
        llm_provider=updated.llm_provider or "fake",
        llm_model=updated.llm_model or "",
        llm_base_url=updated.llm_base_url or "",
        masked_llm_api_key=_mask_secret(updated.llm_api_key or ""),
        materials_vault_path=effective,
        domain_material_paths=updated.domain_material_paths or {},
    )


@router.post("/ingest", response_model=IngestResponse)
def post_ingest(request: Request, body: IngestBody) -> IngestResponse:
    """将材料 Vault 内单个文件摄取到指定领域的索引 Vault（与 CLI ``ingest`` 等价）。"""
    # NOTE: 当前 Web 前端未直接调用（保留给手工/脚本 ingest）
    require_ready_user(request)
    _require_active_domain(body.domain_id)
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
