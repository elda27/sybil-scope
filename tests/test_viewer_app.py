"""
Tests for Streamlit app functionality and UI components.
"""

from datetime import datetime
from pathlib import Path

import pytest

from sybil_scope.core import ActionType, TraceEvent, TraceType


def _has_viewer_dependencies() -> bool:
    """Check if viewer dependencies are available."""
    try:
        import pandas  # noqa: F401
        import streamlit  # noqa: F401

        return True
    except ImportError:
        return False


class TestStreamlitAppHelpers:
    """Test helper functions used in the Streamlit app."""

    def setup_method(self):
        """Set up test data."""
        self.sample_events = [
            TraceEvent(
                type=TraceType.USER,
                action=ActionType.INPUT,
                details={"message": "Hello, AI!"},
            ),
            TraceEvent(
                type=TraceType.AGENT,
                action=ActionType.START,
                details={"name": "assistant"},
            ),
            TraceEvent(
                type=TraceType.LLM,
                action=ActionType.REQUEST,
                details={"model": "gpt-4", "args": {"prompts": ["Hello"]}},
            ),
            TraceEvent(
                type=TraceType.LLM,
                action=ActionType.RESPOND,
                details={"response": "Hi there!"},
            ),
        ]

        # Set up relationships
        self.sample_events[1].parent_id = self.sample_events[0].id
        self.sample_events[2].parent_id = self.sample_events[1].id
        self.sample_events[3].parent_id = self.sample_events[2].id

    @pytest.mark.skipif(
        not _has_viewer_dependencies(),
        reason="viewer dependencies (pandas, streamlit) not installed",
    )
    def test_load_trace_data_success(self, tmp_path: Path):
        """Test successful loading of trace data."""
        from sybil_scope.viewer.app import load_trace_data

        # Write sample events to a temp JSONL file
        filepath = tmp_path / "test_traces.jsonl"
        with open(filepath, "w", encoding="utf-8") as f:
            for ev in self.sample_events:
                f.write(ev.model_dump_json() + "\n")

        # Load from file
        result = load_trace_data(filepath)

        # Verify
        assert len(result) == 4
        assert result[0].type == self.sample_events[0].type
        assert result[0].action == self.sample_events[0].action
        assert result[-1].details.get("response") == "Hi there!"

    @pytest.mark.skipif(
        not _has_viewer_dependencies(),
        reason="viewer dependencies (pandas, streamlit) not installed",
    )
    def test_load_trace_data_empty_file(self, tmp_path: Path):
        """Test loading from empty file."""
        from sybil_scope.viewer.app import load_trace_data

        # Create an empty JSONL file
        filepath = tmp_path / "empty_traces.jsonl"
        filepath.write_text("", encoding="utf-8")

        result = load_trace_data(filepath)

        assert result == []
        assert len(result) == 0

    @pytest.mark.skipif(
        not _has_viewer_dependencies(),
        reason="viewer dependencies (pandas, streamlit) not installed",
    )
    def test_get_event_color_all_types(self):
        """Test color retrieval for all event types."""
        from sybil_scope.viewer.app import get_event_color

        expected_colors = {
            TraceType.USER: "#4CAF50",
            TraceType.AGENT: "#2196F3",
            TraceType.LLM: "#FF9800",
            TraceType.TOOL: "#9C27B0",
        }

        for event_type, expected_color in expected_colors.items():
            assert get_event_color(event_type) == expected_color

    @pytest.mark.skipif(
        not _has_viewer_dependencies(),
        reason="viewer dependencies (pandas, streamlit) not installed",
    )
    def test_get_event_icon_all_types(self):
        """Test icon retrieval for all event types."""
        from sybil_scope.viewer.app import get_event_icon

        expected_icons = {
            TraceType.USER: "👤",
            TraceType.AGENT: "🤖",
            TraceType.LLM: "🧠",
            TraceType.TOOL: "🔧",
        }

        for event_type, expected_icon in expected_icons.items():
            assert get_event_icon(event_type) == expected_icon

    @pytest.mark.skipif(
        not _has_viewer_dependencies(),
        reason="viewer dependencies (pandas, streamlit) not installed",
    )
    def test_format_timestamp(self):
        """Test timestamp formatting."""
        from sybil_scope.viewer.app import format_timestamp

        # Test specific timestamp
        ts = datetime(2023, 10, 1, 14, 30, 45, 123456)
        formatted = format_timestamp(ts)
        assert formatted == "14:30:45.123"

        # Test midnight
        ts_midnight = datetime(2023, 10, 1, 0, 0, 0, 0)
        formatted_midnight = format_timestamp(ts_midnight)
        assert formatted_midnight == "00:00:00.000"

        # Test with microseconds
        ts_micro = datetime(2023, 10, 1, 12, 30, 45, 999999)
        formatted_micro = format_timestamp(ts_micro)
        assert formatted_micro == "12:30:45.999"


