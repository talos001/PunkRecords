from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ChatProfile:
    """侧栏 ``agent_id`` 对应的对话策略（与 ``LLMProvider`` 正交）。"""

    system_prompt: str
    temperature: float = 0.7
    model_override: Optional[str] = None
    provider_id: Optional[str] = None


_PROFILES: dict[str, ChatProfile] = {
    "claude_code": ChatProfile(
        system_prompt=(
            "你是班克记录（PunkRecords）中的对话助手，帮助用户整理与探索个人知识库。"
            "回答简洁、可执行；用户附件已保存在其 Obsidian 材料 Vault 中，路径会在上下文中给出。"
        ),
        temperature=0.7,
    ),
    "codex": ChatProfile(
        system_prompt=(
            "你是班克记录中的助手，偏工程化表述：先结论再步骤，必要时用列表。"
            "用户附件已保存在材料 Vault，路径见下文。"
        ),
        temperature=0.5,
    ),
    "opencode": ChatProfile(
        system_prompt=(
            "你是班克记录中的助手，偏开源与协作风格，解释清晰。"
            "用户附件已保存在材料 Vault，路径见下文。"
        ),
        temperature=0.65,
    ),
}


def get_chat_profile(agent_id: str) -> ChatProfile:
    p = _PROFILES.get(agent_id)
    if p is None:
        return _PROFILES["claude_code"]
    return p
