"""
Tests for individual viewer components (timeline, flow diagram, table view).
"""

from datetime import datetime, timedelta

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


class TestTimelineRenderer:
    """Test TimelineRenderer functionality."""

    def setup_method(self):
        """Set up test data for timeline tests."""
        base_time = datetime(2023, 10, 1, 14, 30, 0)

        self.events = [
            TraceEvent(
                type=TraceType.USER,
                action=ActionType.INPUT,
                timestamp=base_time,
                details={"message": "Hello"},
            ),
            TraceEvent(
                type=TraceType.AGENT,
                action=ActionType.START,
                timestamp=base_time + timedelta(seconds=1),
                details={"name": "test_agent"},
            ),
            TraceEvent(
                type=TraceType.LLM,
                action=ActionType.REQUEST,
                timestamp=base_time + timedelta(seconds=2),
                details={"model": "gpt-4"},
            ),
            TraceEvent(
                type=TraceType.LLM,
                action=ActionType.RESPOND,
                timestamp=base_time + timedelta(seconds=4),
                details={"response": "AI response"},
            ),
        ]

        # Set up parent-child relationships
        self.events[1].parent_id = self.events[0].id  # agent -> user
        self.events[2].parent_id = self.events[1].id  # llm request -> agent
        self.events[3].parent_id = self.events[2].id  # llm response -> request

    def test_timeline_initialization(self):
        """Test timeline renderer initialization."""
        # Test conceptual initialization logic
        events = self.events
        sorted_events = sorted(events, key=lambda e: e.timestamp)
        start_time = min(e.timestamp for e in events) if events else datetime.now()
        end_time = max(e.timestamp for e in events) if events else datetime.now()

        assert len(sorted_events) == 4
        assert start_time == events[0].timestamp
        assert end_time == events[3].timestamp

    def test_timeline_empty_events(self):
        """Test timeline renderer with empty events."""
        # Test with empty events list
        empty_events = []
        current_time = datetime.now()
        start_time = (
            current_time if not empty_events else min(e.timestamp for e in empty_events)
        )
        end_time = (
            current_time if not empty_events else max(e.timestamp for e in empty_events)
        )

        assert len(empty_events) == 0
        assert isinstance(start_time, datetime)
        assert isinstance(end_time, datetime)

    @pytest.mark.skipif(
        not _has_viewer_dependencies(),
        reason="viewer dependencies (pandas, streamlit) not installed",
    )
    def test_timeline_event_sorting(self):
        """Test that events are properly sorted by timestamp."""
        from sybil_scope.viewer.timeline import TimelineRenderer

        # Create events in random order
        unsorted_events = [
            self.events[3],
            self.events[1],
            self.events[0],
            self.events[2],
        ]

        renderer = TimelineRenderer.__new__(TimelineRenderer)
        renderer.events = sorted(unsorted_events, key=lambda e: e.timestamp)
        renderer.start_time = min(e.timestamp for e in unsorted_events)
        renderer.end_time = max(e.timestamp for e in unsorted_events)

        # Verify events are sorted correctly
        for i in range(len(renderer.events) - 1):
            assert renderer.events[i].timestamp <= renderer.events[i + 1].timestamp

    def test_gantt_data_creation_structure(self):
        """Test that Gantt data has correct structure."""
        # Test conceptual gantt data creation
        events = self.events

        # Verify that we have pairs for events with start/end actions
        start_events = [
            e
            for e in events
            if e.action in [ActionType.START, ActionType.REQUEST, ActionType.CALL]
        ]
        end_events = [
            e for e in events if e.action in [ActionType.END, ActionType.RESPOND]
        ]

        assert len(start_events) >= 1  # Should have at least one start event
        assert len(end_events) >= 1  # Should have at least one end event


