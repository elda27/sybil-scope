"""
Public API for the Sibyl Scope tracing library.
"""

from contextlib import contextmanager
from datetime import datetime

from .backend import Backend, FileBackend
from .core import ActionType, TraceContext, TraceEvent, TraceType


class Tracer:
    """Main interface for tracing AI/LLM applications."""

    def __init__(self, backend: Backend | None = None):
        """Initialize tracer with a backend for storing traces.

        Args:
            backend: Backend instance for storing traces. Defaults to FileBackend.
        """
        self.backend = backend or FileBackend()
        self._context_stack: list[TraceContext] = []
        self._current_context: TraceContext | None = None

    @contextmanager
    def trace(
        self,
        trace_type: TraceType | str,
        action: ActionType | str,
        parent_id: int | None = None,
        **details,
    ):
        """Context manager for tracing a block of code.

        Args:
            trace_type: Type of trace (user, agent, llm, tool)
            action: Action being performed
            parent_id: ID of parent trace event
            **details: Additional details to include in trace
        """
        # Convert string types to enums
        if isinstance(trace_type, str):
            trace_type = TraceType(trace_type)
        if isinstance(action, str):
            action = ActionType(action)

        # Create trace event
        event = TraceEvent(
            timestamp=datetime.now(),
            type=trace_type,
            action=action,
            parent_id=parent_id
            or (self._current_context.event.id if self._current_context else None),
            details=details,
        )

        # Create context and push to stack
        context = TraceContext(event)
        self._context_stack.append(context)
        self._current_context = context

        # Log start event
        self.backend.save(event)

        try:
            yield context
        finally:
            # Pop context from stack
            self._context_stack.pop()
            self._current_context = (
                self._context_stack[-1] if self._context_stack else None
            )

            # Log end event if this was an agent
            if trace_type == TraceType.AGENT and action == ActionType.START:
                end_event = TraceEvent(
                    timestamp=datetime.now(),
                    type=TraceType.AGENT,
                    action=ActionType.END,
                    parent_id=event.parent_id,
                    details={},
                )
                self.backend.save(end_event)

    def log(
        self,
        trace_type: TraceType | str,
        action: ActionType | str,
        parent_id: int | None = None,
        **details,
    ):
        """Log a single trace event.

        Args:
            trace_type: Type of trace
            action: Action being performed
            parent_id: ID of parent trace event
            **details: Additional details to include in trace
        """
        # Convert string types to enums
        if isinstance(trace_type, str):
            trace_type = TraceType(trace_type)
        if isinstance(action, str):
            action = ActionType(action)

        event = TraceEvent(
            timestamp=datetime.now(),
            type=trace_type,
            action=action,
            parent_id=parent_id
            or (self._current_context.event.id if self._current_context else None),
            details=details,
        )

        self.backend.save(event)
        return event.id

    def get_current_context(self) -> TraceContext | None:
        """Get the current trace context."""
        return self._current_context

    def flush(self):
        """Flush any pending traces to the backend."""
        self.backend.flush()
