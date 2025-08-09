"""
Sibyl Scope - Comprehensive tracing and observability toolkit for Python AI/LLM applications.
"""

from sybil_scope._version import __version__  # noqa
from sybil_scope.api import Tracer
from sybil_scope.backend import Backend, FileBackend, InMemoryBackend
from sybil_scope.config import (
    ConfigKey,
    configure_backend,
    get_option,
    option_context,
    reset_option,
    set_option,
)
from sybil_scope.core import ActionType, TraceEvent, TraceType
from sybil_scope.decorators import (
    trace_function,
    trace_llm,
    trace_tool,
)

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
    viewer_app = None  # type:ignore