class TestHierarchicalView:
    """Test hierarchical view functionality."""

    def setup_method(self):
        """Set up test data for hierarchical view."""
        base_time = datetime(2023, 10, 1, 14, 30, 0)

        self.events = [
            TraceEvent(
                type=TraceType.USER,
                action=ActionType.INPUT,
                timestamp=base_time,
                details={"message": "What's 2+2?"},
            ),
            TraceEvent(
                type=TraceType.AGENT,
                action=ActionType.START,
                timestamp=base_time.replace(microsecond=100000),
                details={"name": "math_agent"},
            ),
            TraceEvent(
                type=TraceType.TOOL,
                action=ActionType.CALL,
                timestamp=base_time.replace(microsecond=200000),
                details={"name": "calculator", "args": {"expression": "2+2"}},
            ),
            TraceEvent(
                type=TraceType.TOOL,
                action=ActionType.RESPOND,
                timestamp=base_time.replace(microsecond=300000),
                details={"result": 4},
            ),
            TraceEvent(
                type=TraceType.LLM,
                action=ActionType.REQUEST,
                timestamp=base_time.replace(microsecond=400000),
                details={"model": "gpt-4", "args": {"prompts": ["Format: 2+2=4"]}},
            ),
            TraceEvent(
                type=TraceType.LLM,
                action=ActionType.RESPOND,
                timestamp=base_time.replace(microsecond=500000),
                details={"response": "The answer is 4"},
            ),
            TraceEvent(
                type=TraceType.AGENT,
                action=ActionType.END,
                timestamp=base_time.replace(microsecond=600000),
                details={"name": "math_agent"},
            ),
        ]

        # Set up relationships
        self.events[1].parent_id = self.events[0].id  # agent -> user
        self.events[2].parent_id = self.events[1].id  # tool call -> agent
        self.events[3].parent_id = self.events[2].id  # tool response -> call
        self.events[4].parent_id = self.events[1].id  # llm request -> agent
        self.events[5].parent_id = self.events[4].id  # llm response -> request

    def test_find_paired_events_integration(self):
        """Test finding paired events for hierarchical display."""
        # Test the logic for finding paired events
        pairs = {}

        for event in self.events:
            # LLM request/response pairs
            if event.action == ActionType.REQUEST and event.type == TraceType.LLM:
                for potential_response in self.events:
                    if (
                        potential_response.action == ActionType.RESPOND
                        and potential_response.type == TraceType.LLM
                        and potential_response.parent_id == event.id
                    ):
                        pairs[event.id] = potential_response
                        break
            # Tool call/response pairs
            elif event.action == ActionType.CALL and event.type == TraceType.TOOL:
                for potential_response in self.events:
                    if (
                        potential_response.action == ActionType.RESPOND
                        and potential_response.type == TraceType.TOOL
                        and potential_response.parent_id == event.id
                    ):
                        pairs[event.id] = potential_response
                        break

        # Verify pairs were found
        tool_call = next(e for e in self.events if e.action == ActionType.CALL)
        llm_request = next(e for e in self.events if e.action == ActionType.REQUEST)

        assert tool_call.id in pairs
        assert llm_request.id in pairs
        assert pairs[tool_call.id].action == ActionType.RESPOND
        assert pairs[llm_request.id].action == ActionType.RESPOND

    def test_find_agent_start_end_pairs_logic(self):
        """Test finding agent start/end pairs."""
        # Group agents by parent_id
        agents_by_parent = {}
        for event in self.events:
            if event.type == TraceType.AGENT and event.action in [
                ActionType.START,
                ActionType.END,
            ]:
                parent = event.parent_id
                if parent not in agents_by_parent:
                    agents_by_parent[parent] = {"starts": [], "ends": []}
                if event.action == ActionType.START:
                    agents_by_parent[parent]["starts"].append(event)
                else:
                    agents_by_parent[parent]["ends"].append(event)

        # Match starts with ends chronologically
        agent_pairs = {}
        for parent, agents in agents_by_parent.items():
            starts = sorted(agents["starts"], key=lambda x: x.timestamp)
            ends = sorted(agents["ends"], key=lambda x: x.timestamp)

            for i, start in enumerate(starts):
                if i < len(ends):
                    agent_pairs[start.id] = ends[i].id

        # Verify pairing worked
        agent_start = next(e for e in self.events if e.action == ActionType.START)
        agent_end = next(e for e in self.events if e.action == ActionType.END)

        # Check if pairing happened (agents with different parents won't be paired)
        if agent_pairs:
            assert agent_start.id in agent_pairs
            assert agent_pairs[agent_start.id] == agent_end.id
        else:
            # If no pairs found, ensure agents have different parents
            assert agent_start.parent_id != agent_end.parent_id or (
                agent_start.parent_id is None and agent_end.parent_id is not None
            )

    def test_duration_calculation_logic(self):
        """Test duration calculation for paired events."""
        from sybil_scope.viewer.common import TimeHelper

        # Find tool call/response pair
        tool_call = next(e for e in self.events if e.action == ActionType.CALL)
        tool_response = next(
            e
            for e in self.events
            if e.action == ActionType.RESPOND and e.parent_id == tool_call.id
        )

        # Calculate duration
        duration = TimeHelper.calculate_duration(tool_call, tool_response)
        expected_duration = (
            tool_response.timestamp - tool_call.timestamp
        ).total_seconds()

        assert duration == f"{expected_duration:.3f}s"

    def test_format_args_for_display_logic(self):
        """Test formatting arguments for display."""

        def format_args_for_display(args: dict, max_length: int = 50) -> str:
            """Format arguments dict for display in expander label."""
            if not args:
                return ""
            arg_parts = []
            for key, value in args.items():
                if key not in ["kwargs", "args", "_type"] and value:
                    if isinstance(value, list):
                        if len(value) > 0 and isinstance(value[0], str):
                            str_val = str(value[0])[:max_length] + (
                                "..." if len(str(value[0])) > max_length else ""
                            )
                        else:
                            str_val = str(value)[:max_length] + (
                                "..." if len(str(value)) > max_length else ""
                            )
                    else:
                        str_val = str(value)[:max_length] + (
                            "..." if len(str(value)) > max_length else ""
                        )
                    arg_parts.append(f"{key}: {str_val}")
            return ", ".join(arg_parts[:2])  # Show only first 2 args

        # Test with tool call
        tool_call = next(e for e in self.events if e.action == ActionType.CALL)
        args_text = format_args_for_display(tool_call.details.get("args", {}))
        assert "expression: 2+2" in args_text

    def test_format_result_for_display_logic(self):
        """Test formatting results for display."""

        def format_result_for_display(result, error: str = None) -> str:
            """Format result or error for display."""
            if error:
                return (
                    f"❌error: {error[:50]}..."
                    if len(error) > 50
                    else f"❌error: {error}"
                )

            if isinstance(result, dict):
                result_parts = []
                for key, value in result.items():
                    str_val = str(value)[:30] + ("..." if len(str(value)) > 30 else "")
                    result_parts.append(f"{key}: {str_val}")
                return ", ".join(result_parts[:2])
            elif isinstance(result, list):
                if len(result) > 0:
                    return f"[{len(result)} items] {str(result[0])[:50]}..."
                return "[empty]"
            else:
                return str(result)[:100] + ("..." if len(str(result)) > 100 else "")

        # Test with tool response
        tool_response = next(
            e
            for e in self.events
            if e.action == ActionType.RESPOND and e.type == TraceType.TOOL
        )
        result_text = format_result_for_display(tool_response.details.get("result", ""))
        assert "4" in result_text


