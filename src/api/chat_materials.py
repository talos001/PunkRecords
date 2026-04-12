from __future__ import annotations

import asyncio
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from fastapi import UploadFile

_MAX_BYTES = 10 * 1024 * 1024


class ChatAttachmentError(ValueError):
    """附件过大或无法保存（应映射为 HTTP 400）。"""


@dataclass(frozen=True)
class SavedMaterial:
    """相对材料 Vault 根的路径（POSIX 字符串）。"""

    relative_posix: str


def _safe_filename(name: str | None) -> str:
    if not name:
        return "unnamed"
    base = Path(name).name
    if not base or base in (".", ".."):
        return "unnamed"
    base = re.sub(r"[\x00-\x1f]", "", base)
    return base[:200] if len(base) > 200 else base


async def save_chat_uploads(
    *,
    materials_root: Path,
    domain_id: str,
    files: List[UploadFile],
) -> List[SavedMaterial]:
    """将上传文件写入 ``{root}/{domain}/incoming/{date}/{uuid}/``。"""
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    batch = uuid.uuid4().hex[:12]
    base = materials_root / domain_id / "incoming" / day / batch
    out: List[SavedMaterial] = []

    for uf in files:
        raw = await uf.read()
        await uf.close()
        if len(raw) > _MAX_BYTES:
            raise ChatAttachmentError(
                f"单个附件超过 {_MAX_BYTES // (1024 * 1024)}MB 限制"
            )
        name = _safe_filename(uf.filename)
        target = base / name

        def _write() -> None:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)

        await asyncio.to_thread(_write)
        rel = target.relative_to(materials_root.resolve())
        out.append(SavedMaterial(relative_posix=rel.as_posix()))

    return out
