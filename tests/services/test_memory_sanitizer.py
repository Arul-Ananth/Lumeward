from backend.common.services.memory.memory_sanitizer import sanitize_memory_context


def test_sanitize_memory_context_removes_tool_traces_and_redacts_secrets() -> None:
    text = """
Thought: do something
Action: Access user documents
Tool Name: Web Search
/docs/intro-react.md
IMPORTANT: Use the following format
Actual content line about React.
OPENAI_API_KEY=sk-thisisasecretkeyvaluethatmustbemasked
```
Action: Web Search
```
"""

    cleaned = sanitize_memory_context(text)

    assert "Access user documents" not in cleaned
    assert "Tool Name" not in cleaned
    assert "/docs/" not in cleaned
    assert "sk-thisisasecret" not in cleaned
    assert "OPENAI_API_KEY=[REDACTED]" in cleaned
    assert "Actual content line" in cleaned
