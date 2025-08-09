"""
Tests for viewer functionality.
"""

from datetime import datetime
from pathlib import Path

import pytest

from sybil_scope.core import ActionType, TraceEvent, TraceType
from sybil_scope.viewer.common import (
    DEFAULT_COLOR_SCHEME,
    DEFAULT_ICON_SCHEME,
    VIZ_OPTIONS,
    EdgeHelper,
    EventPairHelper,
    EventStyleHelper,
    HierarchyHelper,
    TextFormatter,
    TimeHelper,
    TreeStructureBuilder,
)


def _has_viewer_dependencies() -> bool:
    """Check if viewer dependencies are available."""
    try:
        import pandas  # noqa: F401
        import streamlit  # noqa: F401

        return True
    except ImportError:
        return False


class TestEventPairHelper:
    """Test EventPairHelper functionality."""

    def test_find_paired_events_llm(self):
        """Test finding LLM request/response pairs."""
        request_event = TraceEvent(
            type=TraceType.LLM,
            action=ActionType.REQUEST,
            details={"model": "gpt-4", "prompt": "Test prompt"},
        )
        response_event = TraceEvent(
            type=TraceType.LLM,
            action=ActionType.RESPOND,
            parent_id=request_event.id,
            details={"response": "Test response"},
        )

        helper = EventPairHelper([request_event, response_event])
        pairs = helper.find_paired_events()

        assert request_event.id in pairs
        assert pairs[request_event.id] == response_event

    def test_find_paired_events_tool(self):
        """Test finding Tool call/response pairs."""
        call_event = TraceEvent(
            type=TraceType.TOOL,
            action=ActionType.CALL,
            details={"name": "test_tool", "args": {"param": "value"}},
        )
        response_event = TraceEvent(
            type=TraceType.TOOL,
            action=ActionType.RESPOND,
            parent_id=call_event.id,
            details={"result": "success"},
        )

        helper = EventPairHelper([call_event, response_event])
        pairs = helper.find_paired_events()

        assert call_event.id in pairs
        assert pairs[call_event.id] == response_event

    def test_find_agent_start_end_pairs(self):
        """Test finding Agent start/end pairs."""
        start_event = TraceEvent(
            type=TraceType.AGENT,
            action=ActionType.START,
            details={"name": "test_agent"},
        )
        end_event = TraceEvent(
            type=TraceType.AGENT,
            action=ActionType.END,
            parent_id=None,  # Same parent level
            details={"name": "test_agent"},
        )

        helper = EventPairHelper([start_event, end_event])
        pairs = helper.find_agent_start_end_pairs()

        assert start_event.id in pairs
        assert pairs[start_event.id] == end_event.id

    def test_find_paired_events_no_pairs(self):
        """Test when no pairs exist."""
        event1 = TraceEvent(
            type=TraceType.USER,
            action=ActionType.INPUT,
            details={"message": "Hello"},
        )
        event2 = TraceEvent(
            type=TraceType.AGENT,
            action=ActionType.PROCESS,
            details={"label": "Processing"},
        )

        helper = EventPairHelper([event1, event2])
        pairs = helper.find_paired_events()

        assert len(pairs) == 0

    def test_multiple_agent_pairs_chronological(self):
        """Test multiple agent start/end pairs are matched chronologically."""
        # Create timestamps to ensure chronological order
        base_time = datetime(2023, 10, 1, 14, 30, 0)

        start1 = TraceEvent(
            type=TraceType.AGENT,
            action=ActionType.START,
            details={"name": "agent1"},
            timestamp=base_time,
        )
        start2 = TraceEvent(
            type=TraceType.AGENT,
            action=ActionType.START,
            details={"name": "agent2"},
            timestamp=base_time.replace(microsecond=100000),
        )
        end1 = TraceEvent(
            type=TraceType.AGENT,
            action=ActionType.END,
            details={"name": "agent1"},
            timestamp=base_time.replace(microsecond=200000),
        )
        end2 = TraceEvent(
            type=TraceType.AGENT,
            action=ActionType.END,
            details={"name": "agent2"},
            timestamp=base_time.replace(microsecond=300000),
        )

        helper = EventPairHelper([start1, start2, end1, end2])
        pairs = helper.find_agent_start_end_pairs()

        assert start1.id in pairs
        assert start2.id in pairs
        # Verify pairing exists (IDs are random, but mapping should exist)
        assert len(pairs) == 2
        # First start should map to first end chronologically
        starts_by_time = [start1, start2]
        ends_by_time = [end1, end2]
        for i, start in enumerate(starts_by_time):
            assert pairs[start.id] == ends_by_time[i].id


