from pathlib import Path
from tempfile import NamedTemporaryFile
from punkrecords.agent.claude_code import ClaudeCodeAgent
from punkrecords.agent.base import IngestionResult, QueryResult, LintResult


def test_claude_code_agent_exists():
    agent = ClaudeCodeAgent(api_key="test_key")
    assert agent.name == "claude_code"
    assert agent.api_key == "test_key"


def test_claude_code_agent_methods():
    agent = ClaudeCodeAgent(api_key="test_key")

    # Test ingest()
    with NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("# Test Note\nTest content")
        temp_path = Path(f.name)

    try:
        ingest_result = agent.ingest(temp_path)
        assert isinstance(ingest_result, IngestionResult)
        assert ingest_result.entities == []
        assert ingest_result.relations == []
        assert ingest_result.success is True
        assert ingest_result.error_message is None
    finally:
        temp_path.unlink()

    # Test query()
    query_result = agent.query("test question")
    assert isinstance(query_result, QueryResult)
    assert query_result.answer == ""
    assert query_result.success is True
    assert query_result.error_message is None

    # Test lint()
    lint_result = agent.lint()
    assert isinstance(lint_result, LintResult)
    assert lint_result.changes_made == 0
    assert lint_result.success is True
