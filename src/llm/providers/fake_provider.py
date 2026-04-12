from __future__ import annotations

from collections.abc import AsyncIterator

from ..types import CompletionResult, Message


class FakeLLMProvider:
    """测试与无密钥环境：返回固定前缀 + user 内容摘要。"""

    provider_id = "fake"

    def __init__(self, prefix: str = "[毕达哥拉斯·演示] ") -> None:
        self._prefix = prefix

    async def complete(
        self,
        *,
        messages: list[Message],
        model: str | None,
        temperature: float | None,
    ) -> CompletionResult:
        user_parts = [m.content for m in messages if m.role == "user"]
        tail = "\n".join(user_parts)[-2000:]
        return CompletionResult(text=f"{self._prefix}{tail}")

    async def stream_complete(
        self,
        *,
        messages: list[Message],
        model: str | None,
        temperature: float | None,
    ) -> AsyncIterator[str]:
        result = await self.complete(
            messages=messages, model=model, temperature=temperature
        )
        text = result.text
        step = max(1, min(48, len(text) // 12 or 1))
        for i in range(0, len(text), step):
            yield text[i : i + step]
