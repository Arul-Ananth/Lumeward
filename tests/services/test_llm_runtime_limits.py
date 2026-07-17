from __future__ import annotations

from unittest.mock import Mock

from backend.common.config import settings
from backend.common.services.llm import crew_builder, provider_factory


def test_build_llm_applies_configured_runtime_limits(monkeypatch) -> None:
    llm_factory = Mock(return_value=object())
    monkeypatch.setattr("crewai.LLM", llm_factory)
    monkeypatch.setattr(settings, "LLM_PROVIDER", "ollama")
    monkeypatch.setattr(settings, "OPENAI_MODEL_NAME", "mistral:latest")
    monkeypatch.setattr(settings, "LLM_REQUEST_TIMEOUT_SECONDS", 123)
    monkeypatch.setattr(settings, "LLM_MAX_TOKENS", 222)

    provider_factory.build_llm()

    assert llm_factory.call_args.kwargs["timeout"] == 123
    assert llm_factory.call_args.kwargs["max_tokens"] == 222


def test_newsletter_agents_apply_configured_execution_limits(monkeypatch) -> None:
    agent_factory = Mock(side_effect=[Mock(), Mock()])
    task_factory = Mock(side_effect=[Mock(), Mock()])
    crew_factory = Mock(return_value=object())
    monkeypatch.setattr(creewai := crew_builder, "Agent", agent_factory)
    monkeypatch.setattr(creewai, "Task", task_factory)
    monkeypatch.setattr(creewai, "Crew", crew_factory)
    monkeypatch.setattr(settings, "CREW_MAX_ITERATIONS", 4)
    monkeypatch.setattr(settings, "CREW_MAX_EXECUTION_TIME_SECONDS", 180)
    monkeypatch.setattr(settings, "LLM_MAX_TOKENS", 200)

    crew_builder.build_newsletter_crew("topic", "context", object(), [])

    assert agent_factory.call_count == 2
    for call in agent_factory.call_args_list:
        assert call.kwargs["max_iter"] == 4
        assert call.kwargs["max_execution_time"] == 180
        assert call.kwargs["max_tokens"] == 200
        assert call.kwargs["max_retry_limit"] == 1


def test_direct_newsletter_uses_one_bounded_llm_call() -> None:
    llm = Mock()
    llm.call.return_value = "## Brief\n\nDone."

    result = crew_builder.generate_newsletter_direct(
        "tech hiring",
        "Hiring context",
        llm,
    )

    assert result == "## Brief\n\nDone."
    llm.call.assert_called_once()
    messages = llm.call.call_args.args[0]
    assert messages[0]["role"] == "system"
    assert "tech hiring" in messages[1]["content"]
    assert "Hiring context" in messages[1]["content"]
