from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import List

from fastapi import UploadFile

from src.vaults.material_vault import MaterialVault

_MAX_BYTES = 10 * 1024 * 1024


class ChatAttachmentError(ValueError):
    """附件过大或无法保存（应映射为 HTTP 400）。"""


@dataclass(frozen=True)
class SavedMaterial:
    """相对材料 Vault 根的路径（POSIX 字符串）。"""

    relative_posix: str


async def save_chat_uploads(
    *,
    materials_root: Path,
    domain_id: str,
    files: List[UploadFile],
) -> List[SavedMaterial]:
    """将上传文件写入材料 Vault：``MaterialVault`` 约定的 ``incoming`` 批次目录。"""
    vault = MaterialVault(materials_root.resolve())
    batch_dir = vault.allocate_chat_incoming_batch_dir(domain_id)
    out: List[SavedMaterial] = []

    for uf in files:
        raw = await uf.read()
        await uf.close()
        if len(raw) > _MAX_BYTES:
            raise ChatAttachmentError(
                f"单个附件超过 {_MAX_BYTES // (1024 * 1024)}MB 限制"
            )
        name = MaterialVault.safe_upload_filename(uf.filename)
        target = batch_dir / name

        def _write() -> None:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)

        await asyncio.to_thread(_write)
        rel = vault.get_relative_path(target)
        out.append(SavedMaterial(relative_posix=rel.as_posix()))

    return out