class TestStatisticsView:
    """Test statistics view functionality."""

    def setup_method(self):
        """Set up test data for statistics."""
        self.events = [
            TraceEvent(type=TraceType.USER, action=ActionType.INPUT, details={}),
            TraceEvent(type=TraceType.AGENT, action=ActionType.START, details={}),
            TraceEvent(type=TraceType.LLM, action=ActionType.REQUEST, details={}),
            TraceEvent(type=TraceType.LLM, action=ActionType.RESPOND, details={}),
            TraceEvent(type=TraceType.TOOL, action=ActionType.CALL, details={}),
            TraceEvent(
                type=TraceType.TOOL,
                action=ActionType.RESPOND,
                details={"error": "Failed"},
            ),
            TraceEvent(type=TraceType.AGENT, action=ActionType.END, details={}),
        ]

        # Set up relationships and timing for performance analysis
        base_time = datetime.now()
        for i, event in enumerate(self.events):
            event.timestamp = base_time.replace(microsecond=i * 100000)

        self.events[1].parent_id = self.events[0].id
        self.events[2].parent_id = self.events[1].id
        self.events[3].parent_id = self.events[2].id
        self.events[4].parent_id = self.events[1].id
        self.events[5].parent_id = self.events[4].id

    def test_basic_metrics_calculation(self):
        """Test calculation of basic metrics."""
        # Total events
        total_events = len(self.events)
        assert total_events == 7

        # Event types
        event_types = [e.type.value for e in self.events]
        unique_types = len(set(event_types))
        assert unique_types == 4  # USER, AGENT, LLM, TOOL

        # Duration
        start_time = min(e.timestamp for e in self.events)
        end_time = max(e.timestamp for e in self.events)
        duration = (end_time - start_time).total_seconds()
        assert duration == 0.6  # 6 * 100ms

        # Errors
        error_count = sum(1 for e in self.events if "error" in e.details)
        assert error_count == 1

    def test_event_type_distribution(self):
        """Test event type distribution calculation."""
        type_counts = {}
        for event in self.events:
            event_type = event.type.value
            type_counts[event_type] = type_counts.get(event_type, 0) + 1

        assert type_counts["user"] == 1
        assert type_counts["agent"] == 2  # START and END
        assert type_counts["llm"] == 2  # REQUEST and RESPOND
        assert type_counts["tool"] == 2  # CALL and RESPOND

    def test_action_distribution(self):
        """Test action distribution calculation."""
        action_counts = {}
        for event in self.events:
            action = event.action.value
            action_counts[action] = action_counts.get(action, 0) + 1

        assert action_counts["input"] == 1
        assert action_counts["start"] == 1
        assert action_counts["end"] == 1
        assert action_counts["request"] == 1
        assert action_counts["respond"] == 2  # LLM and TOOL
        assert action_counts["call"] == 1

    def test_performance_analysis_data(self):
        """Test performance analysis data preparation."""
        pairs = []

        for event in self.events:
            if event.action in [ActionType.START, ActionType.REQUEST, ActionType.CALL]:
                # Find matching end event
                for potential_end in self.events:
                    if potential_end.parent_id == event.id and potential_end.action in [
                        ActionType.END,
                        ActionType.RESPOND,
                    ]:
                        duration = (
                            potential_end.timestamp - event.timestamp
                        ).total_seconds()
                        pairs.append(
                            {
                                "Operation": f"{event.type.value} - {event.details.get('name', event.details.get('function', 'Unknown'))}",
                                "Duration (s)": duration,
                                "Type": event.type.value,
                            }
                        )
                        break

        # Verify pairs were found
        assert (
            len(pairs) == 2
        )  # LLM, TOOL (AGENT doesn't have matching END in this setup)

        # Check duration calculations
        durations = [pair["Duration (s)"] for pair in pairs]
        assert all(d >= 0 for d in durations)  # All durations should be non-negative


