from pathlib import Path
from punkrecords.agent.registry import AgentRegistry
from punkrecords.agent.base import BaseAgent, IngestionResult, QueryResult, LintResult


class TestAgent(BaseAgent):
    name = "test"
    def ingest(self, material_path: Path) -> IngestionResult:
        return IngestionResult(entities=[], relations=[], success=True)

    def query(self, question: str) -> QueryResult:
        return QueryResult(answer="test", relevant_entities=[], success=True)

    def lint(self) -> LintResult:
        return LintResult(changes_made=0, success=True, message="done")


def test_register_agent():
    registry = AgentRegistry()
    registry.register(TestAgent)
    assert registry.has_agent("test")
    agent_class = registry.get_agent("test")
    assert agent_class is TestAgent
