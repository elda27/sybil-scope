"""
Nested agent tracing example.
Demonstrates how to trace hierarchical agent interactions.
"""

import time

import sybil_scope as ss


def example_nested_agents():
    """Demonstrate nested agent tracing."""
    tracer = ss.Tracer()

    # User asks for news summary
    user_id = tracer.log(
        ss.TraceType.USER,
        ss.ActionType.INPUT,
        message="Summarize AI news from last week",
    )

    # Main agent starts
    with tracer.trace(
        ss.TraceType.AGENT,
        ss.ActionType.START,
        parent_id=user_id,
        args={"task": "Summarize AI news"},
    ):
        # Call search agent
        tracer.log(
            ss.TraceType.AGENT,
            ss.ActionType.PROCESS,
            label="Calling SearchAgent",
            args={"query": "AI news last week"},
        )

        # Search agent starts
        with tracer.trace(
            ss.TraceType.AGENT,
            ss.ActionType.START,
            name="SearchAgent",
            args={"query": "AI news last week"},
        ):
            # Search tool call
            with tracer.trace(
                ss.TraceType.TOOL,
                ss.ActionType.CALL,
                name="search",
                args={"query": "AI news last week"},
            ) as tool_ctx:
                time.sleep(0.1)
                tracer.log(
                    ss.TraceType.TOOL,
                    ss.ActionType.RESPOND,
                    parent_id=tool_ctx.id,
                    name="search",
                    result=[
                        "Article 1: New LLM breakthrough",
                        "Article 2: AI ethics debate",
                    ],
                )

            # Summarize articles
            tracer.log(
                ss.TraceType.AGENT,
                ss.ActionType.PROCESS,
                label="Summarizing articles",
                args={
                    "articles": [
                        "Article 1: New LLM breakthrough",
                        "Article 2: AI ethics debate",
                    ]
                },
            )

            # LLM call for summary
            with tracer.trace(
                ss.TraceType.LLM,
                ss.ActionType.REQUEST,
                model="gpt-4",
                args={"prompt": "Summarize these articles"},
            ) as llm_ctx:
                time.sleep(0.1)
                tracer.log(
                    ss.TraceType.LLM,
                    ss.ActionType.RESPOND,
                    parent_id=llm_ctx.id,
                    model="gpt-4",
                    response="Recent AI news covers LLM breakthroughs and ethics debates",
                )

            # Return summary
            tracer.log(
                ss.TraceType.AGENT,
                ss.ActionType.PROCESS,
                label="Return summary",
                response="Recent AI news covers LLM breakthroughs and ethics debates",
            )

        # Main agent integrates results
        tracer.log(
            ss.TraceType.AGENT,
            ss.ActionType.PROCESS,
            label="Integrate SearchAgent results",
            response="Recent AI news covers LLM breakthroughs and ethics debates",
        )

    tracer.flush()
    print(f"Traces saved to: {tracer.backend.filepath}")


if __name__ == "__main__":
    print("=== Nested Agents Example ===")
    with ss.option_context((ss.ConfigKey.TRACING_FILE_PREFIX, "nested_agents")):
        example_nested_agents()