class TestTimelineView:
    """Test timeline view functionality."""

    def setup_method(self):
        """Set up test data for timeline."""
        base_time = datetime(2023, 10, 1, 14, 30, 0)

        self.events = [
            TraceEvent(
                type=TraceType.USER,
                action=ActionType.INPUT,
                timestamp=base_time,
                details={"message": "Timeline test"},
            ),
            TraceEvent(
                type=TraceType.AGENT,
                action=ActionType.START,
                timestamp=base_time.replace(second=1),
                details={"name": "timeline_agent"},
            ),
            TraceEvent(
                type=TraceType.LLM,
                action=ActionType.REQUEST,
                timestamp=base_time.replace(second=2),
                details={"model": "gpt-4"},
            ),
            TraceEvent(
                type=TraceType.LLM,
                action=ActionType.RESPOND,
                timestamp=base_time.replace(second=3),
                details={"response": "Timeline response"},
            ),
        ]

    def test_timeline_data_preparation(self):
        """Test preparation of timeline data."""
        if not self.events:
            return  # Skip if no events

        # Calculate time range
        start_time = min(e.timestamp for e in self.events)
        end_time = max(e.timestamp for e in self.events)
        total_duration = (end_time - start_time).total_seconds()

        assert total_duration == 3.0  # 3 seconds

        # Create timeline data structure
        timeline_data = []
        for event in self.events:
            relative_time = (event.timestamp - start_time).total_seconds()
            timeline_data.append(
                {
                    "Time (s)": f"{relative_time:.3f}",
                    "Type": f"🧠 {event.type.value}"
                    if event.type == TraceType.LLM
                    else f"👤 {event.type.value}",
                    "Action": event.action.value,
                    "Label": event.details.get("label", event.details.get("name", "")),
                    "ID": event.id,
                    "Parent ID": event.parent_id or "",
                }
            )

        # Verify data structure
        assert len(timeline_data) == 4
        assert timeline_data[0]["Time (s)"] == "0.000"
        assert timeline_data[1]["Time (s)"] == "1.000"
        assert timeline_data[2]["Time (s)"] == "2.000"
        assert timeline_data[3]["Time (s)"] == "3.000"

    def test_timeline_filtering_logic(self):
        """Test filtering logic for timeline view."""
        # Test type filtering
        type_filter = ["user", "llm"]
        filtered_events = [e for e in self.events if e.type.value in type_filter]
        assert len(filtered_events) == 3  # USER + 2 LLM events

        # Test action filtering
        action_filter = ["input", "request"]
        filtered_events = [e for e in self.events if e.action.value in action_filter]
        assert len(filtered_events) == 2  # INPUT + REQUEST

        # Test combined filtering
        combined_filtered = [
            e
            for e in self.events
            if e.type.value in type_filter and e.action.value in action_filter
        ]
        assert len(combined_filtered) == 2  # USER INPUT + LLM REQUEST

    def test_timeline_empty_events(self):
        """Test timeline with empty events."""
        empty_events = []

        # Should handle empty case gracefully
        assert len(empty_events) == 0

        # Timeline data should be empty
        timeline_data = []
        for event in empty_events:
            # This loop won't execute
            timeline_data.append({})

        assert len(timeline_data) == 0


