"""
Sibyl Scope - Comprehensive tracing and observability toolkit for Python AI/LLM applications.
"""

from .api import Tracer
from .backend import Backend, FileBackend, InMemoryBackend
from .config import (
    ConfigKey,
    configure_backend,
    get_option,
    option_context,
    reset_option,
    set_option,
)
from .core import ActionType, TraceEvent, TraceType
from .decorators import (
    trace_function,
    trace_llm,
    trace_tool,
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
    "ConfigKey",
    "set_option",
    "get_option",
    "reset_option",
    "option_context",
    "configure_backend",
    "trace_function",
    "trace_llm",
    "trace_tool",
]

# Viewer components are available as optional imports
try:
    from sybil_scope.viewer import app as viewer_app
except ImportError:
    # Viewer dependencies not installed
    viewer_app = None
