"""
Custom backend implementation example.
Shows how to create and use custom backends for specialized tracing needs.
"""

import sybil_scope as ss


class FilteredFileBackend(ss.FileBackend):
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
        filepath="filtered_traces.jsonl", excluded_types=[ss.TraceType.LLM]
    )
    # Use the custom backend directly for this example
    tracer = ss.Tracer(backend=backend)

    # This will be saved
    tracer.log(ss.TraceType.USER, ss.ActionType.INPUT, message="Hello")

    # This will be filtered out
    tracer.log(ss.TraceType.LLM, ss.ActionType.REQUEST, prompt="Generate response")

    # This will be saved
    tracer.log(ss.TraceType.AGENT, ss.ActionType.PROCESS, label="Processing")

    tracer.flush()
    print(f"Filtered traces saved to: {backend.filepath}")


if __name__ == "__main__":
    print("=== Custom Backend Example ===")
    with ss.option_context((ss.ConfigKey.TRACING_FILE_PREFIX, "custom_backend")):
        example_custom_backend()