class TestTreeStructureBuilder:
    """Test TreeStructureBuilder functionality."""

    def test_build_tree_structure_simple(self):
        """Test building simple tree structure."""
        parent = TraceEvent(
            type=TraceType.USER,
            action=ActionType.INPUT,
            details={"message": "Hello"},
        )
        child = TraceEvent(
            type=TraceType.AGENT,
            action=ActionType.START,
            parent_id=parent.id,
            details={"name": "agent"},
        )

        tree = TreeStructureBuilder.build_tree_structure([parent, child])

        assert None in tree  # Root level
        assert parent.id in tree  # Parent has children
        assert parent in tree[None]
        assert child in tree[parent.id]

    def test_build_tree_structure_empty(self):
        """Test building tree structure with empty events list."""
        tree = TreeStructureBuilder.build_tree_structure([])
        assert len(tree) == 0

    def test_build_corrected_tree_structure(self):
        """Test building corrected tree structure that handles agent pairs."""
        # Create agent start/end pair
        start = TraceEvent(
            type=TraceType.AGENT,
            action=ActionType.START,
            details={"name": "agent"},
        )
        process = TraceEvent(
            type=TraceType.AGENT,
            action=ActionType.PROCESS,
            parent_id=start.id,
            details={"label": "Processing"},
        )
        end = TraceEvent(
            type=TraceType.AGENT,
            action=ActionType.END,
            details={"name": "agent"},
        )

        tree = TreeStructureBuilder.build_corrected_tree_structure(
            [start, process, end]
        )

        # End event should be filtered out
        assert end not in tree[None]
        assert start in tree[None]
        assert process in tree[start.id]

    def test_build_tree_multiple_levels(self):
        """Test building tree with multiple levels."""
        root = TraceEvent(
            type=TraceType.USER,
            action=ActionType.INPUT,
            details={"message": "Hello"},
        )
        level1 = TraceEvent(
            type=TraceType.AGENT,
            action=ActionType.START,
            parent_id=root.id,
            details={"name": "agent"},
        )
        level2 = TraceEvent(
            type=TraceType.LLM,
            action=ActionType.REQUEST,
            parent_id=level1.id,
            details={"model": "gpt-4"},
        )

        tree = TreeStructureBuilder.build_tree_structure([root, level1, level2])

        assert len(tree[None]) == 1  # One root
        assert len(tree[root.id]) == 1  # One child of root
        assert len(tree[level1.id]) == 1  # One child of level1
        assert root in tree[None]
        assert level1 in tree[root.id]
        assert level2 in tree[level1.id]


class TestEventStyleHelper:
    """Test EventStyleHelper functionality."""

    def test_get_event_color(self):
        """Test getting event colors."""
        assert EventStyleHelper.get_event_color(TraceType.USER) == "#4CAF50"
        assert EventStyleHelper.get_event_color(TraceType.AGENT) == "#2196F3"
        assert EventStyleHelper.get_event_color(TraceType.LLM) == "#FF9800"
        assert EventStyleHelper.get_event_color(TraceType.TOOL) == "#9C27B0"

    def test_get_event_icon(self):
        """Test getting event icons."""
        assert EventStyleHelper.get_event_icon(TraceType.USER) == "👤"
        assert EventStyleHelper.get_event_icon(TraceType.AGENT) == "🤖"
        assert EventStyleHelper.get_event_icon(TraceType.LLM) == "🧠"
        assert EventStyleHelper.get_event_icon(TraceType.TOOL) == "🔧"

    def test_get_event_style(self):
        """Test getting comprehensive event style."""
        event = TraceEvent(
            type=TraceType.LLM,
            action=ActionType.REQUEST,
            details={"model": "gpt-4"},
        )

        style = EventStyleHelper.get_event_style(event)

        assert "color" in style
        assert "font" in style
        assert "shape" in style
        assert style["color"]["border"] == "#FF9800"  # LLM color
        assert style["shape"] == "circle"  # REQUEST action shape

    def test_get_event_style_all_types(self):
        """Test style generation for all event types."""
        for event_type in TraceType:
            event = TraceEvent(
                type=event_type,
                action=ActionType.START,
                details={},
            )
            style = EventStyleHelper.get_event_style(event)

            assert "color" in style
            assert "background" in style["color"]
            assert "border" in style["color"]
            assert "color" in style["font"]

    def test_get_event_style_all_actions(self):
        """Test style generation for all action types."""
        for action_type in ActionType:
            event = TraceEvent(
                type=TraceType.AGENT,
                action=action_type,
                details={},
            )
            style = EventStyleHelper.get_event_style(event)

            assert "shape" in style
            # Verify shape is one of the expected shapes
            expected_shapes = ["ellipse", "box", "diamond", "circle", "triangle"]
            assert style["shape"] in expected_shapes


