"""
Tests for the main API.
"""

from sybil_scope import ActionType, FileBackend, InMemoryBackend, Tracer, TraceType
from sybil_scope.backend import Backend


class FakeBackend(Backend):
    """Simple backend implementation to verify flush/save without using mocks."""

    def __init__(self):
        self.events = []
        self.flushed = False

    def save(self, event):
        self.events.append(event)

    def flush(self):
        self.flushed = True

    def load(self):
        return list(self.events)


class TestTracer:
    def test_init_default_backend(self):
        tracer = Tracer()
        assert isinstance(tracer.backend, FileBackend)
        assert len(tracer._context_stack) == 0
        assert tracer._current_context is None

    def test_init_custom_backend(self):
        backend = InMemoryBackend()
        tracer = Tracer(backend=backend)
        assert tracer.backend is backend

    def test_log_simple_event(self):
        backend = InMemoryBackend()
        tracer = Tracer(backend=backend)

        # Log event
        event_id = tracer.log(TraceType.USER, ActionType.INPUT, message="Hello")

        # Check event was saved
        events = backend.load()
        assert len(events) == 1
        assert events[0].id == event_id
        assert events[0].type == TraceType.USER
        assert events[0].action == ActionType.INPUT
        assert events[0].details["message"] == "Hello"

    def test_log_with_parent_context(self):
        backend = InMemoryBackend()
        tracer = Tracer(backend=backend)

        # Create parent context
        with tracer.trace(TraceType.AGENT, ActionType.START) as ctx:
            # Log child event
            child_id = tracer.log(TraceType.LLM, ActionType.REQUEST, prompt="Test")

            # Check parent relationship
            events = backend.load()
            child_event = next(e for e in events if e.id == child_id)
            assert child_event.parent_id == ctx.id

    def test_trace_context_manager(self):
        backend = InMemoryBackend()
        tracer = Tracer(backend=backend)

        # Use trace context
        with tracer.trace(TraceType.AGENT, ActionType.START, name="TestAgent") as ctx:
            assert tracer._current_context is not None
            assert tracer._current_context.event.type == TraceType.AGENT
            assert tracer._current_context.event.details["name"] == "TestAgent"
            assert ctx.id == tracer._current_context.id

        # Context should be cleared
        assert tracer._current_context is None

        # Check events
        events = backend.load()
        assert len(events) == 2  # START and END
        assert events[0].action == ActionType.START
        assert events[1].action == ActionType.END

    def test_nested_trace_contexts(self):
        backend = InMemoryBackend()
        tracer = Tracer(backend=backend)

        with tracer.trace(TraceType.AGENT, ActionType.START) as outer_ctx:
            outer_id = outer_ctx.id

            with tracer.trace(TraceType.LLM, ActionType.REQUEST) as inner_ctx:
                inner_id = inner_ctx.id

                # Check nesting
                assert tracer._current_context.id == inner_id
                assert len(tracer._context_stack) == 2

                # Log event in inner context
                tracer.log(TraceType.LLM, ActionType.RESPOND, response="Test")

            # Back to outer context
            assert tracer._current_context.id == outer_id
            assert len(tracer._context_stack) == 1

        # All contexts cleared
        assert tracer._current_context is None
        assert len(tracer._context_stack) == 0

        # Verify parent relationships
        events = backend.load()
        inner_event = next(e for e in events if e.id == inner_id)
        assert inner_event.parent_id == outer_id

    def test_trace_string_types(self):
        backend = InMemoryBackend()
        tracer = Tracer(backend=backend)

        # Use string types
        with tracer.trace("agent", "start"):
            tracer.log("llm", "request", prompt="Test")

        events = backend.load()
        assert events[0].type == TraceType.AGENT
        assert events[0].action == ActionType.START
        assert events[1].type == TraceType.LLM
        assert events[1].action == ActionType.REQUEST

    def test_flush(self):
        backend = FakeBackend()
        tracer = Tracer(backend=backend)

        tracer.flush()
        assert backend.flushed is True

    def test_get_current_context(self):
        backend = InMemoryBackend()
        tracer = Tracer(backend=backend)

        # No context
        assert tracer.get_current_context() is None

        # With context
        with tracer.trace(TraceType.AGENT, ActionType.START) as ctx:
            current = tracer.get_current_context()
            assert current is not None
            assert current.id == ctx.id

    def test_non_agent_trace_no_end_event(self):
        backend = InMemoryBackend()
        tracer = Tracer(backend=backend)

        # LLM trace should not generate END event
        with tracer.trace(TraceType.LLM, ActionType.REQUEST):
            pass

        events = backend.load()
        assert len(events) == 1
        assert events[0].action == ActionType.REQUEST

    def test_explicit_parent_id(self):
        backend = InMemoryBackend()
        tracer = Tracer(backend=backend)

        # Create parent
        parent_id = tracer.log(TraceType.USER, ActionType.INPUT)

        # Use explicit parent_id
        with tracer.trace(TraceType.AGENT, ActionType.START, parent_id=parent_id):
            # This should also use the explicit parent
            tracer.log(TraceType.LLM, ActionType.REQUEST, parent_id=12345)

        events = backend.load()

        # Check agent has correct parent
        agent_event = next(
            e
            for e in events
            if e.type == TraceType.AGENT and e.action == ActionType.START
        )
        assert agent_event.parent_id == parent_id

        # Check LLM has explicit parent
        llm_event = next(e for e in events if e.type == TraceType.LLM)
        assert llm_event.parent_id == 12345
