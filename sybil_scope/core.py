"""
Core data models and types for Sibyl Scope.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
import uuid


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


class TraceEvent(BaseModel):
    """Represents a single trace event."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    type: TraceType
    action: ActionType
    id: int = Field(default_factory=lambda: uuid.uuid4().int >> 64)  # Use upper 64 bits for smaller int
    parent_id: Optional[int] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        }


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