class TestTimeHelper:
    """Test TimeHelper functionality."""

    def test_format_timestamp(self):
        """Test timestamp formatting."""
        ts = datetime(2023, 10, 1, 14, 30, 45, 123456)
        formatted = TimeHelper.format_timestamp(ts)

        assert formatted == "14:30:45.123"

    def test_calculate_duration_with_end_event(self):
        """Test duration calculation with end event."""
        start = datetime(2023, 10, 1, 14, 30, 45, 0)
        end = datetime(2023, 10, 1, 14, 30, 47, 500000)

        start_event = TraceEvent(
            type=TraceType.LLM,
            action=ActionType.REQUEST,
            timestamp=start,
            details={},
        )
        end_event = TraceEvent(
            type=TraceType.LLM,
            action=ActionType.RESPOND,
            timestamp=end,
            details={},
        )

        duration = TimeHelper.calculate_duration(start_event, end_event)
        assert duration == "2.500s"

    def test_calculate_duration_no_end_event(self):
        """Test duration calculation without end event."""
        start_event = TraceEvent(
            type=TraceType.AGENT,
            action=ActionType.START,
            details={},
        )

        duration = TimeHelper.calculate_duration(start_event)
        assert duration == "0.000s"

    def test_calculate_duration_with_agent_pairs(self):
        """Test duration calculation using agent pairs."""
        start_time = datetime(2023, 10, 1, 14, 30, 45, 0)
        end_time = datetime(2023, 10, 1, 14, 30, 47, 0)

        start_event = TraceEvent(
            type=TraceType.AGENT,
            action=ActionType.START,
            timestamp=start_time,
            details={},
        )
        end_event = TraceEvent(
            type=TraceType.AGENT,
            action=ActionType.END,
            timestamp=end_time,
            details={},
        )

        events = [start_event, end_event]
        agent_pairs = {start_event.id: end_event.id}

        duration = TimeHelper.calculate_duration(
            start_event, None, events, None, agent_pairs
        )
        assert duration == "2.000s"

    def test_get_event_duration(self):
        """Test getting event duration."""
        start_time = datetime(2023, 10, 1, 14, 30, 45, 0)
        end_time = datetime(2023, 10, 1, 14, 30, 47, 123000)

        start_event = TraceEvent(
            type=TraceType.LLM,
            action=ActionType.REQUEST,
            timestamp=start_time,
            details={},
        )
        end_event = TraceEvent(
            type=TraceType.LLM,
            action=ActionType.RESPOND,
            parent_id=start_event.id,
            timestamp=end_time,
            details={},
        )

        events = [start_event, end_event]
        duration = TimeHelper.get_event_duration(start_event, events)

        assert duration == 2.123

    def test_get_event_duration_no_matching_end(self):
        """Test getting event duration when no matching end event exists."""
        event = TraceEvent(
            type=TraceType.LLM,
            action=ActionType.REQUEST,
            details={},
        )

        duration = TimeHelper.get_event_duration(event, [event])
        assert duration is None


