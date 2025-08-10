"""
Asynchronous tracing example.
Demonstrates how to trace async operations and parallel executions.
"""

import asyncio
from typing import Any

import sybil_scope as ss


async def async_llm_call(prompt: str) -> str:
    """Simulate async LLM call."""
    await asyncio.sleep(0.1)
    return f"Response to: {prompt}"


async def async_tool_call(tool_name: str, args: dict[str, Any]) -> Any:
    """Simulate async tool call."""
    await asyncio.sleep(0.05)
    return {"status": "success", "result": f"Executed {tool_name}"}


async def example_async_tracing():
    """Demonstrate tracing async operations."""
    tracer = ss.Tracer()

    # Start async agent
    agent_id = tracer.log(
        ss.TraceType.AGENT,
        ss.ActionType.START,
        name="AsyncAgent",
        args={"mode": "parallel"},
    )

    # Run multiple async operations in parallel
    async with tracer.trace(
        ss.TraceType.AGENT,
        ss.ActionType.PROCESS,
        parent_id=agent_id,
        label="Parallel Operations",
    ):
        # Create tasks
        tasks = []

        # LLM calls
        for i in range(3):

            async def llm_task(idx):
                llm_id = tracer.log(
                    ss.TraceType.LLM,
                    ss.ActionType.REQUEST,
                    model="gpt-4",
                    args={"prompt": f"Query {idx}"},
                )
                result = await async_llm_call(f"Query {idx}")
                tracer.log(
                    ss.TraceType.LLM,
                    ss.ActionType.RESPOND,
                    parent_id=llm_id,
                    response=result,
                )
                return result

            tasks.append(llm_task(i))

        # Tool calls
        for tool in ["search", "calculator"]:

            async def tool_task(tool_name):
                tool_id = tracer.log(
                    ss.TraceType.TOOL,
                    ss.ActionType.CALL,
                    name=tool_name,
                    args={"query": "test"},
                )
                result = await async_tool_call(tool_name, {"query": "test"})
                tracer.log(
                    ss.TraceType.TOOL,
                    ss.ActionType.RESPOND,
                    parent_id=tool_id,
                    result=result,
                )
                return result

            tasks.append(tool_task(tool))

        # Wait for all tasks
        results = await asyncio.gather(*[task for task in tasks])

        # Log results
        tracer.log(
            ss.TraceType.AGENT,
            ss.ActionType.PROCESS,
            label="Aggregated Results",
            results=results,
        )

    # End agent
    tracer.log(ss.TraceType.AGENT, ss.ActionType.END, parent_id=agent_id)

    tracer.flush()
    print(f"Async traces saved to: {tracer.backend.filepath}")


if __name__ == "__main__":
    print("=== Async Tracing Example ===")
    with ss.option_context((ss.ConfigKey.TRACING_FILE_PREFIX, "async")):
        asyncio.run(example_async_tracing())
