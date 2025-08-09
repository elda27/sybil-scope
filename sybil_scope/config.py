"""
Global configuration for Sibyl Scope, inspired by pandas' options API.

API:
- set_option(key, value)
- get_option(key)
- reset_option(key=None)  # None resets all
- option_context(*pairs): context manager to temporarily set options

Additionally, `configure_tracer()` uses current options to create and
install a global tracer instance with the chosen backend.

Keys (str or Enum accepted):
- tracing.backend: "file" | "memory"
- tracing.file.path: str | pathlib.Path
- tracing.file.name_format: str
- tracing.file.buffer_size: int
"""

from __future__ import annotations

from contextlib import contextmanager
from enum import Enum
from pathlib import Path
from typing import Any, Iterator

from sybil_scope.backend import Backend, FileBackend, InMemoryBackend


class ConfigKey(str, Enum):
    TRACING_BACKEND = "tracing.backend"
    TRACING_FILE_PATH = "tracing.file.path"
    TRACING_FILE_NAME_FORMAT = "tracing.file.name_format"
    TRACING_FILE_BUFFER_SIZE = "tracing.file.buffer_size"
    TRACING_FILE_PREFIX = "tracing.file.prefix"


_DEFAULTS: dict[str, Any] = {
    ConfigKey.TRACING_BACKEND.value: "file",  # file | memory
    ConfigKey.TRACING_FILE_PATH.value: None,  # default auto-named in traces/
    ConfigKey.TRACING_FILE_NAME_FORMAT.value: None,  # default traces_{timestamp}.{extension}
    ConfigKey.TRACING_FILE_BUFFER_SIZE.value: 10,
    ConfigKey.TRACING_FILE_PREFIX.value: None,
}

_options: dict[str, Any] = dict(_DEFAULTS)


def _normalize_key(key: str | Enum) -> str:
    if isinstance(key, Enum):
        return str(key.value)
    if not isinstance(key, str):
        raise TypeError("Option key must be str or Enum")
    return key


def set_option(key: str | Enum, value: Any) -> None:
    """Set a configuration option.

    Args:
        key: Option key as str or Enum
        value: Option value
    """
    k = _normalize_key(key)
    if k not in _DEFAULTS:
        raise KeyError(f"Unknown option: {k}")

    # Basic validation for known keys
    if k == ConfigKey.TRACING_BACKEND.value:
        if value not in ("file", "memory"):
            raise ValueError("tracing.backend must be 'file' or 'memory'")
    elif k == ConfigKey.TRACING_FILE_BUFFER_SIZE.value:
        if value is not None:
            if not isinstance(value, int) or value <= 0:
                raise ValueError("tracing.file.buffer_size must be a positive int")
    elif k == ConfigKey.TRACING_FILE_PATH.value:
        if value is not None and not isinstance(value, (str, Path)):
            raise ValueError("tracing.file.path must be a str, Path, or None")
    elif k == ConfigKey.TRACING_FILE_PREFIX.value:
        if value is not None and not isinstance(value, (str, Path)):
            raise ValueError("tracing.file.prefix must be a str, Path, or None")

    _options[k] = value


def get_option(key: str | Enum) -> Any:
    k = _normalize_key(key)
    if k not in _DEFAULTS:
        raise KeyError(f"Unknown option: {k}")
    return _options[k]


def reset_option(key: str | Enum | None = None) -> None:
    """Reset one or all options.

    Args:
        key: specific key to reset, or None to reset all
    """
    if key is None:
        _options.clear()
        _options.update(_DEFAULTS)
        return
    k = _normalize_key(key)
    if k not in _DEFAULTS:
        raise KeyError(f"Unknown option: {k}")
    _options[k] = _DEFAULTS[k]


@contextmanager
def option_context(*pairs: tuple[str | Enum, Any]) -> Iterator[None]:
    """Temporarily set options within a context.

    Example:
        with option_context((ConfigKey.TRACING_BACKEND, "memory")):
            ...
    """
    # Save originals
    originals: list[tuple[str, Any]] = []
    try:
        for key, value in pairs:
            k = _normalize_key(key)
            originals.append((k, _options[k]))
            set_option(k, value)
        yield
    finally:
        for k, v in originals:
            _options[k] = v


def configure_backend() -> Backend:
    """Create a Tracer from current options (no global state)."""
    backend_kind: str = get_option(ConfigKey.TRACING_BACKEND)
    backend: Backend
    if backend_kind == "memory":
        backend = InMemoryBackend()
    else:
        filepath = get_option(ConfigKey.TRACING_FILE_PATH)
        name_format = get_option(ConfigKey.TRACING_FILE_NAME_FORMAT)
        buffer_size = get_option(ConfigKey.TRACING_FILE_BUFFER_SIZE)
        prefix = get_option(ConfigKey.TRACING_FILE_PREFIX)
        backend = FileBackend(
            filepath=Path(filepath) if isinstance(filepath, str) else filepath,
            name_format=name_format,
            buffer_size=buffer_size,
            prefix=str(prefix) if prefix is not None else None,
        )
    return backend
