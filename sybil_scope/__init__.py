"""
Sibyl Scope - Comprehensive tracing and observability toolkit for Python AI/LLM applications.
"""

from .api import Tracer
from .core import TraceType, ActionType, TraceEvent
from .backend import Backend, FileBackend, InMemoryBackend
from .decorators import (
    trace_function,
    trace_llm,
    trace_tool,
    set_global_tracer,
    get_global_tracer,
)

__version__ = "0.1.0"
__all__ = [
    "Tracer",
    "TraceType",
    "ActionType",
    "TraceEvent",
    "Backend",
    "FileBackend",
    "InMemoryBackend",
    "trace_function",
    "trace_llm",
    "trace_tool",
    "set_global_tracer",
    "get_global_tracer",
]

# Viewer components are available as optional imports
try:
    from sybil_scope.viewer import app as viewer_app
except ImportError:
    # Viewer dependencies not installed
    viewer_app = None
