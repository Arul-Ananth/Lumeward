from crewai import Agent, Crew, Task

from backend.common.config import settings


def generate_newsletter_direct(
    topic: str,
    context: str,
    llm,
    *,
    time_sensitive: bool = False,
    runtime_date_label: str | None = None,
) -> str:
    """Generate one bounded completion for local models that do not need tools.

    Small Ollama models are good at the writing task but may not reliably emit
    CrewAI's agent-control protocol, which otherwise causes repeated calls.
    """
    date_instruction = ""
    if time_sensitive and runtime_date_label:
        date_instruction = (
            f" The runtime date is {runtime_date_label}; use it for relative dates "
            "and do not invent current facts."
        )
    messages = [
        {
            "role": "system",
            "content": (
                "You write concise Markdown intelligence briefings. "
                "Use only the supplied context, distinguish facts from uncertainty, "
                f"and return only the final briefing.{date_instruction}"
            ),
        },
        {
            "role": "user",
            "content": (
                f"Write a short newsletter briefing about: {topic}\n\n"
                f"Context:\n{context or 'No additional context was supplied.'}"
            ),
        },
    ]
    return str(llm.call(messages))


def build_newsletter_crew(
    topic: str,
    context: str,
    llm,
    tools: list,
    *,
    time_sensitive: bool = False,
    runtime_date_label: str | None = None,
) -> Crew:
    max_iterations = getattr(settings, "CREW_MAX_ITERATIONS", 3)
    max_execution_seconds = getattr(settings, "CREW_MAX_EXECUTION_TIME_SECONDS", 240)
    max_tokens = getattr(settings, "LLM_MAX_TOKENS", 256)
    researcher_backstory = (
        "You find facts matching user interests. "
        "Use the Web Search tool for any external research."
    )
    writer_backstory = "You write concise, engaging summaries."
    guardrail = (
        "Use only Web Search tools when external research is needed. "
        "Memory context is plain text; do not attempt to access local files or other tools."
    )
    research_expected_output = "3 key facts."
    writer_task_description = f"Write a newsletter summary on '{topic}'."

    if time_sensitive and runtime_date_label:
        researcher_backstory = (
            f"{researcher_backstory} The runtime date for this request is {runtime_date_label}. "
            "Treat that as the meaning of 'today' and verify time-sensitive facts against it."
        )
        writer_backstory = (
            f"{writer_backstory} Treat {runtime_date_label} as the runtime date for this request. "
            "Do not invent dates or reuse stale dates from prior knowledge."
        )
        guardrail = (
            f"{guardrail} The runtime date is {runtime_date_label}. "
            "If current information cannot be verified, say so explicitly."
        )
        research_expected_output = (
            f"3 dated facts grounded to the runtime date {runtime_date_label}, "
            "or an explicit statement that current information could not be verified."
        )
        writer_task_description = (
            f"Write a newsletter summary on '{topic}'. "
            f"Use {runtime_date_label} as the runtime date and do not include conflicting absolute dates."
        )

    researcher = Agent(
        role="Researcher",
        goal=f"Find facts about {topic}",
        backstory=researcher_backstory,
        tools=tools,
        llm=llm,
        verbose=True,
        max_iter=max_iterations,
        max_execution_time=max_execution_seconds,
        max_retry_limit=1,
        max_tokens=max_tokens,
    )

    writer = Agent(
        role="Writer",
        goal="Summarize facts",
        backstory=writer_backstory,
        llm=llm,
        verbose=True,
        max_iter=max_iterations,
        max_execution_time=max_execution_seconds,
        max_retry_limit=1,
        max_tokens=max_tokens,
    )

    task1 = Task(
        description=f"Research '{topic}'. {guardrail}\nContext: {context}",
        expected_output=research_expected_output,
        agent=researcher,
    )

    task2 = Task(
        description=writer_task_description,
        expected_output="A short Markdown newsletter.",
        agent=writer,
        context=[task1],
    )

    return Crew(
        agents=[researcher, writer],
        tasks=[task1, task2],
        verbose=True,
    )
