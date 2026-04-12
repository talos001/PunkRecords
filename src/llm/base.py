from __future__ import annotations

from typing import Protocol

from .types import CompletionResult, Message


class LLMProvider(Protocol):
    """大模型适配器：给定 messages 返回补全文本。"""

    provider_id: str

    async def complete(
        self,
        *,
        messages: list[Message],
        model: str | None,
        temperature: float | None,
    ) -> CompletionResult:
        ...