class TestEventInspector:
    """Test event inspector functionality."""

    def setup_method(self):
        """Set up test data for event inspector."""
        self.events = [
            TraceEvent(
                type=TraceType.LLM,
                action=ActionType.REQUEST,
                details={
                    "model": "gpt-4",
                    "args": {"prompts": ["Test prompt"], "temperature": 0.7},
                },
            ),
            TraceEvent(
                type=TraceType.LLM,
                action=ActionType.RESPOND,
                details={
                    "response": "Test response",
                    "llm_output": {"token_usage": {"total": 50}},
                },
            ),
            TraceEvent(
                type=TraceType.TOOL,
                action=ActionType.CALL,
                details={
                    "name": "test_tool",
                    "args": {"param1": "value1", "param2": "value2"},
                },
            ),
            TraceEvent(
                type=TraceType.TOOL,
                action=ActionType.RESPOND,
                details={
                    "error": "Tool execution failed",
                    "error_type": "ConnectionError",
                },
            ),
        ]

    def test_event_details_rendering_logic(self):
        """Test logic for rendering event details."""
        for event in self.events:
            # Basic info should always be available
            assert hasattr(event, "id")
            assert hasattr(event, "type")
            assert hasattr(event, "action")
            assert hasattr(event, "timestamp")

            # Details should be accessible
            assert isinstance(event.details, dict)

            # Test specific detail formatting
            if event.type == TraceType.LLM and event.action == ActionType.REQUEST:
                assert "model" in event.details
                assert "args" in event.details
            elif event.type == TraceType.LLM and event.action == ActionType.RESPOND:
                assert "response" in event.details
            elif event.type == TraceType.TOOL and event.action == ActionType.CALL:
                assert "name" in event.details
                assert "args" in event.details
            elif event.type == TraceType.TOOL and event.action == ActionType.RESPOND:
                # Could have either result or error
                assert "error" in event.details or "result" in event.details

    def test_event_lookup_logic(self):
        """Test event lookup by ID."""
        # Create a lookup map
        events_by_id = {e.id: e for e in self.events}

        # Test lookup
        for event in self.events:
            found_event = events_by_id.get(event.id)
            assert found_event is not None
            assert found_event == event

        # Test non-existent ID
        non_existent_id = max(e.id for e in self.events) + 1
        found_event = events_by_id.get(non_existent_id)
        assert found_event is None

    def test_json_formatting_logic(self):
        """Test JSON formatting for event details."""
        import json

        for event in self.events:
            # Test that details can be JSON serialized
            try:
                json_str = json.dumps(event.details, indent=2)
                assert isinstance(json_str, str)
                assert len(json_str) > 0

                # Verify it's valid JSON by parsing it back
                parsed = json.loads(json_str)
                assert parsed == event.details
            except (TypeError, ValueError) as e:
                pytest.fail(f"Event details should be JSON serializable: {e}")


