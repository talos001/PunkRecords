from pathlib import Path
from src.agent.codex import CodexAgent
from src.agent.base import IngestionResult, QueryResult, LintResult


def test_codex_agent_exists():
    agent = CodexAgent(api_key="test_key")
    assert agent.name == "codex"
    assert agent.api_key == "test_key"

    # Verify methods return correct types
    ingest_result = agent.ingest(Path("/tmp/test.md"))
    assert isinstance(ingest_result, IngestionResult)
    assert ingest_result.success is True

    query_result = agent.query("test question")
    assert isinstance(query_result, QueryResult)
    assert query_result.success is True

    lint_result = agent.lint()
    assert isinstance(lint_result, LintResult)
    assert lint_result.success is True
