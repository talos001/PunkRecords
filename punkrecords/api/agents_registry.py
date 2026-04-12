"""为 HTTP API 暴露的 Agent 元数据（与 `agent/*.py` 中 `name` 对齐）。"""

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class AgentMeta:
    id: str
    label: str
    description: str = ""
    is_default: bool = False


# 与 ClaudeCodeAgent.name 等一致
AGENTS: List[AgentMeta] = [
    AgentMeta(
        id="claude_code",
        label="Claude Code",
        description="Anthropic Claude Code 工作流",
        is_default=True,
    ),
    AgentMeta(
        id="codex",
        label="Codex",
        description="OpenAI Codex 类代理",
    ),
    AgentMeta(
        id="opencode",
        label="OpenCode",
        description="OpenCode 代理",
    ),
]

DEFAULT_AGENT_ID = "claude_code"


def get_agent_meta(agent_id: str) -> AgentMeta | None:
    for a in AGENTS:
        if a.id == agent_id:
            return a
    return None
