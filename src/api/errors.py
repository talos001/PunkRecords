from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ApiError(Exception):
    status_code: int
    code: str
    message: str
    extra: dict[str, Any] | None = None

