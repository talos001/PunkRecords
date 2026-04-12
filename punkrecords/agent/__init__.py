from typing import TYPE_CHECKING
from .base import BaseAgent, IngestionResult, QueryResult, LintResult
from .registry import AgentRegistry, get_agent_registry
from .claude_code import ClaudeCodeAgent

if TYPE_CHECKING:
    from .codex import CodexAgent
    from .opencode import OpenCodeAgent

__all__ = [
    "BaseAgent",
    "IngestionResult",
    "QueryResult",
    "LintResult",
    "AgentRegistry",
    "get_agent_registry",
    "ClaudeCodeAgent",
]