class TestTextFormatter:
    """Test TextFormatter functionality."""

    def test_truncate_text_short(self):
        """Test truncating text that's under the limit."""
        text = "Short text"
        result = TextFormatter.truncate_text(text, 50)
        assert result == "Short text"

    def test_truncate_text_long(self):
        """Test truncating text that exceeds the limit."""
        text = "This is a very long text that should be truncated"
        result = TextFormatter.truncate_text(text, 20)
        assert result == "This is a very long ..."

    def test_truncate_text_non_string(self):
        """Test truncating non-string input."""
        result = TextFormatter.truncate_text(12345, 10)
        assert result == "12345"

    def test_truncate_text_none(self):
        """Test truncating None input."""
        result = TextFormatter.truncate_text(None, 10)
        assert result == ""

    def test_format_args_for_display_simple(self):
        """Test formatting simple arguments."""
        args = {"param1": "value1", "param2": "value2"}
        result = TextFormatter.format_args_for_display(args)
        assert "param1: value1" in result
        assert "param2: value2" in result

    def test_format_args_for_display_empty(self):
        """Test formatting empty arguments."""
        result = TextFormatter.format_args_for_display({})
        assert result == ""

    def test_format_args_for_display_with_exclusions(self):
        """Test formatting arguments with excluded keys."""
        args = {"param1": "value1", "kwargs": "excluded", "_type": "excluded"}
        result = TextFormatter.format_args_for_display(args)
        assert "param1: value1" in result
        assert "kwargs" not in result
        assert "_type" not in result

    def test_format_args_for_display_list_values(self):
        """Test formatting arguments with list values."""
        args = {"prompts": ["First prompt", "Second prompt"]}
        result = TextFormatter.format_args_for_display(args)
        assert "prompts: First prompt" in result

    def test_format_result_for_display_error(self):
        """Test formatting result with error."""
        result = TextFormatter.format_result_for_display(
            "some result", "Error occurred"
        )
        assert result.startswith("❌error: Error occurred")

    def test_format_result_for_display_dict(self):
        """Test formatting dict result."""
        result_data = {"key1": "value1", "key2": "value2", "key3": "value3"}
        result = TextFormatter.format_result_for_display(result_data)
        assert "key1: value1" in result
        assert "key2: value2" in result

    def test_format_result_for_display_list(self):
        """Test formatting list result."""
        result_data = ["item1", "item2", "item3"]
        result = TextFormatter.format_result_for_display(result_data)
        assert "[3 items]" in result
        assert "item1" in result

    def test_format_result_for_display_empty_list(self):
        """Test formatting empty list result."""
        result = TextFormatter.format_result_for_display([])
        assert result == "[empty]"

    def test_get_display_name(self):
        """Test getting display name from event."""
        # Test with name
        event = TraceEvent(
            type=TraceType.TOOL,
            action=ActionType.CALL,
            details={"name": "test_tool"},
        )
        assert TextFormatter.get_display_name(event) == "test_tool"

        # Test with label fallback
        event = TraceEvent(
            type=TraceType.AGENT,
            action=ActionType.PROCESS,
            details={"label": "Processing"},
        )
        assert TextFormatter.get_display_name(event) == "Processing"

        # Test with action fallback
        event = TraceEvent(
            type=TraceType.USER,
            action=ActionType.INPUT,
            details={},
        )
        assert TextFormatter.get_display_name(event) == "input"

    def test_get_input_summary_user(self):
        """Test getting input summary for user events."""
        event = TraceEvent(
            type=TraceType.USER,
            action=ActionType.INPUT,
            details={"message": "Hello, how are you?"},
        )
        result = TextFormatter.get_input_summary(event)
        assert result == "Hello, how are you?"

    def test_get_input_summary_llm(self):
        """Test getting input summary for LLM events."""
        event = TraceEvent(
            type=TraceType.LLM,
            action=ActionType.REQUEST,
            details={"args": {"prompts": ["Test prompt for LLM"]}},
        )
        result = TextFormatter.get_input_summary(event)
        assert result == "Test prompt for LLM"

    def test_get_input_summary_tool(self):
        """Test getting input summary for tool events."""
        event = TraceEvent(
            type=TraceType.TOOL,
            action=ActionType.CALL,
            details={"args": {"query": "search term", "limit": 10}},
        )
        result = TextFormatter.get_input_summary(event)
        assert "query=search term" in result
        assert "limit=10" in result

    def test_get_output_summary_llm(self):
        """Test getting output summary for LLM events."""
        event = TraceEvent(
            type=TraceType.LLM,
            action=ActionType.RESPOND,
            details={"response": "This is the LLM response"},
        )
        result = TextFormatter.get_output_summary(event)
        assert result == "This is the LLM response"

    def test_get_output_summary_tool_success(self):
        """Test getting output summary for successful tool events."""
        event = TraceEvent(
            type=TraceType.TOOL,
            action=ActionType.RESPOND,
            details={"result": {"status": "success", "data": "result data"}},
        )
        result = TextFormatter.get_output_summary(event)
        assert "status:success" in result
        assert "data:result data" in result

    def test_get_output_summary_tool_error(self):
        """Test getting output summary for failed tool events."""
        event = TraceEvent(
            type=TraceType.TOOL,
            action=ActionType.RESPOND,
            details={"error": "Tool execution failed"},
        )
        result = TextFormatter.get_output_summary(event)
        assert result == "ERROR: Tool execution failed"

    def test_get_output_summary_agent(self):
        """Test getting output summary for agent events."""
        event = TraceEvent(
            type=TraceType.AGENT,
            action=ActionType.PROCESS,
            details={"response": {"output": "Agent response message"}},
        )
        result = TextFormatter.get_output_summary(event)
        assert result == "Agent response message"


