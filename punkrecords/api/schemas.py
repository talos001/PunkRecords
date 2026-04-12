from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class DomainOut(BaseModel):
    id: str
    name: str
    description: str
    emoji: str = ""
    variant: str = "coral"
    enabled: bool = True


class DomainsResponse(BaseModel):
    domains: List[DomainOut]
    default_domain_id: str


class ChatMessageOut(BaseModel):
    id: str
    role: str
    content: str
    created_at: str


class ChatResponse(BaseModel):
    message: ChatMessageOut
    job_ids: List[str] = Field(default_factory=list)


class VersionResponse(BaseModel):
    service: str = "punkrecords"
    version: str
    api_version: str = "v1"


class AgentOut(BaseModel):
    id: str
    label: str
    description: str = ""
    is_default: bool = False


class AgentsResponse(BaseModel):
    agents: List[AgentOut]
    default_agent_id: str


class SettingsAgentBody(BaseModel):
    agent_id: str


class SettingsAgentResponse(BaseModel):
    agent_id: str


class SettingsResponse(BaseModel):
    default_domain_id: Optional[str] = None
    theme: str = "light"
    language: str = "zh-CN"
