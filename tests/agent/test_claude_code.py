from punkrecords.agent.claude_code import ClaudeCodeAgent


def test_claude_code_agent_exists():
    agent = ClaudeCodeAgent(api_key="test_key")
    assert agent.name == "claude_code"
    assert agent.api_key == "test_key"