class TestHierarchyHelper:
    """Test HierarchyHelper functionality."""

    def setup_method(self):
        """Set up test data."""
        self.root = TraceEvent(
            type=TraceType.USER,
            action=ActionType.INPUT,
            details={"message": "Hello"},
        )
        self.child1 = TraceEvent(
            type=TraceType.AGENT,
            action=ActionType.START,
            parent_id=self.root.id,
            details={"name": "agent1"},
        )
        self.child2 = TraceEvent(
            type=TraceType.LLM,
            action=ActionType.REQUEST,
            parent_id=self.child1.id,
            details={"model": "gpt-4"},
        )
        self.events = [self.root, self.child1, self.child2]
        self.helper = HierarchyHelper(self.events)

    def test_calculate_depth(self):
        """Test calculating event depth in hierarchy."""
        assert self.helper.calculate_depth(self.root.id) == 0
        assert self.helper.calculate_depth(self.child1.id) == 1
        assert self.helper.calculate_depth(self.child2.id) == 2

    def test_get_children(self):
        """Test getting children of an event."""
        children = self.helper.get_children(self.root.id)
        assert self.child1.id in children

        children = self.helper.get_children(self.child1.id)
        assert self.child2.id in children

        children = self.helper.get_children(self.child2.id)
        assert len(children) == 0

    def test_has_children(self):
        """Test checking if event has children."""
        assert self.helper.has_children(self.root.id)
        assert self.helper.has_children(self.child1.id)
        assert not self.helper.has_children(self.child2.id)

    def test_get_root_events(self):
        """Test getting root events."""
        roots = self.helper.get_root_events()
        assert self.root.id in roots
        assert len(roots) == 1

    def test_get_leaf_events(self):
        """Test getting leaf events."""
        leaves = self.helper.get_leaf_events()
        assert self.child2.id in leaves
        assert len(leaves) == 1

    def test_empty_hierarchy(self):
        """Test hierarchy helper with empty events."""
        helper = HierarchyHelper([])
        assert len(helper.get_root_events()) == 0
        assert len(helper.get_leaf_events()) == 0


