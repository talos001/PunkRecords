from pathlib import Path
from typing import List
from .base import BaseAgent, IngestionResult, QueryResult, LintResult
from ..graph.entities import Entity, Relation


class ClaudeCodeAgent(BaseAgent):
    """Claude Code agent backend implementation.

    Uses Claude Code for knowledge processing via Anthropic API.
    """

    name = "claude_code"

    def __init__(self, api_key: str = None):
        self.api_key = api_key

    def ingest(self, material_path: Path) -> IngestionResult:
        """Ingest a note using Claude Code.

        Reads the markdown content, prompts Claude to extract entities and relations.
        """
        content = material_path.read_text(encoding="utf-8")

        # TODO: Actual Anthropic API call will be implemented when we add dependencies
        # For now, stub the structure - actual prompt engineering comes later

        entities: List[Entity] = []
        relations: List[Relation] = []

        return IngestionResult(
            entities=entities,
            relations=relations,
            success=True,
            error_message=None,
        )

    def query(self, question: str) -> QueryResult:
        """Query the knowledge base using Claude Code."""
        # TODO: Implement actual query with context from graph
        return QueryResult(
            answer="",
            relevant_entities=[],
            success=True,
            error_message=None,
        )

    def lint(self) -> LintResult:
        """Lint and reorganize the knowledge base."""
        # TODO: Implement knowledge base linting
        return LintResult(
            changes_made=0,
            success=True,
            message="Linting complete - no changes made",
        )


from .registry import get_agent_registry
get_agent_registry().register(ClaudeCodeAgent)
