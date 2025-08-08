"""
Tests for core functionality.
"""

from datetime import datetime
from sybil_scope.core import TraceType, ActionType, TraceEvent, TraceContext


class TestTraceType:
    def test_trace_type_values(self):
        assert TraceType.USER == "user"
        assert TraceType.AGENT == "agent"
        assert TraceType.LLM == "llm"
        assert TraceType.TOOL == "tool"


class TestActionType:
    def test_action_type_values(self):
        assert ActionType.INPUT == "input"
        assert ActionType.START == "start"
        assert ActionType.END == "end"
        assert ActionType.PROCESS == "process"
        assert ActionType.REQUEST == "request"
        assert ActionType.RESPOND == "respond"
        assert ActionType.CALL == "call"


class TestTraceEvent:
    def test_create_basic_event(self):
        event = TraceEvent(
            type=TraceType.USER, action=ActionType.INPUT, details={"message": "Hello"}
        )

        assert event.type == TraceType.USER
        assert event.action == ActionType.INPUT
        assert event.details == {"message": "Hello"}
        assert event.parent_id is None
        assert isinstance(event.id, int)
        assert isinstance(event.timestamp, datetime)

    def test_create_event_with_parent(self):
        parent_event = TraceEvent(type=TraceType.USER, action=ActionType.INPUT)
        child_event = TraceEvent(
            type=TraceType.AGENT, action=ActionType.START, parent_id=parent_event.id
        )

        assert child_event.parent_id == parent_event.id

    def test_event_serialization(self):
        event = TraceEvent(
            type=TraceType.LLM,
            action=ActionType.REQUEST,
            details={"model": "gpt-4", "prompt": "Test"},
        )

        # Serialize to dict
        data = event.model_dump()
        assert data["type"] == "llm"
        assert data["action"] == "request"
        assert data["details"]["model"] == "gpt-4"

        # Serialize to JSON
        json_str = event.model_dump_json()
        assert '"type":"llm"' in json_str
        assert '"action":"request"' in json_str

    def test_event_deserialization(self):
        data = {
            "timestamp": "2023-10-01T12:00:00.000000Z",
            "type": "agent",
            "action": "process",
            "id": 12345,
            "parent_id": 67890,
            "details": {"label": "Test"},
        }

        event = TraceEvent(**data)
        assert event.type == TraceType.AGENT
        assert event.action == ActionType.PROCESS
        assert event.id == 12345
        assert event.parent_id == 67890
        assert event.details["label"] == "Test"


class TestTraceContext:
    def test_create_context(self):
        event = TraceEvent(type=TraceType.AGENT, action=ActionType.START)
        context = TraceContext(event)

        assert context.event == event
        assert context.id == event.id
        assert len(context.children) == 0

    def test_add_child(self):
        parent_event = TraceEvent(type=TraceType.AGENT, action=ActionType.START)
        context = TraceContext(parent_event)

        child_event = TraceEvent(
            type=TraceType.LLM, action=ActionType.REQUEST, parent_id=parent_event.id
        )

        context.add_child(child_event)
        assert len(context.children) == 1
        assert context.children[0] == child_event
