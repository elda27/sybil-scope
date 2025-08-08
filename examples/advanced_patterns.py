"""
Advanced usage patterns for Sibyl Scope.
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from sybil_scope import (
    ActionType,
    FileBackend,
    InMemoryBackend,
    Tracer,
    TraceType,
    set_global_tracer,
    trace_function,
)


# Example 1: Custom backend
class FilteredFileBackend(FileBackend):
    """Custom backend that filters certain event types."""

    def __init__(self, filepath=None, excluded_types=None):
        super().__init__(filepath)
        self.excluded_types = excluded_types or []

    def save(self, event):
        """Save event only if not excluded."""
        if event.type not in self.excluded_types:
            super().save(event)


def example_custom_backend():
    """Demonstrate using a custom backend."""
    # Create backend that excludes LLM events
    backend = FilteredFileBackend(
        filepath="filtered_traces.jsonl", excluded_types=[TraceType.LLM]
    )
    tracer = Tracer(backend=backend)

    # This will be saved
    tracer.log(TraceType.USER, ActionType.INPUT, message="Hello")

    # This will be filtered out
    tracer.log(TraceType.LLM, ActionType.REQUEST, prompt="Generate response")

    # This will be saved
    tracer.log(TraceType.AGENT, ActionType.PROCESS, label="Processing")

    tracer.flush()
    print(f"Filtered traces saved to: {backend.filepath}")


# Example 2: Async tracing
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
    tracer = Tracer()

    # Start async agent
    agent_id = tracer.log(
        TraceType.AGENT, ActionType.START, name="AsyncAgent", args={"mode": "parallel"}
    )

    # Run multiple async operations in parallel
    async with tracer.trace(
        TraceType.AGENT,
        ActionType.PROCESS,
        parent_id=agent_id,
        label="Parallel Operations",
    ):
        # Create tasks
        tasks = []

        # LLM calls
        for i in range(3):

            async def llm_task(idx):
                llm_id = tracer.log(
                    TraceType.LLM,
                    ActionType.REQUEST,
                    model="gpt-4",
                    args={"prompt": f"Query {idx}"},
                )
                result = await async_llm_call(f"Query {idx}")
                tracer.log(
                    TraceType.LLM, ActionType.RESPOND, parent_id=llm_id, response=result
                )
                return result

            tasks.append(llm_task(i))

        # Tool calls
        for tool in ["search", "calculator"]:

            async def tool_task(tool_name):
                tool_id = tracer.log(
                    TraceType.TOOL,
                    ActionType.CALL,
                    name=tool_name,
                    args={"query": "test"},
                )
                result = await async_tool_call(tool_name, {"query": "test"})
                tracer.log(
                    TraceType.TOOL, ActionType.RESPOND, parent_id=tool_id, result=result
                )
                return result

            tasks.append(tool_task(tool))

        # Wait for all tasks
        results = await asyncio.gather(*[task for task in tasks])

        # Log results
        tracer.log(
            TraceType.AGENT,
            ActionType.PROCESS,
            label="Aggregated Results",
            results=results,
        )

    # End agent
    tracer.log(TraceType.AGENT, ActionType.END, parent_id=agent_id)

    tracer.flush()
    print(f"Async traces saved to: {tracer.backend.filepath}")


# Example 3: Performance monitoring
def example_performance_monitoring():
    """Demonstrate using traces for performance monitoring."""
    tracer = Tracer(backend=InMemoryBackend())
    set_global_tracer(tracer)

    @trace_function()
    def slow_operation(duration: float):
        """Simulate slow operation."""
        time.sleep(duration)
        return f"Completed in {duration}s"

    @trace_function()
    def fast_operation():
        """Simulate fast operation."""
        time.sleep(0.01)
        return "Done quickly"

    # Run operations
    with tracer.trace(TraceType.AGENT, ActionType.START, name="PerformanceTest"):
        slow_operation(0.2)
        fast_operation()
        slow_operation(0.3)

        # Parallel operations
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(slow_operation, 0.1),
                executor.submit(fast_operation),
                executor.submit(slow_operation, 0.15),
            ]
            for future in futures:
                future.result()

    # Analyze performance
    events = tracer.backend.load()

    print("\nPerformance Analysis:")
    print("-" * 50)

    # Calculate durations for paired events
    event_pairs = {}
    for event in events:
        if event.action in [ActionType.START, ActionType.REQUEST, ActionType.CALL]:
            event_pairs[event.id] = {"start": event, "end": None}

    for event in events:
        if (
            event.action in [ActionType.END, ActionType.RESPOND]
            and event.parent_id in event_pairs
        ):
            event_pairs[event.parent_id]["end"] = event

    # Print performance metrics
    for pair_id, pair in event_pairs.items():
        if pair["start"] and pair["end"]:
            duration = (pair["end"].timestamp - pair["start"].timestamp).total_seconds()
            details = pair["start"].details

            print(
                f"{pair['start'].type.value} - {details.get('function', details.get('name', 'Unknown'))}: {duration:.3f}s"
            )

    print("-" * 50)


# Example 4: Error tracking and recovery
def example_error_tracking():
    """Demonstrate error tracking and recovery patterns."""
    tracer = Tracer()

    def risky_operation(should_fail: bool = False):
        """Operation that might fail."""
        if should_fail:
            raise ValueError("Simulated error")
        return "Success"

    # Start agent with error handling
    with tracer.trace(TraceType.AGENT, ActionType.START, name="ErrorHandlingAgent"):
        # Try operation that succeeds
        try:
            with tracer.trace(
                TraceType.AGENT, ActionType.PROCESS, label="Attempt 1"
            ) as attempt_ctx:
                result = risky_operation(should_fail=False)
                tracer.log(
                    TraceType.AGENT,
                    ActionType.PROCESS,
                    parent_id=attempt_ctx.id,
                    label="Success",
                    result=result,
                )
        except Exception as e:
            tracer.log(
                TraceType.AGENT,
                ActionType.PROCESS,
                parent_id=attempt_ctx.id,
                label="Error",
                error=str(e),
                error_type=type(e).__name__,
            )

        # Try operation that fails with recovery
        try:
            with tracer.trace(
                TraceType.AGENT, ActionType.PROCESS, label="Attempt 2"
            ) as attempt_ctx:
                result = risky_operation(should_fail=True)
                tracer.log(
                    TraceType.AGENT,
                    ActionType.PROCESS,
                    parent_id=attempt_ctx.id,
                    label="Success",
                    result=result,
                )
        except Exception as e:
            tracer.log(
                TraceType.AGENT,
                ActionType.PROCESS,
                parent_id=attempt_ctx.id,
                label="Error Caught",
                error=str(e),
                error_type=type(e).__name__,
            )

            # Recovery strategy
            with tracer.trace(
                TraceType.AGENT,
                ActionType.PROCESS,
                parent_id=attempt_ctx.id,
                label="Recovery Strategy",
            ):
                # Try alternative approach
                tracer.log(
                    TraceType.AGENT,
                    ActionType.PROCESS,
                    label="Using Fallback",
                    strategy="default_value",
                )
                result = "Fallback result"

        # Log final status
        tracer.log(
            TraceType.AGENT,
            ActionType.PROCESS,
            label="Final Result",
            result=result,
            had_errors=True,
        )

    tracer.flush()
    print(f"Error tracking traces saved to: {tracer.backend.filepath}")


# Example 5: Multi-modal tracing (text, image, audio references)
def example_multimodal_tracing():
    """Demonstrate tracing multi-modal AI operations."""
    tracer = Tracer()

    # User uploads image
    user_id = tracer.log(
        TraceType.USER,
        ActionType.INPUT,
        message="Analyze this image",
        attachments=[{"type": "image", "path": "/tmp/user_image.jpg"}],
    )

    # Vision model analysis
    with tracer.trace(
        TraceType.AGENT, ActionType.START, parent_id=user_id, name="VisionAgent"
    ):
        # Image preprocessing
        tracer.log(
            TraceType.AGENT,
            ActionType.PROCESS,
            label="Preprocessing",
            operations=["resize", "normalize"],
            image_size=(1024, 1024),
        )

        # Vision model call
        with tracer.trace(
            TraceType.LLM,
            ActionType.REQUEST,
            model="gpt-4-vision",
            args={"image_path": "/tmp/user_image.jpg", "prompt": "Describe this image"},
        ) as vision_ctx:
            time.sleep(0.2)  # Simulate processing
            tracer.log(
                TraceType.LLM,
                ActionType.RESPOND,
                parent_id=vision_ctx.id,
                model="gpt-4-vision",
                response="The image shows a sunset over mountains",
                detected_objects=["sun", "mountains", "clouds"],
            )

        # Generate audio description
        tracer.log(
            TraceType.AGENT,
            ActionType.PROCESS,
            label="Generate Audio",
            text="The image shows a sunset over mountains",
        )

        with tracer.trace(
            TraceType.TOOL,
            ActionType.CALL,
            name="text_to_speech",
            args={
                "text": "The image shows a sunset over mountains",
                "voice": "natural",
            },
        ) as tts_ctx:
            time.sleep(0.1)
            tracer.log(
                TraceType.TOOL,
                ActionType.RESPOND,
                parent_id=tts_ctx.id,
                name="text_to_speech",
                result={"audio_path": "/tmp/description.mp3", "duration": 3.5},
            )

        # Final multi-modal response
        tracer.log(
            TraceType.AGENT,
            ActionType.PROCESS,
            label="Multi-modal Response",
            response={
                "text": "The image shows a sunset over mountains",
                "audio": "/tmp/description.mp3",
                "metadata": {
                    "detected_objects": ["sun", "mountains", "clouds"],
                    "dominant_colors": ["orange", "purple", "blue"],
                },
            },
        )

    tracer.flush()
    print(f"Multi-modal traces saved to: {tracer.backend.filepath}")


if __name__ == "__main__":
    print("=== Example 1: Custom Backend ===")
    example_custom_backend()
    print("\n" + "=" * 50 + "\n")

    print("=== Example 2: Async Tracing ===")
    asyncio.run(example_async_tracing())
    print("\n" + "=" * 50 + "\n")

    print("=== Example 3: Performance Monitoring ===")
    example_performance_monitoring()
    print("\n" + "=" * 50 + "\n")

    print("=== Example 4: Error Tracking ===")
    example_error_tracking()
    print("\n" + "=" * 50 + "\n")

    print("=== Example 5: Multi-modal Tracing ===")
    example_multimodal_tracing()
