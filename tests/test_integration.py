"""
Integration tests for Sibyl Scope.
"""

import json
import tempfile
import time
from pathlib import Path

from sybil_scope import (
    ActionType,
    FileBackend,
    InMemoryBackend,
    Tracer,
    TraceType,
    trace_function,
    trace_tool,
)


class TestEndToEndScenarios:
    def test_complete_agent_workflow(self):
        """Test a complete agent workflow with all trace types."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".jsonl") as f:
            filepath = Path(f.name)

        try:
            tracer = Tracer(backend=FileBackend(filepath))

            # User input
            user_id = tracer.log(
                TraceType.USER, ActionType.INPUT, message="What's the weather in Paris?"
            )

            # Agent processing
            with tracer.trace(
                TraceType.AGENT,
                ActionType.START,
                parent_id=user_id,
                name="WeatherAgent",
            ):
                # LLM planning
                with tracer.trace(
                    TraceType.LLM,
                    ActionType.REQUEST,
                    model="gpt-4",
                    args={"prompt": "Plan weather query"},
                ) as llm_ctx:
                    time.sleep(0.01)  # Simulate processing
                    tracer.log(
                        TraceType.LLM,
                        ActionType.RESPOND,
                        parent_id=llm_ctx.id,
                        response="Need to call weather API for Paris",
                    )

                # Tool call
                with tracer.trace(
                    TraceType.TOOL,
                    ActionType.CALL,
                    name="weather_api",
                    args={"city": "Paris"},
                ) as tool_ctx:
                    time.sleep(0.01)
                    tracer.log(
                        TraceType.TOOL,
                        ActionType.RESPOND,
                        parent_id=tool_ctx.id,
                        result={"temp": 18, "condition": "cloudy"},
                    )

                # Format response
                with tracer.trace(
                    TraceType.LLM,
                    ActionType.REQUEST,
                    model="gpt-4",
                    args={"prompt": "Format weather data"},
                ) as llm_ctx:
                    tracer.log(
                        TraceType.LLM,
                        ActionType.RESPOND,
                        parent_id=llm_ctx.id,
                        response="It's 18°C and cloudy in Paris",
                    )

                # Final response
                tracer.log(
                    TraceType.AGENT,
                    ActionType.PROCESS,
                    label="Final Response",
                    response="It's 18°C and cloudy in Paris",
                )

            # Ensure all events are written
            tracer.flush()

            # Verify the trace structure
            events = tracer.backend.load()

            # Should have all event types
            event_types = {e.type for e in events}
            assert TraceType.USER in event_types
            assert TraceType.AGENT in event_types
            assert TraceType.LLM in event_types
            assert TraceType.TOOL in event_types

            # Verify parent-child relationships
            user_event = next(e for e in events if e.type == TraceType.USER)
            agent_start = next(
                e
                for e in events
                if e.type == TraceType.AGENT and e.action == ActionType.START
            )
            assert agent_start.parent_id == user_event.id

            # Verify chronological order
            timestamps = [e.timestamp for e in events]
            assert timestamps == sorted(timestamps)

        finally:
            filepath.unlink(missing_ok=True)

    def test_error_handling_workflow(self):
        """Test workflow with errors and recovery."""
        backend = InMemoryBackend()
        tracer = Tracer(backend=backend)

        @trace_tool("database", tracer=tracer)
        def query_db(query):
            if "DROP" in query:
                raise ValueError("Dangerous query detected")
            return [{"id": 1, "name": "Test"}]

        @trace_function(tracer=tracer)
        def safe_query_wrapper(query):
            try:
                return query_db(query)
            except ValueError as e:
                # Log error and use cached data
                tracer.log(
                    TraceType.AGENT,
                    ActionType.PROCESS,
                    label="Error Recovery",
                    error=str(e),
                    fallback="Using cached data",
                )
                return [{"id": 0, "name": "Cached"}]

        # Test safe query
        result1 = safe_query_wrapper("SELECT * FROM users")
        assert result1[0]["id"] == 1

        # Test dangerous query with recovery
        result2 = safe_query_wrapper("DROP TABLE users")
        assert result2[0]["id"] == 0

        # Verify error was logged
        events = backend.load()
        error_events = [e for e in events if "error" in e.details]
        assert len(error_events) > 0
        assert "Dangerous query detected" in error_events[0].details["error"]

    def test_parallel_operations(self):
        """Test tracing parallel operations."""
        from concurrent.futures import ThreadPoolExecutor

        backend = InMemoryBackend()
        tracer = Tracer(backend=backend)

        def parallel_task(task_id, tracer):
            with tracer.trace(
                TraceType.AGENT, ActionType.PROCESS, label=f"Task {task_id}"
            ):
                time.sleep(0.01)
                tracer.log(
                    TraceType.AGENT,
                    ActionType.PROCESS,
                    label="Result",
                    task_id=task_id,
                    result=f"Task {task_id} completed",
                )

        # Run tasks in parallel
        with tracer.trace(TraceType.AGENT, ActionType.START, name="ParallelProcessor"):
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = []
                for i in range(3):
                    future = executor.submit(parallel_task, i, tracer)
                    futures.append(future)

                # Wait for all tasks
                for future in futures:
                    future.result()

        # Verify all tasks were traced
        events = backend.load()
        task_events = [
            e for e in events if e.details.get("label", "").startswith("Task")
        ]
        assert len(task_events) == 3

        # Verify task results
        result_events = [e for e in events if e.details.get("label") == "Result"]
        assert len(result_events) == 3
        task_ids = {e.details["task_id"] for e in result_events}
        assert task_ids == {0, 1, 2}

    def test_nested_agents(self):
        """Test deeply nested agent calls."""
        backend = InMemoryBackend()
        tracer = Tracer(backend=backend)

        def create_nested_agents(depth, parent_id=None):
            if depth == 0:
                return "Leaf result"

            with tracer.trace(
                TraceType.AGENT,
                ActionType.START,
                parent_id=parent_id,
                name=f"Agent Level {depth}",
            ) as ctx:
                # Process at this level
                tracer.log(
                    TraceType.AGENT,
                    ActionType.PROCESS,
                    label=f"Processing at level {depth}",
                )

                # Call nested agent
                result = create_nested_agents(depth - 1, ctx.id)

                # Return result
                tracer.log(
                    TraceType.AGENT,
                    ActionType.PROCESS,
                    label="Returning result",
                    result=result,
                )

                return f"Level {depth}: {result}"

        # Create 3 levels of nesting
        create_nested_agents(3)

        # Verify structure
        events = backend.load()
        agent_starts = [
            e
            for e in events
            if e.type == TraceType.AGENT and e.action == ActionType.START
        ]
        assert len(agent_starts) == 3

        # Verify nesting
        level_3 = next(e for e in agent_starts if "Level 3" in e.details["name"])
        level_2 = next(e for e in agent_starts if "Level 2" in e.details["name"])
        level_1 = next(e for e in agent_starts if "Level 1" in e.details["name"])

        assert level_2.parent_id == level_3.id
        assert level_1.parent_id == level_2.id

    def test_trace_persistence_and_reload(self):
        """Test saving and reloading traces."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".jsonl") as f:
            filepath = Path(f.name)

        try:
            # Create traces with first tracer
            tracer1 = Tracer(backend=FileBackend(filepath))

            tracer1.log(TraceType.USER, ActionType.INPUT, message="First session")
            with tracer1.trace(TraceType.AGENT, ActionType.START):
                tracer1.log(TraceType.LLM, ActionType.REQUEST, prompt="Test")
            tracer1.flush()

            # Create new tracer with same file (append mode)
            tracer2 = Tracer(backend=FileBackend(filepath))

            tracer2.log(TraceType.USER, ActionType.INPUT, message="Second session")
            tracer2.flush()

            # Load all events
            all_events = tracer2.backend.load()

            # Should have events from both sessions
            user_events = [e for e in all_events if e.type == TraceType.USER]
            assert len(user_events) == 2
            assert user_events[0].details["message"] == "First session"
            assert user_events[1].details["message"] == "Second session"

            # Verify file format
            with open(filepath, "r") as f:
                lines = f.readlines()
                for line in lines:
                    # Each line should be valid JSON
                    data = json.loads(line.strip())
                    assert "timestamp" in data
                    assert "type" in data
                    assert "action" in data
                    assert "id" in data

        finally:
            filepath.unlink(missing_ok=True)
