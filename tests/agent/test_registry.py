from pathlib import Path
import pytest
from src.agent.registry import AgentRegistry, get_agent_registry
from src.agent.base import BaseAgent, IngestionResult, QueryResult, LintResult


class TestAgent(BaseAgent):
    name = "test"
    def ingest(self, material_path: Path) -> IngestionResult:
        return IngestionResult(entities=[], relations=[], success=True)

    def query(self, question: str) -> QueryResult:
        return QueryResult(answer="test", relevant_entities=[], success=True)

    def lint(self) -> LintResult:
        return LintResult(changes_made=0, success=True, message="done")


class TestAgentWithoutName(BaseAgent):
    def ingest(self, material_path: Path) -> IngestionResult:
        return IngestionResult(entities=[], relations=[], success=True)

    def query(self, question: str) -> QueryResult:
        return QueryResult(answer="test", relevant_entities=[], success=True)

    def lint(self) -> LintResult:
        return LintResult(changes_made=0, success=True, message="done")


class NonAgentClass:
    name = "not_an_agent"


def test_register_agent():
    registry = AgentRegistry()
    registry.register(TestAgent)
    assert registry.has_agent("test")
    agent_class = registry.get_agent("test")
    assert agent_class is TestAgent


def test_register_agent_without_name():
    registry = AgentRegistry()
    with pytest.raises(ValueError):
        registry.register(TestAgentWithoutName)


def test_register_non_agent_class():
    registry = AgentRegistry()
    with pytest.raises(ValueError):
        registry.register(NonAgentClass)


def test_register_duplicate_agent():
    registry = AgentRegistry()
    registry.register(TestAgent)
    with pytest.raises(ValueError):
        registry.register(TestAgent)


def test_get_non_existent_agent():
    registry = AgentRegistry()
    assert registry.get_agent("nonexistent") is None


def test_list_agents():
    registry = AgentRegistry()
    registry.register(TestAgent)
    assert "test" in registry.list_agents()
    assert len(registry.list_agents()) == 1


def test_singleton_registry():
    registry1 = get_agent_registry()
    registry2 = get_agent_registry()
    assert registry1 is registry2