class TestEdgeHelper:
    """Test EdgeHelper functionality."""

    def test_create_edge_label_llm_pair(self):
        """Test creating edge label for LLM request/response pair."""
        request = TraceEvent(
            type=TraceType.LLM,
            action=ActionType.REQUEST,
            details={"model": "gpt-4"},
        )
        response = TraceEvent(
            type=TraceType.LLM,
            action=ActionType.RESPOND,
            details={"response": "Test response"},
        )

        label = EdgeHelper.create_edge_label(request, response)
        assert label == "response"

    def test_create_edge_label_tool_pair(self):
        """Test creating edge label for tool call/response pair."""
        call = TraceEvent(
            type=TraceType.TOOL,
            action=ActionType.CALL,
            details={"name": "test_tool"},
        )
        response = TraceEvent(
            type=TraceType.TOOL,
            action=ActionType.RESPOND,
            details={"result": "success"},
        )

        label = EdgeHelper.create_edge_label(call, response)
        assert label == "result"

    def test_create_edge_label_tool_error(self):
        """Test creating edge label for tool error response."""
        call = TraceEvent(
            type=TraceType.TOOL,
            action=ActionType.CALL,
            details={"name": "test_tool"},
        )
        response = TraceEvent(
            type=TraceType.TOOL,
            action=ActionType.RESPOND,
            details={"error": "Tool failed"},
        )

        label = EdgeHelper.create_edge_label(call, response)
        assert label == "error"

    def test_create_edge_label_agent_relationships(self):
        """Test creating edge labels for agent relationships."""
        start = TraceEvent(
            type=TraceType.AGENT,
            action=ActionType.START,
            details={"name": "agent"},
        )
        process = TraceEvent(
            type=TraceType.AGENT,
            action=ActionType.PROCESS,
            details={"label": "Processing"},
        )
        end = TraceEvent(
            type=TraceType.AGENT,
            action=ActionType.END,
            details={"name": "agent"},
        )

        assert EdgeHelper.create_edge_label(start, process) == "executes"
        assert EdgeHelper.create_edge_label(start, end) == "completes"

    def test_create_edge_label_user_to_agent(self):
        """Test creating edge label for user to agent relationship."""
        user = TraceEvent(
            type=TraceType.USER,
            action=ActionType.INPUT,
            details={"message": "Hello"},
        )
        agent = TraceEvent(
            type=TraceType.AGENT,
            action=ActionType.START,
            details={"name": "agent"},
        )

        label = EdgeHelper.create_edge_label(user, agent)
        assert label == "triggers"

    def test_create_edge_label_default(self):
        """Test creating edge label for default relationships."""
        event1 = TraceEvent(
            type=TraceType.USER,
            action=ActionType.INPUT,
            details={},
        )
        event2 = TraceEvent(
            type=TraceType.USER,
            action=ActionType.INPUT,
            details={},
        )

        label = EdgeHelper.create_edge_label(event1, event2)
        assert label == "flows to"

    def test_get_edge_color_error(self):
        """Test getting edge color for error relationships."""
        parent = TraceEvent(type=TraceType.TOOL, action=ActionType.CALL, details={})
        child = TraceEvent(
            type=TraceType.TOOL,
            action=ActionType.RESPOND,
            details={"error": "Failed"},
        )

        color = EdgeHelper.get_edge_color(parent, child)
        assert color == "#ff4444"

    def test_get_edge_color_by_child_type(self):
        """Test getting edge color based on child event type."""
        parent = TraceEvent(type=TraceType.AGENT, action=ActionType.START, details={})

        llm_child = TraceEvent(
            type=TraceType.LLM, action=ActionType.REQUEST, details={}
        )
        assert EdgeHelper.get_edge_color(parent, llm_child) == "#ff9800"

        tool_child = TraceEvent(type=TraceType.TOOL, action=ActionType.CALL, details={})
        assert EdgeHelper.get_edge_color(parent, tool_child) == "#9c27b0"

        agent_child = TraceEvent(
            type=TraceType.AGENT, action=ActionType.START, details={}
        )
        assert EdgeHelper.get_edge_color(parent, agent_child) == "#2196f3"

        user_child = TraceEvent(
            type=TraceType.USER, action=ActionType.INPUT, details={}
        )
        assert EdgeHelper.get_edge_color(parent, user_child) == "#4caf50"

    def test_get_edge_color_default(self):
        """Test getting default edge color."""
        parent = TraceEvent(type=TraceType.AGENT, action=ActionType.START, details={})
        # Create a mock child with unknown type for default case
        child = TraceEvent(type=TraceType.AGENT, action=ActionType.PROCESS, details={})

        # This should fall through to default case
        color = EdgeHelper.get_edge_color(parent, child)
        # Default color should be gray
        assert color in ["#666666", "#2196f3"]  # Could be agent color or default


