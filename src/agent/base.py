from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from ..graph.entities import Entity, Relation


@dataclass
class IngestionResult:
    """Result from ingesting a note."""
    entities: List[Entity]
    relations: List[Relation]
    success: bool
    error_message: Optional[str] = None


@dataclass
class QueryResult:
    """Result from querying the knowledge base."""
    answer: str
    relevant_entities: List[Entity]
    success: bool
    error_message: Optional[str] = None


@dataclass
class LintResult:
    """Result from linting/reorganizing knowledge."""
    changes_made: int
    success: bool
    message: str


class BaseAgent(ABC):
    """Abstract base class for LLM agent backends."""

    # Agent name for registry
    name: str

    @abstractmethod
    def ingest(self, material_path: Path) -> IngestionResult:
        """Ingest a raw note from materials vault.

        Args:
            material_path: Absolute path to raw markdown file

        Returns:
            IngestionResult with extracted entities and relations
        """
        pass

    @abstractmethod
    def query(self, question: str) -> QueryResult:
        """Query the knowledge base with a natural language question.

        Args:
            question: User's question in natural language

        Returns:
            QueryResult with answer and relevant entities
        """
        pass

    @abstractmethod
    def lint(self) -> LintResult:
        """Lint and reorganize the knowledge base.

        Rebuilds relationships, optimizes connections, fixes broken links.

        Returns:
            LintResult with summary of changes
        """
        pass
