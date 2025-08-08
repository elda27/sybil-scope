"""
Tests for backend implementations.
"""

from pathlib import Path
import tempfile
import json

from sybil_scope.core import TraceEvent, TraceType, ActionType
from sybil_scope.backend import FileBackend, InMemoryBackend


class TestInMemoryBackend:
    def test_save_and_load(self):
        backend = InMemoryBackend()

        # Create events
        event1 = TraceEvent(type=TraceType.USER, action=ActionType.INPUT)
        event2 = TraceEvent(type=TraceType.AGENT, action=ActionType.START)

        # Save events
        backend.save(event1)
        backend.save(event2)

        # Load events
        events = backend.load()
        assert len(events) == 2
        assert events[0].id == event1.id
        assert events[1].id == event2.id

    def test_flush_noop(self):
        backend = InMemoryBackend()
        backend.save(TraceEvent(type=TraceType.USER, action=ActionType.INPUT))

        # Flush should not affect in-memory storage
        backend.flush()
        assert len(backend.events) == 1

    def test_load_returns_copy(self):
        backend = InMemoryBackend()
        event = TraceEvent(type=TraceType.USER, action=ActionType.INPUT)
        backend.save(event)

        # Load should return a copy
        events1 = backend.load()
        events2 = backend.load()

        assert events1 is not events2
        assert len(events1) == len(events2) == 1


class TestFileBackend:
    def test_save_and_flush(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".jsonl") as f:
            filepath = Path(f.name)

        try:
            backend = FileBackend(filepath=filepath)

            # Create events
            events = []
            for i in range(15):  # More than buffer size
                event = TraceEvent(
                    type=TraceType.USER, action=ActionType.INPUT, details={"index": i}
                )
                events.append(event)
                backend.save(event)

            # Should have auto-flushed
            assert len(backend._buffer) < 10

            # Manual flush
            backend.flush()
            assert len(backend._buffer) == 0

            # Verify file contents
            with open(filepath, "r") as f:
                lines = f.readlines()
                assert len(lines) == 15

                # Check first event
                first_event_data = json.loads(lines[0])
                assert first_event_data["type"] == "user"
                assert first_event_data["details"]["index"] == 0

        finally:
            filepath.unlink(missing_ok=True)

    def test_load_from_file(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".jsonl") as f:
            filepath = Path(f.name)

        try:
            # Write events
            backend = FileBackend(filepath=filepath)
            events = []
            for i in range(5):
                event = TraceEvent(
                    type=TraceType.AGENT, action=ActionType.PROCESS, details={"step": i}
                )
                events.append(event)
                backend.save(event)
            backend.flush()

            # Load events
            loaded_events = backend.load()
            assert len(loaded_events) == 5

            for i, event in enumerate(loaded_events):
                assert event.type == TraceType.AGENT
                assert event.action == ActionType.PROCESS
                assert event.details["step"] == i

        finally:
            filepath.unlink(missing_ok=True)

    def test_load_empty_file(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".jsonl") as f:
            filepath = Path(f.name)

        try:
            backend = FileBackend(filepath=filepath)
            events = backend.load()
            assert events == []
        finally:
            filepath.unlink(missing_ok=True)

    def test_load_nonexistent_file(self):
        backend = FileBackend(filepath=Path("/tmp/nonexistent_file.jsonl"))
        events = backend.load()
        assert events == []

    def test_default_filepath(self):
        backend = FileBackend()
        assert backend.filepath.suffix == ".jsonl"
        assert "traces_" in str(backend.filepath)

    def test_append_mode(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".jsonl") as f:
            filepath = Path(f.name)

        try:
            # First backend instance
            backend1 = FileBackend(filepath=filepath)
            backend1.save(TraceEvent(type=TraceType.USER, action=ActionType.INPUT))
            backend1.flush()

            # Second backend instance (should append)
            backend2 = FileBackend(filepath=filepath)
            backend2.save(TraceEvent(type=TraceType.AGENT, action=ActionType.START))
            backend2.flush()

            # Load all events
            events = backend2.load()
            assert len(events) == 2
            assert events[0].type == TraceType.USER
            assert events[1].type == TraceType.AGENT

        finally:
            filepath.unlink(missing_ok=True)
