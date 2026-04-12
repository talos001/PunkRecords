from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from fastapi import UploadFile

from src.config import Config
from src.llm import LLMRegistry
from src.llm.types import Message

from .chat_materials import SavedMaterial, save_chat_uploads
from .chat_profiles import get_chat_profile
from .schemas import ChatMessageOut, ChatResponse


def _build_user_content(
    *,
    domain_id: str,
    domain_name: str,
    text: str,
    saved: List[SavedMaterial],
) -> str:
    lines = [
        f"领域：{domain_name}（id: {domain_id}）",
        "",
        "用户输入：",
        text if text else "（空，仅附件）",
    ]
    if saved:
        lines.extend(["", "附件已保存（相对材料 Vault 根）："])
        lines.extend(f"- {s.relative_posix}" for s in saved)
    return "\n".join(lines)


async def run_chat(
    *,
    domain_id: str,
    domain_name: str,
    agent_id: str,
    text: str,
    files: List[UploadFile],
    materials_root: Path,
    registry: LLMRegistry,
    config: Config,
) -> ChatResponse:
    profile = get_chat_profile(agent_id)
    saved: List[SavedMaterial] = []
    if files:
        saved = await save_chat_uploads(
            materials_root=materials_root,
            domain_id=domain_id,
            files=files,
        )

    user_content = _build_user_content(
        domain_id=domain_id,
        domain_name=domain_name,
        text=text,
        saved=saved,
    )
    messages: List[Message] = [
        Message(role="system", content=profile.system_prompt),
        Message(role="user", content=user_content),
    ]
    model = profile.model_override or config.llm_model
    provider = registry.get_provider(profile.provider_id)
    result = await provider.complete(
        messages=messages,
        model=model,
        temperature=profile.temperature,
    )
    now = datetime.now(timezone.utc)
    created = now.isoformat().replace("+00:00", "Z")
    return ChatResponse(
        message=ChatMessageOut(
            id=str(uuid.uuid4()),
            role="assistant",
            content=result.text,
            created_at=created,
        ),
        job_ids=[],
    )
