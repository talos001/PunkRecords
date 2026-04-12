from typing import TYPE_CHECKING
from .base import BaseAgent, IngestionResult, QueryResult, LintResult
from .registry import AgentRegistry

if TYPE_CHECKING:
    from .claude_code import ClaudeCodeAgent
    from .codex import CodexAgent
    from .opencode import OpenCodeAgent

__all__ = [
    "BaseAgent",
    "IngestionResult",
    "QueryResult",
    "LintResult",
    "AgentRegistry",
]