class TestConstants:
    """Test module constants."""

    def test_default_color_scheme(self):
        """Test default color scheme constants."""
        assert TraceType.USER in DEFAULT_COLOR_SCHEME
        assert TraceType.AGENT in DEFAULT_COLOR_SCHEME
        assert TraceType.LLM in DEFAULT_COLOR_SCHEME
        assert TraceType.TOOL in DEFAULT_COLOR_SCHEME

    def test_default_icon_scheme(self):
        """Test default icon scheme constants."""
        assert TraceType.USER in DEFAULT_ICON_SCHEME
        assert TraceType.AGENT in DEFAULT_ICON_SCHEME
        assert TraceType.LLM in DEFAULT_ICON_SCHEME
        assert TraceType.TOOL in DEFAULT_ICON_SCHEME

    def test_viz_options(self):
        """Test visualization options."""
        assert "📊 Statistics" in VIZ_OPTIONS
        assert "🌳 Hierarchical" in VIZ_OPTIONS
        assert "📅 Timeline" in VIZ_OPTIONS
        assert "🌊 Flow Diagram" in VIZ_OPTIONS
        assert "📋 Table View" in VIZ_OPTIONS


class TestViewerAppHelpers:
    """Test helper functions from the main app."""

    @pytest.mark.skipif(
        not _has_viewer_dependencies(),
        reason="viewer dependencies (pandas, streamlit) not installed",
    )
    def test_load_trace_data(self, tmp_path: Path):
        """Test loading trace data from file."""
        # Import here to avoid circular import issues
        from sybil_scope.viewer.app import load_trace_data

        # Prepare a temp JSONL file
        events = [
            TraceEvent(type=TraceType.USER, action=ActionType.INPUT, details={}),
            TraceEvent(type=TraceType.AGENT, action=ActionType.START, details={}),
        ]
        filepath = tmp_path / "test_traces.jsonl"
        with open(filepath, "w", encoding="utf-8") as f:
            for ev in events:
                f.write(ev.model_dump_json() + "\n")

        # Load from file
        result = load_trace_data(filepath)

        # Verify
        assert len(result) == 2
        assert result[0].type == TraceType.USER
        assert result[1].action == ActionType.START

    @pytest.mark.skipif(
        not _has_viewer_dependencies(),
        reason="viewer dependencies (pandas, streamlit) not installed",
    )
    def test_get_event_color_integration(self):
        """Test event color function integration."""
        from sybil_scope.viewer.app import get_event_color

        assert get_event_color(TraceType.USER) == "#4CAF50"
        assert get_event_color(TraceType.LLM) == "#FF9800"

    @pytest.mark.skipif(
        not _has_viewer_dependencies(),
        reason="viewer dependencies (pandas, streamlit) not installed",
    )
    def test_get_event_icon_integration(self):
        """Test event icon function integration."""
        from sybil_scope.viewer.app import get_event_icon

        assert get_event_icon(TraceType.AGENT) == "🤖"
        assert get_event_icon(TraceType.TOOL) == "🔧"

    @pytest.mark.skipif(
        not _has_viewer_dependencies(),
        reason="viewer dependencies (pandas, streamlit) not installed",
    )
    def test_format_timestamp_integration(self):
        """Test timestamp formatting function integration."""
        from sybil_scope.viewer.app import format_timestamp

        ts = datetime(2023, 10, 1, 14, 30, 45, 123456)
        result = format_timestamp(ts)
        assert result == "14:30:45.123"


