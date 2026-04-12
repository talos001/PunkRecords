from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Optional

from anthropic import APIConnectionError, APIStatusError, AsyncAnthropic

from ..types import CompletionResult, Message


class AnthropicLLMProvider:
    provider_id = "anthropic"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str | None = None,
        default_model: str = "claude-sonnet-4-20250514",
        timeout_seconds: float = 120.0,
    ) -> None:
        client_kw: dict = {"api_key": api_key, "timeout": timeout_seconds}
        if base_url:
            client_kw["base_url"] = base_url
        self._client = AsyncAnthropic(**client_kw)
        self._default_model = default_model

    async def complete(
        self,
        *,
        messages: list[Message],
        model: str | None,
        temperature: float | None,
    ) -> CompletionResult:
        system, anthropic_messages = _to_anthropic_messages(messages)
        use_model = model or self._default_model
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
        except APIConnectionError as e:
            raise RuntimeError(
                "无法连接 Anthropic API，请检查网络与代理；若配置了 llm_base_url（第三方网关），请确认地址可达"
            ) from e
        text = _extract_text(resp)
        return CompletionResult(text=text, finish_reason=getattr(resp, "stop_reason", None))

    async def stream_complete(
        self,
        *,
        messages: list[Message],
        model: str | None,
        temperature: float | None,
    ) -> AsyncIterator[str]:
        system, anthropic_messages = _to_anthropic_messages(messages)
        use_model = model or self._default_model
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
            async with self._client.messages.stream(**kwargs) as stream:
                async for text in stream.text_stream:
                    if text:
                        yield text
        except APIStatusError as e:
            raise RuntimeError("LLM 服务暂时不可用，请稍后重试") from e
        except APIConnectionError as e:
            raise RuntimeError(
                "无法连接 Anthropic API，请检查网络与代理；若配置了 llm_base_url（第三方网关），请确认地址可达"
            ) from e


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
