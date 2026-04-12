from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterator, Optional


class BaseVault(ABC):
    """Base class for all Obsidian vaults in PunkRecords."""

    def __init__(self, path: Path):
        self.path = path.resolve()
        if not self.path.exists():
            raise ValueError(f"Vault path does not exist: {self.path}")

    @abstractmethod
    def iter_markdown_files(self) -> Iterator[Path]:
        """Iterate over all markdown files in the vault."""
        pass

    def get_absolute_path(self, relative_path: Path) -> Path:
        """Get absolute path from a path relative to vault root."""
        return (self.path / relative_path).resolve()

    def exists(self) -> bool:
        """Check if the vault exists."""
        return self.path.exists()
