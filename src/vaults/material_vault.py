from pathlib import Path
from typing import Iterator
from .base import BaseVault


class MaterialVault(BaseVault):
    """Raw materials vault that stores original note content.

    Users maintain their raw notes here, organized by domain directories.
    Index vaults reference content from this vault.
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
