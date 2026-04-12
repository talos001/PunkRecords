from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from src import __version__ as PKG_VERSION
from src.ingest.service import ingest_material_file

from ..agents_registry import AGENTS, DEFAULT_AGENT_ID, get_agent_meta
from ..chat_materials import ChatAttachmentError
from ..chat_service import run_chat, run_chat_stream
from ..domains_data import DEFAULT_DOMAIN_ID, domain_ids, domains_response, get_domain
from ..schemas import (
    AgentOut,
    AgentsResponse,
    ChatResponse,
    DomainsResponse,
    IngestBody,
    IngestResponse,
    SettingsAgentBody,
    SettingsAgentResponse,
    SettingsResponse,
    VersionResponse,
)
from ..state import get_current_agent_id, set_current_agent_id

router = APIRouter()


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
def get_settings_agent() -> SettingsAgentResponse:
    return SettingsAgentResponse(agent_id=get_current_agent_id())


@router.put("/settings/agent", response_model=SettingsAgentResponse)
def put_settings_agent(body: SettingsAgentBody) -> SettingsAgentResponse:
    if get_agent_meta(body.agent_id) is None:
        raise HTTPException(status_code=400, detail="未知 agent_id")
    set_current_agent_id(body.agent_id)
    return SettingsAgentResponse(agent_id=body.agent_id)


@router.get("/settings", response_model=SettingsResponse)
def get_settings() -> SettingsResponse:
    return SettingsResponse(
        default_domain_id=DEFAULT_DOMAIN_ID,
        theme="light",
        language="zh-CN",
    )


@router.post("/ingest", response_model=IngestResponse)
def post_ingest(request: Request, body: IngestBody) -> IngestResponse:
    """将材料 Vault 内单个文件摄取到指定领域的索引 Vault（与 CLI ``ingest`` 等价）。"""
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
