"""进程内可写设置（单机无 DB 场景）；后续可换持久化。"""

from threading import Lock

from .agents_registry import DEFAULT_AGENT_ID

_lock = Lock()
_current_agent_id: str = DEFAULT_AGENT_ID


def get_current_agent_id() -> str:
    with _lock:
        return _current_agent_id


def set_current_agent_id(agent_id: str) -> None:
    global _current_agent_id
    with _lock:
        _current_agent_id = agent_id
