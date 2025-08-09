"""
Backend implementations for storing trace data.
"""

import json
import os
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

from sybil_scope.core import TraceEvent


class Backend(ABC):
    """Abstract base class for trace storage backends."""

    @abstractmethod
    def save(self, event: TraceEvent):
        """Save a trace event."""
        pass

    @abstractmethod
    def flush(self):
        """Flush any buffered events."""
        pass

    @abstractmethod
    def load(self) -> list[TraceEvent]:
        """Load all trace events."""
        pass


class FileBackend(Backend):
    """File-based backend that stores traces in JSONL format.

    By default, it writes to a 'traces/' directory in the current working
    directory and generates informative filenames including timestamp and PID.
    """

    def __init__(
        self,
        filepath: Path | None = None,
        name_format: str | None = None,
        buffer_size: int | None = None,
        prefix: str | None = None,
    ):
        """Initialize file backend.

        Args:
            filepath: Path to JSONL file. If not provided, defaults to
                'traces/traces_{YYYYMMDD}_{HHMMSS}_{PID}.jsonl'.
            name_format: Filename pattern. Defaults to "traces_{timestamp}.{extension}".
                Available tokens:
                - {timestamp}: Creation timestamp
                - {extension}: File extension (e.g., "jsonl")
                - {pid}: Current process ID
                - {random}: Random hex for uniqueness
                - {prefix}: Optional user-defined prefix (sanitized for filenames)
            buffer_size: Number of events to buffer before flush (default 10)
            prefix: Optional string used in filename generation. When provided and
                filepath is not set, the default pattern becomes
                "{prefix}_traces_{timestamp}.{extension}".
        """
        if filepath is None:
            if name_format is None:
                # If a prefix is provided, incorporate it in the default pattern
                name_format = (
                    "{prefix}_traces_{timestamp}.{extension}"
                    if prefix
                    else "traces_{timestamp}.{extension}"
                )
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_dir = Path("traces")
            safe_prefix = None
            if prefix:
                # Sanitize prefix for filenames: keep alnum, dash, underscore
                safe_prefix = "".join(
                    ch if (ch.isalnum() or ch in ("-", "_")) else "-"
                    for ch in str(prefix)
                )
            filepath = default_dir / name_format.format(
                timestamp=timestamp,
                extension="jsonl",
                pid=os.getpid(),
                random=uuid.uuid4().hex,
                prefix=safe_prefix or "",
            )

        self.filepath = Path(filepath)

        # Ensure the parent directory exists (create if needed)
        parent = self.filepath.parent
        if str(parent) != "" and not parent.exists():
            parent.mkdir(parents=True, exist_ok=True)

        self._buffer: list[TraceEvent] = []
        # Flush every N events (default 10)
        self._buffer_size = buffer_size or 10

    def save(self, event: TraceEvent):
        """Save a trace event to the buffer."""
        self._buffer.append(event)

        if len(self._buffer) >= self._buffer_size:
            self.flush()

    def flush(self):
        """Write buffered events to file."""
        if not self._buffer:
            return

        # Re-ensure directory exists in case of path changes
        parent = self.filepath.parent
        if str(parent) != "" and not parent.exists():
            parent.mkdir(parents=True, exist_ok=True)

        with open(self.filepath, "a", encoding="utf-8") as f:
            for event in self._buffer:
                f.write(event.model_dump_json() + "\n")

        self._buffer.clear()

    def load(self) -> list[TraceEvent]:
        """Load all trace events from file."""
        if not self.filepath.exists():
            return []

        events = []
        with open(self.filepath, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    event_data = json.loads(line)
                    events.append(TraceEvent(**event_data))

        return events


class InMemoryBackend(Backend):
    """In-memory backend for testing and development."""

    def __init__(self):
        self.events: list[TraceEvent] = []

    def save(self, event: TraceEvent):
        """Save a trace event to memory."""
        self.events.append(event)

    def flush(self):
        """No-op for in-memory backend."""
        pass

    def load(self) -> list[TraceEvent]:
        """Return all stored events."""
        return self.events.copy()