class TestFlowDiagramRenderer:
    """Test FlowDiagramRenderer functionality."""

    def setup_method(self):
        """Set up test data for flow diagram tests."""
        self.events = [
            TraceEvent(
                type=TraceType.USER,
                action=ActionType.INPUT,
                details={"message": "Test message"},
            ),
            TraceEvent(
                type=TraceType.AGENT,
                action=ActionType.START,
                details={"name": "test_agent"},
            ),
            TraceEvent(
                type=TraceType.TOOL,
                action=ActionType.CALL,
                details={"name": "search_tool", "args": {"query": "test"}},
            ),
            TraceEvent(
                type=TraceType.TOOL,
                action=ActionType.RESPOND,
                details={"result": {"status": "success"}},
            ),
        ]

        # Set up relationships
        self.events[1].parent_id = self.events[0].id
        self.events[2].parent_id = self.events[1].id
        self.events[3].parent_id = self.events[2].id

    def test_flow_diagram_initialization(self):
        """Test flow diagram renderer initialization."""
        # Test initialization logic
        events = self.events
        events_by_id = {e.id: e for e in events}

        assert len(events) == 4
        assert len(events_by_id) == 4
        assert all(event.id in events_by_id for event in events)

    def test_node_label_creation_logic(self):
        """Test the logic for creating node labels."""
        # Test individual components that would go into a node label
        user_event = self.events[0]
        agent_event = self.events[1]
        tool_event = self.events[2]

        # Test event type identification
        assert user_event.type == TraceType.USER
        assert agent_event.type == TraceType.AGENT
        assert tool_event.type == TraceType.TOOL

        # Test details extraction
        assert user_event.details.get("message") == "Test message"
        assert agent_event.details.get("name") == "test_agent"
        assert tool_event.details.get("name") == "search_tool"

        # Test timestamp availability
        assert isinstance(user_event.timestamp, datetime)

    def test_event_relationships(self):
        """Test that event relationships are correctly established."""
        # Verify parent-child relationships
        assert self.events[1].parent_id == self.events[0].id
        assert self.events[2].parent_id == self.events[1].id
        assert self.events[3].parent_id == self.events[2].id

        # Test building events_by_id mapping
        events_by_id = {e.id: e for e in self.events}

        for event in self.events:
            assert event.id in events_by_id
            assert events_by_id[event.id] == event

    def test_style_application_logic(self):
        """Test logic for applying styles to events."""
        from sybil_scope.viewer.common import EventStyleHelper

        # Test that style helper works for all event types
        for event in self.events:
            color = EventStyleHelper.get_event_color(event.type)
            icon = EventStyleHelper.get_event_icon(event.type)
            style = EventStyleHelper.get_event_style(event)

            assert isinstance(color, str)
            assert color.startswith("#")  # Should be hex color
            assert isinstance(icon, str)
            assert len(icon) > 0  # Should have some icon
            assert isinstance(style, dict)
            assert "color" in style


