from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

from .types import CompletionResult, Message


class LLMProvider(Protocol):
    """大模型适配器：给定 messages 返回补全文本或流式分块。"""

    provider_id: str

    async def complete(
        self,
        *,
        messages: list[Message],
        model: str | None,
        temperature: float | None,
    ) -> CompletionResult:
        ...

    def stream_complete(
        self,
        *,
        messages: list[Message],
        model: str | None,
        temperature: float | None,
    ) -> AsyncIterator[str]:
        """按顺序产出正文片段（UTF-8 字符串）。"""
        ...
