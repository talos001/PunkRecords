from __future__ import annotations

import os
from typing import Optional

from src.config import Config

from .base import LLMProvider
from .providers.anthropic_provider import AnthropicLLMProvider
from .providers.fake_provider import FakeLLMProvider


class LLMRegistry:
    """按 ``Config.llm_provider`` 与 profile 上的 ``provider_id`` 构造适配器。"""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._cache: dict[str, LLMProvider] = {}

    def get_provider(self, provider_id: Optional[str]) -> LLMProvider:
        key = (provider_id or self._config.llm_provider or "fake").strip().lower()
        if key in self._cache:
            return self._cache[key]
        p = self._build(key)
        self._cache[key] = p
        return p

    def _build(self, provider_id: str) -> LLMProvider:
        if provider_id == "fake":
            return FakeLLMProvider()
        if provider_id == "anthropic":
            key = (
                self._config.agent_api_key
                or os.environ.get("ANTHROPIC_API_KEY")
                or ""
            ).strip()
            if not key:
                raise ValueError(
                    "未配置 Anthropic API Key（config.agent_api_key 或环境变量 ANTHROPIC_API_KEY）"
                )
            return AnthropicLLMProvider(
                api_key=key,
                timeout_seconds=self._config.llm_timeout_seconds,
            )
        raise ValueError(f"不支持的 llm_provider: {provider_id}")