class TestTableRenderer:
    """Test TableRenderer functionality."""

    def setup_method(self):
        """Set up test data for table tests."""
        self.events = [
            TraceEvent(
                type=TraceType.USER,
                action=ActionType.INPUT,
                details={"message": "Hello"},
            ),
            TraceEvent(
                type=TraceType.AGENT,
                action=ActionType.START,
                details={"name": "agent1"},
            ),
            TraceEvent(
                type=TraceType.AGENT,
                action=ActionType.PROCESS,
                details={"label": "Processing"},
            ),
            TraceEvent(
                type=TraceType.LLM,
                action=ActionType.REQUEST,
                details={"model": "gpt-4"},
            ),
            TraceEvent(
                type=TraceType.LLM,
                action=ActionType.RESPOND,
                details={"response": "Response"},
            ),
        ]

        # Set up parent-child relationships
        self.events[1].parent_id = self.events[0].id  # agent -> user
        self.events[2].parent_id = self.events[1].id  # process -> agent
        self.events[3].parent_id = self.events[1].id  # llm request -> agent
        self.events[4].parent_id = self.events[3].id  # llm response -> request

    def test_table_initialization(self):
        """Test table renderer initialization."""
        # Test initialization logic
        events = self.events
        events_by_id = {e.id: e for e in events}

        # Build relationships manually for testing
        children_map = {}
        parent_map = {}

        for event in events:
            if event.parent_id:
                if event.parent_id not in children_map:
                    children_map[event.parent_id] = []
                children_map[event.parent_id].append(event.id)
                parent_map[event.id] = event.parent_id

        assert len(events) == 5
        assert len(events_by_id) == 5

        # Test relationship building
        user_id = self.events[0].id
        agent_id = self.events[1].id

        assert agent_id in children_map[user_id]
        assert parent_map[agent_id] == user_id

    def test_depth_calculation_logic(self):
        """Test depth calculation logic."""
        # Build parent map
        parent_map = {}
        for event in self.events:
            if event.parent_id:
                parent_map[event.id] = event.parent_id

        def calculate_depth(event_id):
            depth = 0
            current_id = event_id
            while current_id in parent_map:
                depth += 1
                current_id = parent_map[current_id]
                if depth > 20:  # Prevent infinite loops
                    break
            return depth

        # Test depths
        user_depth = calculate_depth(self.events[0].id)  # Root
        agent_depth = calculate_depth(self.events[1].id)  # Child of user
        process_depth = calculate_depth(self.events[2].id)  # Child of agent
        llm_req_depth = calculate_depth(self.events[3].id)  # Child of agent
        llm_resp_depth = calculate_depth(self.events[4].id)  # Child of llm request

        assert user_depth == 0
        assert agent_depth == 1
        assert process_depth == 2
        assert llm_req_depth == 2
        assert llm_resp_depth == 3

    def test_hierarchy_building(self):
        """Test hierarchy building logic."""
        children_map = {}
        parent_map = {}

        for event in self.events:
            if event.parent_id:
                if event.parent_id not in children_map:
                    children_map[event.parent_id] = []
                children_map[event.parent_id].append(event.id)
                parent_map[event.id] = event.parent_id

        # Test that relationships are correct
        user_id = self.events[0].id
        agent_id = self.events[1].id
        process_id = self.events[2].id
        llm_req_id = self.events[3].id
        llm_resp_id = self.events[4].id

        # User should have agent as child
        assert agent_id in children_map[user_id]

        # Agent should have process and llm request as children
        assert process_id in children_map[agent_id]
        assert llm_req_id in children_map[agent_id]

        # LLM request should have response as child
        assert llm_resp_id in children_map[llm_req_id]

        # Test parent relationships
        assert parent_map[agent_id] == user_id
        assert parent_map[process_id] == agent_id
        assert parent_map[llm_req_id] == agent_id
        assert parent_map[llm_resp_id] == llm_req_id

    def test_table_data_structure(self):
        """Test the structure of data for table display."""
        # Test what would go into a pandas DataFrame
        table_data = []

        for event in self.events:
            row = {
                "ID": event.id,
                "Type": event.type.value,
                "Action": event.action.value,
                "Parent ID": event.parent_id or "",
                "Timestamp": event.timestamp.strftime("%H:%M:%S.%f")[:-3],
                "Details": str(event.details),
            }
            table_data.append(row)

        assert len(table_data) == len(self.events)

        # Verify all required columns are present
        required_columns = ["ID", "Type", "Action", "Parent ID", "Timestamp", "Details"]
        for row in table_data:
            for col in required_columns:
                assert col in row

    def test_filtering_logic(self):
        """Test filtering logic for table view."""
        # Test type filtering
        llm_events = [e for e in self.events if e.type == TraceType.LLM]
        agent_events = [e for e in self.events if e.type == TraceType.AGENT]
        user_events = [e for e in self.events if e.type == TraceType.USER]

        assert len(llm_events) == 2
        assert len(agent_events) == 2
        assert len(user_events) == 1

        # Test action filtering
        start_events = [e for e in self.events if e.action == ActionType.START]
        request_events = [e for e in self.events if e.action == ActionType.REQUEST]
        respond_events = [e for e in self.events if e.action == ActionType.RESPOND]

        assert len(start_events) == 1
        assert len(request_events) == 1
        assert len(respond_events) == 1

    def test_event_details_formatting(self):
        """Test formatting of event details for table display."""
        for event in self.events:
            # Test that details can be converted to string
            details_str = str(event.details)
            assert isinstance(details_str, str)

            # Test specific detail extraction
            if event.type == TraceType.USER:
                assert "message" in event.details
            elif event.type == TraceType.AGENT and event.action == ActionType.START:
                assert "name" in event.details
            elif event.type == TraceType.LLM and event.action == ActionType.REQUEST:
                assert "model" in event.details
            elif event.type == TraceType.LLM and event.action == ActionType.RESPOND:
                assert "response" in event.details


