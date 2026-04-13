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


class AuthLoginBody(BaseModel):
    username: str
    password: str


class AuthRegisterBody(BaseModel):
    username: str
    password: str


class AuthRefreshBody(BaseModel):
    refresh_token: str


class AuthResetPasswordBody(BaseModel):
    username: str
    new_password: str


class AuthTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class BootstrapUserOut(BaseModel):
    id: str
    username: str


class BootstrapResponse(BaseModel):
    user: BootstrapUserOut
    vault_config_status: str
    effective_materials_path: str
    source: str


class MaterialsPathBody(BaseModel):
    mode: str
    custom_path: Optional[str] = None
    confirm_effective_path: str


class MaterialsPathResponse(BaseModel):
    effective_materials_path: str
    vault_config_status: str


class IngestBody(BaseModel):
    domain_id: str
    relative_path: str
    agent_id: Optional[str] = None
    """覆盖 ``default_agent_backend``（如 ``claude_code``）。"""


class IngestResponse(BaseModel):
    success: bool
    entity_count: int = 0
    relation_count: int = 0
    error_message: Optional[str] = None
