"""
Tests for decorator functionality.
"""

import pytest

from sybil_scope import (
    ActionType,
    InMemoryBackend,
    Tracer,
    TraceType,
    trace_function,
    trace_llm,
    trace_tool,
)


class TestGlobalTracer:
    def test_no_global_tracer_api(self):
        # Library no longer exposes global tracer helpers
        # This test ensures the explicit tracer path works.
        backend = InMemoryBackend()
        tracer = Tracer(backend=backend)

        @trace_function(tracer=tracer)
        def f():
            return 1

        assert f() == 1


class TestTraceFunctionDecorator:
    def test_basic_function_tracing(self):
        backend = InMemoryBackend()
        tracer = Tracer(backend=backend)

        @trace_function(tracer=tracer)
        def test_func(x, y):
            return x + y

        result = test_func(2, 3)
        assert result == 5

        # Check traces
        events = backend.load()
        assert len(events) == 2  # Start and response

        # Check start event
        start_event = events[0]
        assert start_event.type == TraceType.AGENT
        assert start_event.action == ActionType.PROCESS
        assert start_event.details["function"] == "test_func"
        assert start_event.details["args"] == (2, 3)
        assert start_event.details["kwargs"] == {}

        # Check response event
        response_event = events[1]
        assert response_event.type == TraceType.AGENT
        assert response_event.action == ActionType.RESPOND
        assert response_event.details["result"] == 5

    def test_function_with_kwargs(self):
        backend = InMemoryBackend()
        tracer = Tracer(backend=backend)

        @trace_function(tracer=tracer)
        def test_func(a, b=10):
            return a * b

        result = test_func(5, b=20)
        assert result == 100

        events = backend.load()
        start_event = events[0]
        assert start_event.details["args"] == (5,)
        assert start_event.details["kwargs"] == {"b": 20}

    def test_function_with_exception(self):
        backend = InMemoryBackend()
        tracer = Tracer(backend=backend)

        @trace_function(tracer=tracer)
        def failing_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            failing_func()

        events = backend.load()
        assert len(events) == 2

        # Check error event
        error_event = events[1]
        assert error_event.action == ActionType.RESPOND
        assert error_event.details["error"] == "Test error"
        assert error_event.details["error_type"] == "ValueError"

    def test_custom_trace_type_and_action(self):
        backend = InMemoryBackend()
        tracer = Tracer(backend=backend)

        @trace_function(
            trace_type=TraceType.TOOL, action=ActionType.CALL, tracer=tracer
        )
        def tool_func():
            return "tool result"

        tool_func()

        events = backend.load()
        assert events[0].type == TraceType.TOOL
        assert events[0].action == ActionType.CALL

    def test_no_capture_args_or_result(self):
        backend = InMemoryBackend()
        tracer = Tracer(backend=backend)

        @trace_function(capture_args=False, capture_result=False, tracer=tracer)
        def test_func(secret_arg):
            return "secret_result"

        test_func("sensitive_data")

        events = backend.load()
        assert len(events) == 1  # Only start event

        start_event = events[0]
        assert "args" not in start_event.details
        assert "kwargs" not in start_event.details

    def test_with_no_explicit_tracer(self):
        # Without explicit tracer, function runs without tracing
        @trace_function()  # No tracer param
        def test_func():
            return "no trace"

        assert test_func() == "no trace"

    def test_no_tracer_configured(self):
        @trace_function()
        def test_func():
            return "no trace"

        result = test_func()
        assert result == "no trace"