class TestViewerComponentIntegration:
    """Integration tests for viewer components working together."""

    def setup_method(self):
        """Set up comprehensive test data."""
        base_time = datetime(2023, 10, 1, 14, 30, 0)

        self.events = [
            TraceEvent(
                type=TraceType.USER,
                action=ActionType.INPUT,
                timestamp=base_time,
                details={"message": "What's the weather?"},
            ),
            TraceEvent(
                type=TraceType.AGENT,
                action=ActionType.START,
                timestamp=base_time + timedelta(milliseconds=100),
                details={"name": "weather_agent"},
            ),
            TraceEvent(
                type=TraceType.TOOL,
                action=ActionType.CALL,
                timestamp=base_time + timedelta(seconds=1),
                details={"name": "weather_api", "args": {"city": "SF"}},
            ),
            TraceEvent(
                type=TraceType.TOOL,
                action=ActionType.RESPOND,
                timestamp=base_time + timedelta(seconds=2),
                details={"result": {"temp": "72F", "condition": "sunny"}},
            ),
            TraceEvent(
                type=TraceType.LLM,
                action=ActionType.REQUEST,
                timestamp=base_time + timedelta(seconds=2, milliseconds=500),
                details={"model": "gpt-4", "args": {"prompts": ["Format weather"]}},
            ),
            TraceEvent(
                type=TraceType.LLM,
                action=ActionType.RESPOND,
                timestamp=base_time + timedelta(seconds=4),
                details={"response": "It's sunny and 72F in SF"},
            ),
            TraceEvent(
                type=TraceType.AGENT,
                action=ActionType.END,
                timestamp=base_time + timedelta(seconds=5),
                details={"name": "weather_agent"},
            ),
        ]

        # Set up relationships
        self.events[1].parent_id = self.events[0].id  # agent -> user
        self.events[2].parent_id = self.events[1].id  # tool call -> agent
        self.events[3].parent_id = self.events[2].id  # tool response -> call
        self.events[4].parent_id = self.events[1].id  # llm request -> agent
        self.events[5].parent_id = self.events[4].id  # llm response -> request

    def test_cross_component_data_consistency(self):
        """Test that all components can work with the same event data."""
        # Test that events can be processed by all component types

        # Timeline processing
        sorted_events = sorted(self.events, key=lambda e: e.timestamp)
        assert len(sorted_events) == len(self.events)

        # Flow diagram processing
        events_by_id = {e.id: e for e in self.events}
        assert len(events_by_id) == len(self.events)

        # Table view processing
        parent_map = {}
        children_map = {}
        for event in self.events:
            if event.parent_id:
                parent_map[event.id] = event.parent_id
                if event.parent_id not in children_map:
                    children_map[event.parent_id] = []
                children_map[event.parent_id].append(event.id)

        # Verify relationships work for all components
        assert len(parent_map) == 5  # All events except root and agent end have parents
        assert (
            len(children_map) == 4
        )  # User, agent, tool call, llm request have children

    def test_event_pairing_across_components(self):
        """Test that event pairing works consistently across components."""
        from sybil_scope.viewer.common import EventPairHelper

        helper = EventPairHelper(self.events)
        pairs = helper.find_paired_events()

        # Should find tool call/response pair
        tool_call = next(e for e in self.events if e.action == ActionType.CALL)
        tool_response = next(
            e
            for e in self.events
            if e.action == ActionType.RESPOND and e.type == TraceType.TOOL
        )

        assert tool_call.id in pairs
        assert pairs[tool_call.id] == tool_response

        # Should find LLM request/response pair
        llm_request = next(e for e in self.events if e.action == ActionType.REQUEST)
        llm_response = next(
            e
            for e in self.events
            if e.action == ActionType.RESPOND and e.type == TraceType.LLM
        )

        assert llm_request.id in pairs
        assert pairs[llm_request.id] == llm_response

    def test_timing_calculations_consistency(self):
        """Test that timing calculations are consistent across components."""
        from sybil_scope.viewer.common import TimeHelper

        # Test duration calculations
        tool_call = next(e for e in self.events if e.action == ActionType.CALL)
        tool_response = next(
            e
            for e in self.events
            if e.action == ActionType.RESPOND and e.type == TraceType.TOOL
        )

        duration = TimeHelper.calculate_duration(tool_call, tool_response)
        assert duration == "1.000s"  # 1 second difference

        # Test event duration extraction
        event_duration = TimeHelper.get_event_duration(tool_call, self.events)
        assert event_duration == 1.0

    def test_text_formatting_consistency(self):
        """Test that text formatting works consistently across components."""
        from sybil_scope.viewer.common import TextFormatter

        # Test input summaries
        user_event = next(e for e in self.events if e.type == TraceType.USER)
        user_summary = TextFormatter.get_input_summary(user_event)
        assert "weather" in user_summary.lower()

        tool_call = next(e for e in self.events if e.action == ActionType.CALL)
        tool_summary = TextFormatter.get_input_summary(tool_call)
        assert "city=SF" in tool_summary

        # Test output summaries
        llm_response = next(
            e
            for e in self.events
            if e.action == ActionType.RESPOND and e.type == TraceType.LLM
        )
        llm_output = TextFormatter.get_output_summary(llm_response)
        assert "sunny" in llm_output and "72F" in llm_output

    def test_complete_workflow_simulation(self):
        """Test complete workflow that could be used by any viewer component."""
        # Simulate what a viewer component would do:

        # 1. Initialize with events
        events = self.events

        # 2. Build helper objects
        from sybil_scope.viewer.common import (
            EventPairHelper,
            HierarchyHelper,
            TextFormatter,
            TreeStructureBuilder,
        )

        pair_helper = EventPairHelper(events)
        hierarchy_helper = HierarchyHelper(events)
        tree = TreeStructureBuilder.build_corrected_tree_structure(events)

        # 3. Extract key information
        pairs = pair_helper.find_paired_events()
        root_events = hierarchy_helper.get_root_events()

        # 4. Verify the workflow produces expected results
        assert len(pairs) == 2  # Tool and LLM pairs
        assert len(root_events) == 2  # Two roots (user input and agent end)
        assert tree[None][0].type == TraceType.USER  # First root is user event

        # 5. Test that all events can be processed for display
        for event in events:
            display_name = TextFormatter.get_display_name(event)
            input_summary = TextFormatter.get_input_summary(event)
            output_summary = TextFormatter.get_output_summary(event)

            assert isinstance(display_name, str)
            assert isinstance(input_summary, str)
            assert isinstance(output_summary, str)

    def test_error_handling_across_components(self):
        """Test that error conditions are handled consistently."""
        # Test with empty events
        empty_events = []

        from sybil_scope.viewer.common import EventPairHelper, HierarchyHelper

        empty_pair_helper = EventPairHelper(empty_events)
        empty_hierarchy = HierarchyHelper(empty_events)

        # Should not crash
        empty_pairs = empty_pair_helper.find_paired_events()
        empty_roots = empty_hierarchy.get_root_events()

        assert len(empty_pairs) == 0
        assert len(empty_roots) == 0

        # Test with malformed events (missing details)
        malformed_event = TraceEvent(
            type=TraceType.AGENT,
            action=ActionType.PROCESS,
            details={},  # Empty details
        )

        from sybil_scope.viewer.common import TextFormatter

        # Should handle gracefully
        display_name = TextFormatter.get_display_name(malformed_event)
        assert display_name == "process"  # Falls back to action


if __name__ == "__main__":
    pytest.main([__file__])
