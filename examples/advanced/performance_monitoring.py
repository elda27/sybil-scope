"""
Performance monitoring example.
Shows how to use traces for performance analysis and optimization.
"""

import time
from concurrent.futures import ThreadPoolExecutor

import sybil_scope as ss


def example_performance_monitoring():
    """Demonstrate using traces for performance monitoring."""
    # Use in-memory for performance example to avoid file IO
    tracer = ss.Tracer(backend=ss.InMemoryBackend())

    @ss.trace_function(tracer=tracer)
    def slow_operation(duration: float):
        """Simulate slow operation."""
        time.sleep(duration)
        return f"Completed in {duration}s"

    @ss.trace_function(tracer=tracer)
    def fast_operation():
        """Simulate fast operation."""
        time.sleep(0.01)
        return "Done quickly"

    # Run operations
    with tracer.trace(ss.TraceType.AGENT, ss.ActionType.START, name="PerformanceTest"):
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
        if event.action in [
            ss.ActionType.START,
            ss.ActionType.REQUEST,
            ss.ActionType.CALL,
        ]:
            event_pairs[event.id] = {"start": event, "end": None}

    for event in events:
        if (
            event.action in [ss.ActionType.END, ss.ActionType.RESPOND]
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


if __name__ == "__main__":
    print("=== Performance Monitoring Example ===")
    with ss.option_context((ss.ConfigKey.TRACING_FILE_PREFIX, "performance")):
        example_performance_monitoring()
