from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

Role = Literal["system", "user", "assistant"]


@dataclass(frozen=True)
class Message:
    role: Role
    content: str


@dataclass
class CompletionResult:
    text: str
    finish_reason: Optional[str] = None
