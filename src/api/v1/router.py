from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from src import __version__ as PKG_VERSION

from ..agents_registry import AGENTS, DEFAULT_AGENT_ID, get_agent_meta
from ..domains_data import DEFAULT_DOMAIN_ID, domain_ids, domains_response, get_domain
from ..schemas import (
    AgentOut,
    AgentsResponse,
    ChatMessageOut,
    ChatResponse,
    DomainsResponse,
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
        await uf.close()

    if not text and not file_names:
        raise HTTPException(status_code=400, detail="text 与 files 不能同时为空")

    # TODO: 接入 Vault、ingest、真实 Agent 调用
    parts = [
        f"已收到你在「{domain_name}」下的请求（领域 id：`{domain_id}`）。",
        f"当前 Agent：`{effective_agent}`。",
    ]
    if text:
        parts.append(f"正文长度：{len(text)} 字符。")
    if file_names:
        parts.append("附件：" + "、".join(file_names) + "。")
    parts.append("真实回答将在接入 LLM 与知识库管线后返回。")
    content = "\n".join(parts)

    now = datetime.now(timezone.utc)
    created = now.isoformat().replace("+00:00", "Z")

    return ChatResponse(
        message=ChatMessageOut(
            id=str(uuid.uuid4()),
            role="assistant",
            content=content,
            created_at=created,
        ),
        job_ids=[],
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
