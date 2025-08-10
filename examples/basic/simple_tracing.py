"""
Basic tracing example with context manager.
Demonstrates the fundamental concepts of Sibyl Scope tracing.
"""

import time

import sybil_scope as ss


def example_basic_tracing():
    """Demonstrate basic tracing with context manager."""
    tracer = ss.Tracer()

    # Trace a user input
    user_id = tracer.log(
        ss.TraceType.USER, ss.ActionType.INPUT, message="What's the weather in Tokyo?"
    )

    # Trace agent processing
    with tracer.trace(
        ss.TraceType.AGENT,
        ss.ActionType.START,
        parent_id=user_id,
        args={"task": "Answer weather query"},
    ):
        # Trace planning step
        with tracer.trace(
            ss.TraceType.AGENT,
            ss.ActionType.PROCESS,
            label="Planning",
            args={"user_query": "What's the weather in Tokyo?"},
        ):
            # Simulate LLM call for planning
            with tracer.trace(
                ss.TraceType.LLM,
                ss.ActionType.REQUEST,
                model="gpt-4",
                args={"prompt": "Plan how to answer weather query", "temperature": 0.2},
            ) as llm_ctx:
                time.sleep(0.1)  # Simulate API call
                tracer.log(
                    ss.TraceType.LLM,
                    ss.ActionType.RESPOND,
                    parent_id=llm_ctx.id,
                    model="gpt-4",
                    response="Use weather tool to get Tokyo weather",
                )

        # Trace tool selection
        tracer.log(
            ss.TraceType.AGENT,
            ss.ActionType.PROCESS,
            label="Tool Selection",
            response="weather",
        )

        # Trace tool call
        with tracer.trace(
            ss.TraceType.TOOL,
            ss.ActionType.CALL,
            name="weather",
            args={"location": "Tokyo"},
        ) as tool_ctx:
            time.sleep(0.1)  # Simulate API call
            tracer.log(
                ss.TraceType.TOOL,
                ss.ActionType.RESPOND,
                parent_id=tool_ctx.id,
                name="weather",
                result={"temperature": "22°C", "condition": "sunny", "humidity": "60%"},
            )

        # Trace response generation
        with tracer.trace(
            ss.TraceType.AGENT,
            ss.ActionType.PROCESS,
            label="Generate Response",
            args={
                "tool_result": {
                    "temperature": "22°C",
                    "condition": "sunny",
                    "humidity": "60%",
                }
            },
        ):
            # Another LLM call for response
            with tracer.trace(
                ss.TraceType.LLM,
                ss.ActionType.REQUEST,
                model="gpt-4",
                args={"prompt": "Format weather data for user", "max_tokens": 50},
            ) as llm_ctx:
                time.sleep(0.1)
                tracer.log(
                    ss.TraceType.LLM,
                    ss.ActionType.RESPOND,
                    parent_id=llm_ctx.id,
                    model="gpt-4",
                    response="Currently in Tokyo: 22°C, sunny, 60% humidity",
                )

        # Log final answer
        tracer.log(
            ss.TraceType.AGENT,
            ss.ActionType.PROCESS,
            label="Final Answer",
            response="Currently in Tokyo: 22°C, sunny, 60% humidity",
        )

    # Ensure all traces are written
    tracer.flush()
    print(f"Traces saved to: {tracer.backend.filepath}")


if __name__ == "__main__":
    print("=== Basic Tracing Example ===")
    with ss.option_context((ss.ConfigKey.TRACING_FILE_PREFIX, "basic_tracing")):
        example_basic_tracing()
