from __future__ import annotations

from ..types import CompletionResult, Message


class FakeLLMProvider:
    """测试与无密钥环境：返回固定前缀 + user 内容摘要。"""

    provider_id = "fake"

    def __init__(self, prefix: str = "[fake-llm] ") -> None:
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