class TestViewerIntegration:
    """Integration tests for viewer functionality."""

    def test_complete_workflow(self):
        """Test complete workflow with sample events."""
        # Create a realistic event sequence
        user_event = TraceEvent(
            type=TraceType.USER,
            action=ActionType.INPUT,
            details={"message": "What is the weather like?"},
        )

        agent_start = TraceEvent(
            type=TraceType.AGENT,
            action=ActionType.START,
            parent_id=user_event.id,
            details={"name": "weather_agent"},
        )

        tool_call = TraceEvent(
            type=TraceType.TOOL,
            action=ActionType.CALL,
            parent_id=agent_start.id,
            details={"name": "weather_api", "args": {"location": "San Francisco"}},
        )

        tool_response = TraceEvent(
            type=TraceType.TOOL,
            action=ActionType.RESPOND,
            parent_id=tool_call.id,
            details={"result": {"temperature": "72F", "condition": "sunny"}},
        )

        llm_request = TraceEvent(
            type=TraceType.LLM,
            action=ActionType.REQUEST,
            parent_id=agent_start.id,
            details={"model": "gpt-4", "args": {"prompts": ["Format weather data"]}},
        )

        llm_response = TraceEvent(
            type=TraceType.LLM,
            action=ActionType.RESPOND,
            parent_id=llm_request.id,
            details={"response": "The weather in San Francisco is sunny and 72F"},
        )

        agent_end = TraceEvent(
            type=TraceType.AGENT,
            action=ActionType.END,
            parent_id=None,  # Same level as start
            details={"name": "weather_agent"},
        )

        events = [
            user_event,
            agent_start,
            tool_call,
            tool_response,
            llm_request,
            llm_response,
            agent_end,
        ]

        # Test tree building
        tree = TreeStructureBuilder.build_corrected_tree_structure(events)
        assert user_event in tree[None]
        assert agent_start in tree[user_event.id]
        assert tool_call in tree[agent_start.id]
        assert llm_request in tree[agent_start.id]
        # agent_end should be filtered out in corrected tree

        # Test event pairing
        helper = EventPairHelper(events)
        pairs = helper.find_paired_events()
        assert tool_call.id in pairs
        assert pairs[tool_call.id] == tool_response
        assert llm_request.id in pairs
        assert pairs[llm_request.id] == llm_response

        # Test text formatting
        tool_input = TextFormatter.get_input_summary(tool_call)
        assert "location=San Francisco" in tool_input

        tool_output = TextFormatter.get_output_summary(tool_response)
        assert "temperature:72F" in tool_output

        llm_output = TextFormatter.get_output_summary(llm_response)
        # Response text is truncated to 40 chars, so check for partial match
        assert "sunny" in llm_output or "72F" in llm_output

        # Test hierarchy
        hierarchy = HierarchyHelper(events)
        assert hierarchy.calculate_depth(user_event.id) == 0
        assert hierarchy.calculate_depth(agent_start.id) == 1
        assert hierarchy.calculate_depth(tool_call.id) == 2

    def test_error_handling_workflow(self):
        """Test workflow with error conditions."""
        # Create events with errors
        tool_call = TraceEvent(
            type=TraceType.TOOL,
            action=ActionType.CALL,
            details={"name": "failing_tool", "args": {"param": "value"}},
        )

        tool_error = TraceEvent(
            type=TraceType.TOOL,
            action=ActionType.RESPOND,
            parent_id=tool_call.id,
            details={"error": "API connection failed", "error_type": "ConnectionError"},
        )

        events = [tool_call, tool_error]

        # Test event pairing still works with errors
        helper = EventPairHelper(events)
        pairs = helper.find_paired_events()
        assert tool_call.id in pairs
        assert pairs[tool_call.id] == tool_error

        # Test error formatting
        error_output = TextFormatter.format_result_for_display(
            None, tool_error.details["error"]
        )
        assert error_output.startswith("❌error:")
        assert "API connection failed" in error_output

        # Test edge color for errors
        edge_color = EdgeHelper.get_edge_color(tool_call, tool_error)
        assert edge_color == "#ff4444"  # Error color

    def test_performance_analysis_data(self):
        """Test data for performance analysis."""
        # Create events with timing
        base_time = datetime(2023, 10, 1, 14, 30, 0, 0)  # Fixed time

        start_event = TraceEvent(
            type=TraceType.LLM,
            action=ActionType.REQUEST,
            timestamp=base_time,
            details={"model": "gpt-4"},
        )

        end_event = TraceEvent(
            type=TraceType.LLM,
            action=ActionType.RESPOND,
            parent_id=start_event.id,
            timestamp=base_time.replace(microsecond=500000),  # 0.5 seconds later
            details={"response": "Generated response"},
        )

        events = [start_event, end_event]

        # Test duration calculation
        duration = TimeHelper.get_event_duration(start_event, events)
        assert duration == 0.5


if __name__ == "__main__":
    pytest.main([__file__])