class TestTraceLLMDecorator:
    def test_llm_tracing(self):
        backend = InMemoryBackend()
        tracer = Tracer(backend=backend)

        @trace_llm(model="gpt-4", tracer=tracer)
        def call_llm(prompt, temperature=0.7):
            return f"Response to: {prompt}"

        call_llm("Hello", temperature=0.5)

        events = backend.load()
        assert len(events) == 2

        # Check request
        request_event = events[0]
        assert request_event.type == TraceType.LLM
        assert request_event.action == ActionType.REQUEST
        assert request_event.details["model"] == "gpt-4"
        assert request_event.details["args"]["prompt"] == "Hello"
        assert request_event.details["args"]["temperature"] == 0.5

        # Check response
        response_event = events[1]
        assert response_event.type == TraceType.LLM
        assert response_event.action == ActionType.RESPOND
        assert response_event.details["response"] == "Response to: Hello"

    def test_llm_with_positional_prompt(self):
        backend = InMemoryBackend()
        tracer = Tracer(backend=backend)

        @trace_llm(model="claude", tracer=tracer)
        def call_llm(prompt):
            return "Done"

        call_llm("Test prompt")

        events = backend.load()
        request_event = events[0]
        assert request_event.details["args"]["prompt"] == "Test prompt"

    def test_llm_with_error(self):
        backend = InMemoryBackend()
        tracer = Tracer(backend=backend)

        @trace_llm(model="gpt-4", tracer=tracer)
        def failing_llm(prompt):
            raise RuntimeError("API error")

        with pytest.raises(RuntimeError):
            failing_llm("test")

        events = backend.load()
        error_event = events[1]
        assert error_event.details["error"] == "API error"
        assert error_event.details["error_type"] == "RuntimeError"


class TestTraceToolDecorator:
    def test_tool_tracing(self):
        backend = InMemoryBackend()
        tracer = Tracer(backend=backend)

        @trace_tool("calculator", tracer=tracer)
        def add(x, y):
            return x + y

        result = add(10, 20)
        assert result == 30

        events = backend.load()
        assert len(events) == 2

        # Check call
        call_event = events[0]
        assert call_event.type == TraceType.TOOL
        assert call_event.action == ActionType.CALL
        assert call_event.details["name"] == "calculator"
        assert call_event.details["args"] == {"x": 10, "y": 20}

        # Check response
        response_event = events[1]
        assert response_event.type == TraceType.TOOL
        assert response_event.action == ActionType.RESPOND
        assert response_event.details["result"] == 30

    def test_tool_with_kwargs(self):
        backend = InMemoryBackend()
        tracer = Tracer(backend=backend)

        @trace_tool("search", tracer=tracer)
        def search(query, limit=10):
            return [f"Result {i}" for i in range(limit)]

        search(query="test", limit=3)

        events = backend.load()
        call_event = events[0]
        assert call_event.details["args"] == {"query": "test", "limit": 3}

    def test_tool_with_error(self):
        backend = InMemoryBackend()
        tracer = Tracer(backend=backend)

        @trace_tool("broken_tool", tracer=tracer)
        def broken():
            raise Exception("Tool failed")

        with pytest.raises(Exception):
            broken()

        events = backend.load()
        error_event = events[1]
        assert error_event.details["name"] == "broken_tool"
        assert error_event.details["error"] == "Tool failed"


class TestDecoratorIntegration:
    def test_nested_decorated_functions(self):
        backend = InMemoryBackend()
        tracer = Tracer(backend=backend)

        @trace_tool("weather", tracer=tracer)
        def get_weather(city):
            return f"Sunny in {city}"

        @trace_llm(model="gpt-4", tracer=tracer)
        def generate_response(data):
            return f"The weather is: {data}"

        @trace_function(tracer=tracer)
        def process_weather_request(city):
            weather_data = get_weather(city)
            response = generate_response(weather_data)
            return response

        process_weather_request("Tokyo")

        events = backend.load()

        # Should have events for all three functions
        function_names = [
            e.details.get("function") for e in events if "function" in e.details
        ]
        assert "process_weather_request" in function_names

        tool_names = [e.details.get("name") for e in events if "name" in e.details]
        assert "weather" in tool_names

        model_names = [e.details.get("model") for e in events if "model" in e.details]
        assert "gpt-4" in model_names
