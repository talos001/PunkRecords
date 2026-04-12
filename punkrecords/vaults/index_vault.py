import json
from pathlib import Path
from typing import Iterator, Dict, List
from .base import BaseVault


class IndexVault(BaseVault):
    """Domain-specific index vault that stores knowledge indices.

    Each domain has its own index vault. This vault only stores indices:
    - Wiki index: structured wiki page relationships
    - Graph index: knowledge graph entities and relations

    Indices reference raw content from the materials vault.
    """

    def __init__(self, path: Path, domain_name: str):
        super().__init__(path)
        self.domain_name = domain_name
        self._ensure_dirs()

    @property
    def punkrecords_dir(self) -> Path:
        """Get the .punkrecords directory for index storage."""
        return self.path / ".punkrecords"

    @property
    def graph_index_path(self) -> Path:
        """Path to graph index storage."""
        return self.punkrecords_dir / "graph_index.json"

    @property
    def wiki_index_path(self) -> Path:
        """Path to wiki index storage."""
        return self.punkrecords_dir / "wiki_index.json"

    def _ensure_dirs(self) -> None:
        """Ensure required directories exist."""
        self.punkrecords_dir.mkdir(exist_ok=True, parents=True)
        if not self.graph_index_path.exists():
            self.graph_index_path.write_text("{}", encoding="utf-8")
        if not self.wiki_index_path.exists():
            self.wiki_index_path.write_text("{}", encoding="utf-8")

    def iter_markdown_files(self) -> Iterator[Path]:
        """Iterate over markdown files in the vault (unused for index vault)."""
        yield from []

    def create_material_reference(self, raw_relative_path: Path, title: str) -> Dict:
        """Create a material reference entry for the index.

        Args:
            raw_relative_path: Path relative to materials vault root
            title: Note title

        Returns:
            Reference dictionary that can be stored in index
        """
        return {
            "title": title,
            "raw_path": str(raw_relative_path),
        }

    def load_graph_index(self) -> Dict:
        """Load the graph index from disk."""
        if not self.graph_index_path.exists():
            return {}
        return json.loads(self.graph_index_path.read_text(encoding="utf-8"))

    def save_graph_index(self, index_data: Dict) -> None:
        """Save the graph index to disk."""
        self.graph_index_path.write_text(
            json.dumps(index_data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    def load_wiki_index(self) -> Dict:
        """Load the wiki index from disk."""
        if not self.wiki_index_path.exists():
            return {}
        return json.loads(self.wiki_index_path.read_text(encoding="utf-8"))

    def save_wiki_index(self, index_data: Dict) -> None:
        """Save the wiki index to disk."""
        self.wiki_index_path.write_text(
            json.dumps(index_data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
