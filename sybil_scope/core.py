"""
Core data models and types for Sibyl Scope.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.functional_serializers import PlainSerializer

# Custom datetime serializer for JSON output
IsoDateTime = Annotated[
    datetime,
    PlainSerializer(
        lambda x: x.strftime("%Y-%m-%dT%H:%M:%S.%fZ"), return_type=str, when_used="json"
    ),
]


class TraceType(str, Enum):
    """Types of trace events."""

    USER = "user"
    AGENT = "agent"
    LLM = "llm"
    TOOL = "tool"


class ActionType(str, Enum):
    """Types of actions in trace events."""

    INPUT = "input"
    START = "start"
    END = "end"
    PROCESS = "process"
    REQUEST = "request"
    RESPOND = "respond"
    CALL = "call"


def _generate_trace_id() -> int:
    """Generate a unique trace ID using UUID."""
    return uuid.uuid4().int >> 64  # Use upper 64 bits for smaller int


class TraceEvent(BaseModel):
    """Represents a single trace event in the Sibyl Scope tracing system."""

    model_config = ConfigDict()

    timestamp: IsoDateTime = Field(
        default_factory=datetime.now,
        description="UTC timestamp when the trace event occurred",
    )
    type: TraceType = Field(description="Type of trace event (user, agent, llm, tool)")
    action: ActionType = Field(
        description="Action being performed (input, start, end, process, request, respond, call)"
    )
    id: int = Field(
        default_factory=_generate_trace_id,
        description="Unique identifier for this trace event",
    )
    parent_id: int | None = Field(
        default=None, description="ID of the parent trace event, if any"
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional details and metadata for the trace event",
    )


class TraceContext:
    """Context for managing nested traces."""

    def __init__(self, event: TraceEvent):
        self.event = event
        self.children: list[TraceEvent] = []

    def add_child(self, child: TraceEvent):
        """Add a child event to this context."""
        self.children.append(child)

    @property
    def id(self) -> int:
        """Get the ID of this context's event."""
        return self.event.id
