from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator, List, Tuple

from fastapi import UploadFile

from src.config import Config
from src.ingest.service import ingest_chat_saved_files
from src.llm import LLMRegistry
from src.llm.types import Message

from .chat_materials import SavedMaterial, save_chat_uploads
from .chat_profiles import ChatProfile, get_chat_profile
from .schemas import ChatMessageOut, ChatResponse

_log = logging.getLogger(__name__)


async def _maybe_ingest_after_chat(
    config: Config,
    domain_id: str,
    saved: List[SavedMaterial],
) -> None:
    if not config.chat_auto_ingest or not saved:
        return

    def _run() -> None:
        ingest_chat_saved_files(
            config,
            domain_id,
            saved,
            agent_backend=config.default_agent_backend,
        )

    try:
        await asyncio.to_thread(_run)
    except Exception as e:
        _log.warning("聊天后自动摄取批次失败: %s", e)


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


async def prepare_chat_messages(
    *,
    domain_id: str,
    domain_name: str,
    agent_id: str,
    text: str,
    files: List[UploadFile],
    materials_root: Path,
) -> Tuple[List[Message], ChatProfile, List[SavedMaterial]]:
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
    return messages, profile, saved


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
    messages, profile, saved = await prepare_chat_messages(
        domain_id=domain_id,
        domain_name=domain_name,
        agent_id=agent_id,
        text=text,
        files=files,
        materials_root=materials_root,
    )
    model = profile.model_override or config.llm_model
    provider = registry.get_provider(profile.provider_id)
    result = await provider.complete(
        messages=messages,
        model=model,
        temperature=profile.temperature,
    )
    await _maybe_ingest_after_chat(config, domain_id, saved)
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


async def run_chat_stream(
    *,
    domain_id: str,
    domain_name: str,
    agent_id: str,
    text: str,
    files: List[UploadFile],
    materials_root: Path,
    registry: LLMRegistry,
    config: Config,
) -> AsyncIterator[str]:
    messages, profile, saved = await prepare_chat_messages(
        domain_id=domain_id,
        domain_name=domain_name,
        agent_id=agent_id,
        text=text,
        files=files,
        materials_root=materials_root,
    )
    model = profile.model_override or config.llm_model
    provider = registry.get_provider(profile.provider_id)
    async for chunk in provider.stream_complete(
        messages=messages,
        model=model,
        temperature=profile.temperature,
    ):
        if chunk:
            yield chunk
    await _maybe_ingest_after_chat(config, domain_id, saved)
