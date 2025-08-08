"""
Backend implementations for storing trace data.
"""

import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

from .core import TraceEvent


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
    """File-based backend that stores traces in JSONL format."""

    def __init__(self, filepath: Path | None = None):
        """Initialize file backend.

        Args:
            filepath: Path to JSONL file. Defaults to traces_{timestamp}.jsonl
        """
        if filepath is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = Path(f"traces_{timestamp}.jsonl")

        self.filepath = Path(filepath)
        self._buffer: list[TraceEvent] = []
        self._buffer_size = 10  # Flush every 10 events

    def save(self, event: TraceEvent):
        """Save a trace event to the buffer."""
        self._buffer.append(event)

        if len(self._buffer) >= self._buffer_size:
            self.flush()

    def flush(self):
        """Write buffered events to file."""
        if not self._buffer:
            return

        with open(self.filepath, "a") as f:
            for event in self._buffer:
                f.write(event.model_dump_json() + "\n")

        self._buffer.clear()

    def load(self) -> list[TraceEvent]:
        """Load all trace events from file."""
        if not self.filepath.exists():
            return []

        events = []
        with open(self.filepath, "r") as f:
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
