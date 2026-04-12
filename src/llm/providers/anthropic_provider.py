from __future__ import annotations

from typing import Optional

from anthropic import APIStatusError, AsyncAnthropic

from ..types import CompletionResult, Message


class AnthropicLLMProvider:
    provider_id = "anthropic"

    def __init__(
        self,
        *,
        api_key: str,
        timeout_seconds: float = 120.0,
    ) -> None:
        self._client = AsyncAnthropic(api_key=api_key, timeout=timeout_seconds)

    async def complete(
        self,
        *,
        messages: list[Message],
        model: str | None,
        temperature: float | None,
    ) -> CompletionResult:
        system, anthropic_messages = _to_anthropic_messages(messages)
        use_model = model or "claude-sonnet-4-20250514"
        kwargs: dict = {
            "model": use_model,
            "max_tokens": 4096,
            "messages": anthropic_messages,
        }
        if system:
            kwargs["system"] = system
        if temperature is not None:
            kwargs["temperature"] = temperature
        try:
            resp = await self._client.messages.create(**kwargs)
        except APIStatusError as e:
            raise RuntimeError("LLM 服务暂时不可用，请稍后重试") from e
        text = _extract_text(resp)
        return CompletionResult(text=text, finish_reason=getattr(resp, "stop_reason", None))


def _extract_text(resp: object) -> str:
    parts: list[str] = []
    for block in getattr(resp, "content", []) or []:
        if getattr(block, "type", None) == "text":
            parts.append(getattr(block, "text", "") or "")
    return "".join(parts).strip() or "（模型未返回文本）"


def _to_anthropic_messages(
    messages: list[Message],
) -> tuple[Optional[str], list[dict]]:
    system_chunks: list[str] = []
    out: list[dict] = []
    for m in messages:
        if m.role == "system":
            system_chunks.append(m.content)
            continue
        if m.role == "user":
            out.append({"role": "user", "content": m.content})
        elif m.role == "assistant":
            out.append({"role": "assistant", "content": m.content})
    system = "\n\n".join(system_chunks) if system_chunks else None
    return system, out
