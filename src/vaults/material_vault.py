from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from .base import BaseVault


class MaterialVault(BaseVault):
    """Raw materials vault that stores original note content.

    Users maintain their raw notes here, organized by domain directories.
    Index vaults reference content from this vault.

    **聊天上传目录约定**（Plan B 阶段 1）：``{vault_root}/{domain_id}/incoming/{UTC日期}/{batch_id}/文件名``，
    batch_id 为 12 位 hex，日期为 ``YYYY-MM-DD``（UTC）。
    """

    def iter_markdown_files(self) -> Iterator[Path]:
        """Iterate recursively over all markdown files in the vault."""
        for md_file in self.path.rglob("*.md"):
            if not any(part.startswith(".") for part in md_file.parts):
                yield md_file

    def read_note(self, relative_path: Path) -> str:
        """Read the content of a note given its relative path from vault root."""
        abs_path = self.get_absolute_path(relative_path)
        return abs_path.read_text(encoding="utf-8")

    def get_relative_path(self, absolute_path: Path) -> Path:
        """Get path relative to vault root from absolute path."""
        return absolute_path.relative_to(self.path)

    @staticmethod
    def safe_upload_filename(name: str | None) -> str:
        """上传原始文件名，仅保留 basename，去掉路径与危险字符。"""
        if not name:
            return "unnamed"
        base = Path(name).name
        if not base or base in (".", ".."):
            return "unnamed"
        base = re.sub(r"[\x00-\x1f]", "", base)
        return base[:200] if len(base) > 200 else base

    @staticmethod
    def validate_domain_segment(domain_id: str) -> str:
        """防止 domain_id 携带路径分隔符；非法则抛 ``ValueError``。"""
        if not domain_id or not domain_id.strip():
            raise ValueError("domain_id 不能为空")
        s = domain_id.strip()
        if ".." in s or "/" in s or "\\" in s or s.startswith("."):
            raise ValueError("非法 domain_id")
        return s

    def allocate_chat_incoming_batch_dir(self, domain_id: str) -> Path:
        """分配新的聊天附件批次目录（绝对路径）；目录尚未创建，写入首文件时再 ``mkdir``。"""
        dom = self.validate_domain_segment(domain_id)
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        batch = uuid.uuid4().hex[:12]
        return self.path / dom / "incoming" / day / batch
