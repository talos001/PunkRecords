from pathlib import Path
from typing import List
from .base import BaseAgent, IngestionResult, QueryResult, LintResult
from ..graph.entities import Entity, Relation
from .registry import get_agent_registry


class CodexAgent(BaseAgent):
    """Codex agent backend implementation.

    Uses OpenAI Codex for knowledge processing.
    """

    name = "codex"

    def __init__(self, api_key: str = None):
        self.api_key = api_key

    def ingest(self, material_path: Path) -> IngestionResult:
        # TODO: Actual API call implemented later
        entities: List[Entity] = []
        relations: List[Relation] = []
        return IngestionResult(
            entities=entities,
            relations=relations,
            success=True,
            error_message=None,
        )

    def query(self, question: str) -> QueryResult:
        # TODO: Actual query implemented later
        return QueryResult(
            answer="",
            relevant_entities=[],
            success=True,
            error_message=None,
        )

    def lint(self) -> LintResult:
        # TODO: Actual linting implemented later
        return LintResult(
            changes_made=0,
            success=True,
            message="Linting complete - no changes made",
        )


get_agent_registry().register(CodexAgent)
