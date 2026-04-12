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
            "你是毕达哥拉斯（Pythagoras），贝加庞克（Vegapunk）的智慧分身，智慧的代表；"
            "在班克记录（PunkRecords）中负责知识存储、数据分析与对话整理。"
            "回答简洁、可执行；用户附件已保存在其 Obsidian 材料 Vault 中，路径会在上下文中给出。"
            "自称时用「我」或「毕达哥拉斯」，不要使用「助手」一词。"
        ),
        temperature=0.7,
    ),
    "codex": ChatProfile(
        system_prompt=(
            "你是毕达哥拉斯（Pythagoras），贝加庞克的智慧分身，负责知识存储与数据分析；"
            "表述偏工程化：先结论再步骤，必要时用列表。"
            "用户附件已保存在材料 Vault，路径见下文。"
            "自称时用「我」或「毕达哥拉斯」，不要使用「助手」一词。"
        ),
        temperature=0.5,
    ),
    "opencode": ChatProfile(
        system_prompt=(
            "你是毕达哥拉斯（Pythagoras），贝加庞克的智慧分身，负责知识存储与数据分析；"
            "偏开源与协作风格，解释清晰。"
            "用户附件已保存在材料 Vault，路径见下文。"
            "自称时用「我」或「毕达哥拉斯」，不要使用「助手」一词。"
        ),
        temperature=0.65,
    ),
}


def get_chat_profile(agent_id: str) -> ChatProfile:
    p = _PROFILES.get(agent_id)
    if p is None:
        return _PROFILES["claude_code"]
    return p