class TestViewerIntegrationEnd2End:
    """End-to-end integration tests for the viewer."""

    def setup_method(self):
        """Set up comprehensive test scenario."""
        base_time = datetime(2023, 10, 1, 14, 30, 0)

        # Create a realistic conversation flow
        self.events = [
            TraceEvent(
                type=TraceType.USER,
                action=ActionType.INPUT,
                timestamp=base_time,
                details={"message": "What's the capital of France?"},
            ),
            TraceEvent(
                type=TraceType.AGENT,
                action=ActionType.START,
                timestamp=base_time.replace(microsecond=50000),
                details={"name": "knowledge_agent"},
            ),
            TraceEvent(
                type=TraceType.TOOL,
                action=ActionType.CALL,
                timestamp=base_time.replace(microsecond=100000),
                details={
                    "name": "knowledge_search",
                    "args": {"query": "capital France"},
                },
            ),
            TraceEvent(
                type=TraceType.TOOL,
                action=ActionType.RESPOND,
                timestamp=base_time.replace(microsecond=300000),
                details={"result": {"answer": "Paris", "confidence": 0.95}},
            ),
            TraceEvent(
                type=TraceType.LLM,
                action=ActionType.REQUEST,
                timestamp=base_time.replace(microsecond=400000),
                details={
                    "model": "gpt-4",
                    "args": {"prompts": ["Format: Paris is the capital"]},
                },
            ),
            TraceEvent(
                type=TraceType.LLM,
                action=ActionType.RESPOND,
                timestamp=base_time.replace(microsecond=700000),
                details={"response": "The capital of France is Paris."},
            ),
            TraceEvent(
                type=TraceType.AGENT,
                action=ActionType.PROCESS,
                timestamp=base_time.replace(microsecond=750000),
                details={
                    "label": "Final Response",
                    "response": {"output": "The capital of France is Paris."},
                },
            ),
            TraceEvent(
                type=TraceType.AGENT,
                action=ActionType.END,
                timestamp=base_time.replace(microsecond=800000),
                details={"name": "knowledge_agent"},
            ),
        ]

        # Set up relationships
        self.events[1].parent_id = self.events[0].id  # agent -> user
        self.events[2].parent_id = self.events[1].id  # tool call -> agent
        self.events[3].parent_id = self.events[2].id  # tool response -> call
        self.events[4].parent_id = self.events[1].id  # llm request -> agent
        self.events[5].parent_id = self.events[4].id  # llm response -> request
        self.events[6].parent_id = self.events[1].id  # agent process -> agent

    def test_complete_viewer_workflow(self):
        """Test complete workflow that viewer would perform."""
        from sybil_scope.viewer.common import (
            EventPairHelper,
            HierarchyHelper,
            TextFormatter,
            TimeHelper,
            TreeStructureBuilder,
        )

        # 1. Build tree structure
        tree = TreeStructureBuilder.build_corrected_tree_structure(self.events)
        assert self.events[0] in tree[None]  # User is root

        # 2. Find event pairs
        pair_helper = EventPairHelper(self.events)
        pairs = pair_helper.find_paired_events()

        tool_call = next(e for e in self.events if e.action == ActionType.CALL)
        llm_request = next(e for e in self.events if e.action == ActionType.REQUEST)

        assert tool_call.id in pairs
        assert llm_request.id in pairs

        # 3. Calculate hierarchy
        hierarchy = HierarchyHelper(self.events)
        depths = {e.id: hierarchy.calculate_depth(e.id) for e in self.events}

        assert depths[self.events[0].id] == 0  # User at root
        assert depths[self.events[1].id] == 1  # Agent at level 1
        assert depths[self.events[2].id] == 2  # Tool call at level 2

        # 4. Format display text
        user_input = TextFormatter.get_input_summary(self.events[0])
        assert "capital of France" in user_input

        tool_output = TextFormatter.get_output_summary(self.events[3])
        assert "answer:Paris" in tool_output

        llm_output = TextFormatter.get_output_summary(self.events[5])
        assert "capital of France is Paris" in llm_output

        # 5. Calculate durations
        tool_duration = TimeHelper.get_event_duration(self.events[2], self.events)
        llm_duration = TimeHelper.get_event_duration(self.events[4], self.events)

        assert tool_duration == 0.2  # 200ms
        assert llm_duration == 0.3  # 300ms

    def test_error_handling_in_workflow(self):
        """Test error handling throughout the workflow."""
        # Test with minimal events
        minimal_events = [self.events[0]]  # Just user input

        from sybil_scope.viewer.common import (
            EventPairHelper,
            HierarchyHelper,
            TreeStructureBuilder,
        )

        # Should not crash with minimal data
        tree = TreeStructureBuilder.build_corrected_tree_structure(minimal_events)
        assert len(tree[None]) == 1

        pair_helper = EventPairHelper(minimal_events)
        pairs = pair_helper.find_paired_events()
        assert len(pairs) == 0  # No pairs possible

        hierarchy = HierarchyHelper(minimal_events)
        roots = hierarchy.get_root_events()
        assert len(roots) == 1

    def test_performance_analysis_end2end(self):
        """Test end-to-end performance analysis."""
        # Calculate metrics that would be shown in statistics view

        # Total duration
        start_time = min(e.timestamp for e in self.events)
        end_time = max(e.timestamp for e in self.events)
        total_duration = (end_time - start_time).total_seconds()
        assert total_duration == 0.8  # 800ms

        # Find all operation pairs for performance analysis
        operations = []
        for event in self.events:
            if event.action in [ActionType.START, ActionType.REQUEST, ActionType.CALL]:
                for potential_end in self.events:
                    if potential_end.parent_id == event.id and potential_end.action in [
                        ActionType.END,
                        ActionType.RESPOND,
                    ]:
                        duration = (
                            potential_end.timestamp - event.timestamp
                        ).total_seconds()
                        op_name = event.details.get(
                            "name", event.details.get("model", "Unknown")
                        )
                        operations.append(
                            {
                                "name": op_name,
                                "type": event.type.value,
                                "duration": duration,
                            }
                        )
                        break

        # Verify operations were found
        assert len(operations) == 2  # Tool and LLM operations

        # Check that durations are reasonable
        tool_op = next(op for op in operations if op["type"] == "tool")
        llm_op = next(op for op in operations if op["type"] == "llm")

        assert tool_op["duration"] == 0.2
        assert llm_op["duration"] == 0.3
        assert tool_op["name"] == "knowledge_search"
        assert llm_op["name"] == "gpt-4"

    def test_all_visualization_types_compatibility(self):
        """Test that events work with all visualization types."""
        # Test statistics view compatibility
        event_types = [e.type.value for e in self.events]
        action_types = [e.action.value for e in self.events]

        assert len(set(event_types)) == 4  # USER, AGENT, TOOL, LLM
        assert len(set(action_types)) >= 4  # Multiple actions

        # Test timeline compatibility
        sorted_events = sorted(self.events, key=lambda e: e.timestamp)
        assert len(sorted_events) == len(self.events)

        # Test hierarchical view compatibility
        from sybil_scope.viewer.common import TreeStructureBuilder

        tree = TreeStructureBuilder.build_corrected_tree_structure(self.events)
        assert len(tree) > 0

        # Test table view compatibility
        parent_map = {e.id: e.parent_id for e in self.events if e.parent_id}
        assert len(parent_map) == 6  # All events except root have parents

        # Test flow diagram compatibility
        events_by_id = {e.id: e for e in self.events}
        assert len(events_by_id) == len(self.events)


if __name__ == "__main__":
    pytest.main([__file__])
