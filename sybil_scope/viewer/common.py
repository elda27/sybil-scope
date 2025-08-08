"""
Common utilities and shared functionality for Sibyl Scope viewer components.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from enum import Enum
from typing import Any, TypedDict

from sybil_scope.core import ActionType, TraceEvent, TraceType


class TraceDict(TypedDict):
    """Type definition for agent trace grouping."""

    starts: list[TraceEvent]
    ends: list[TraceEvent]


TraceEventTree = dict[int | None, list[TraceEvent]]


class EventPairHelper:
    """Helper class for managing event pairs and relationships."""

    def __init__(self, events: list[TraceEvent]):
        self.events = events
        self.events_by_id = {e.id: e for e in events}

    def find_paired_events(self) -> dict[int, TraceEvent]:
        """Find request/response and call/response pairs for LLM and Tool events."""
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
        return pairs

    def find_agent_start_end_pairs(self) -> dict[int, int]:
        """Find matching agent start/end pairs based on chronological order."""
        # Group agents by parent_id
        agents_by_parent: dict[int | None, TraceDict] = {}
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

            # Match each start with the next end
            for i, start in enumerate(starts):
                if i < len(ends):
                    agent_pairs[start.id] = ends[i].id

        return agent_pairs


class TreeStructureBuilder:
    """Helper class for building tree structures from events."""

    @staticmethod
    def build_tree_structure(events: list[TraceEvent]) -> TraceEventTree:
        """Build parent-child tree structure from events."""
        tree = defaultdict(list)
        for event in events:
            tree[event.parent_id].append(event)
        return tree

    @staticmethod
    def build_corrected_tree_structure(events: list[TraceEvent]) -> TraceEventTree:
        """Build corrected parent-child tree structure, fixing agent start/end relationships."""
        # First, identify agent start/end pairs that should be grouped
        agent_pairs = {}
        agents_by_parent: dict[int | None, TraceDict] = {}

        for event in events:
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
        for parent, agents in agents_by_parent.items():
            starts = sorted(agents["starts"], key=lambda x: x.timestamp)
            ends = sorted(agents["ends"], key=lambda x: x.timestamp)

            for i, start in enumerate(starts):
                if i < len(ends):
                    agent_pairs[start.id] = ends[i].id

        # Build corrected tree structure
        tree = defaultdict(list)
        skipped_end_ids = set(agent_pairs.values())

        for event in events:
            # Skip agent end events that are part of a pair
            if event.id in skipped_end_ids:
                continue

            # For other events, use original parent_id
            tree[event.parent_id].append(event)

        return tree


class EventStyleHelper:
    """Helper class for consistent event styling across visualizations."""

    @staticmethod
    def get_event_color(event_type: TraceType) -> str:
        """Get color for event type."""
        colors = {
            TraceType.USER: "#4CAF50",  # Green
            TraceType.AGENT: "#2196F3",  # Blue
            TraceType.LLM: "#FF9800",  # Orange
            TraceType.TOOL: "#9C27B0",  # Purple
        }
        return colors.get(event_type, "#757575")

    @staticmethod
    def get_event_icon(event_type: TraceType) -> str:
        """Get icon for event type."""
        icons = {
            TraceType.USER: "👤",
            TraceType.AGENT: "🤖",
            TraceType.LLM: "🧠",
            TraceType.TOOL: "🔧",
        }
        return icons.get(event_type, "📍")

    @staticmethod
    def get_event_style(event: TraceEvent) -> dict[str, Any]:
        """Get comprehensive style configuration for an event."""
        colors = {
            TraceType.USER: {"bg": "#E8F5E8", "border": "#4CAF50", "text": "#2E7D32"},
            TraceType.AGENT: {"bg": "#E3F2FD", "border": "#2196F3", "text": "#1565C0"},
            TraceType.LLM: {"bg": "#FFF3E0", "border": "#FF9800", "text": "#E65100"},
            TraceType.TOOL: {"bg": "#F3E5F5", "border": "#9C27B0", "text": "#6A1B9A"},
        }

        color_scheme = colors.get(
            event.type, {"bg": "#F5F5F5", "border": "#757575", "text": "#424242"}
        )

        # Different shapes based on action
        shapes = {
            ActionType.INPUT: "ellipse",
            ActionType.START: "box",
            ActionType.END: "box",
            ActionType.PROCESS: "diamond",
            ActionType.REQUEST: "circle",
            ActionType.RESPOND: "circle",
            ActionType.CALL: "triangle",
        }

        return {
            "color": {
                "background": color_scheme["bg"],
                "border": color_scheme["border"],
                "highlight": {
                    "background": color_scheme["bg"],
                    "border": color_scheme["border"],
                },
            },
            "font": {"color": color_scheme["text"], "size": 12},
            "shape": shapes.get(event.action, "box"),
            "borderWidth": 2,
            "borderWidthSelected": 3,
        }


class TimeHelper:
    """Helper class for time-related operations."""

    @staticmethod
    def format_timestamp(ts: datetime) -> str:
        """Format timestamp for display."""
        return ts.strftime("%H:%M:%S.%f")[:-3]

    @staticmethod
    def calculate_duration(
        start_event: TraceEvent,
        end_event: TraceEvent | None = None,
        events: list[TraceEvent] | None = None,
        tree: TraceEventTree | None = None,
        agent_pairs: dict[int, int] | None = None,
    ) -> str:
        """Calculate duration between two events."""
        if end_event:
            duration = (end_event.timestamp - start_event.timestamp).total_seconds()
            return f"{duration:.3f}s"
        else:
            # For agent events, try to find corresponding end event using agent_pairs
            if (
                start_event.type == TraceType.AGENT
                and start_event.action == ActionType.START
                and agent_pairs
                and events
            ):
                end_id = agent_pairs.get(start_event.id)
                if end_id:
                    for event in events:
                        if event.id == end_id:
                            duration = (
                                event.timestamp - start_event.timestamp
                            ).total_seconds()
                            return f"{duration:.3f}s"

            # If no end event, calculate from children
            if tree:
                children = tree.get(start_event.id, [])
                if children:
                    latest_child = max(children, key=lambda x: x.timestamp)
                    duration = (
                        latest_child.timestamp - start_event.timestamp
                    ).total_seconds()
                    return f"{duration:.3f}s"
            return "0.000s"

    @staticmethod
    def get_event_duration(event: TraceEvent, events: list[TraceEvent]) -> float | None:
        """Get duration for events that have corresponding end events."""
        if event.action in [ActionType.START, ActionType.REQUEST, ActionType.CALL]:
            # Find matching end event
            for potential_end in events:
                if potential_end.parent_id == event.id and potential_end.action in [
                    ActionType.END,
                    ActionType.RESPOND,
                ]:
                    return (potential_end.timestamp - event.timestamp).total_seconds()
        return None


class TextFormatter:
    """Helper class for text formatting and display."""

    @staticmethod
    def truncate_text(text: Any, max_length: int = 50) -> str:
        """Truncate text to specified length with ellipsis."""
        if isinstance(text, str) and len(text) > max_length:
            return text[:max_length] + "..."
        return str(text) if text else ""

    @staticmethod
    def format_args_for_display(args: dict[str, Any], max_length: int = 50) -> str:
        """Format arguments dict for display in expander label."""
        if not args:
            return ""
        arg_parts = []
        for key, value in args.items():
            if key not in ["kwargs", "args", "_type"] and value:
                if isinstance(value, list):
                    if len(value) > 0 and isinstance(value[0], str):
                        # For lists, show first element
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

    @staticmethod
    def format_result_for_display(result: Any, error: str | None = None) -> str:
        """Format result or error for display in expander label."""
        if error:
            return (
                f"❌error: {error[:50]}..." if len(error) > 50 else f"❌error: {error}"
            )

        if isinstance(result, dict):
            # For dict results, show key-value pairs
            result_parts = []
            for key, value in result.items():
                str_val = str(value)[:30] + ("..." if len(str(value)) > 30 else "")
                result_parts.append(f"{key}: {str_val}")
            return ", ".join(result_parts[:2])
        elif isinstance(result, list):
            # For list results, show count and first item
            if len(result) > 0:
                return f"[{len(result)} items] {str(result[0])[:50]}..."
            return "[empty]"
        else:
            return str(result)[:100] + ("..." if len(str(result)) > 100 else "")

    @staticmethod
    def get_display_name(event: TraceEvent) -> str:
        """Get the best display name for an event."""
        name = event.details.get("name", "")
        label = event.details.get("label", "")
        function = event.details.get("function", "")
        model = event.details.get("model", "")

        return name or label or function or model or event.action.value

    @staticmethod
    def get_input_summary(event: TraceEvent) -> str:
        """Extract and format input information from event."""
        # For USER events
        if event.type == TraceType.USER:
            message = event.details.get("message", "")
            if message:
                return message[:50] + ("..." if len(message) > 50 else "")

        # For LLM REQUEST events
        elif event.type == TraceType.LLM and event.action == ActionType.REQUEST:
            args = event.details.get("args", {})
            if isinstance(args, dict):
                # Try to get prompt from various possible keys
                prompts = args.get("prompts", [])
                if prompts and isinstance(prompts, list) and len(prompts) > 0:
                    prompt_text = prompts[0]
                else:
                    prompt_text = args.get("prompt", args.get("messages", ""))

                if prompt_text:
                    prompt_str = str(prompt_text)
                    return prompt_str[:40] + ("..." if len(prompt_str) > 40 else "")

        # For TOOL CALL events
        elif event.type == TraceType.TOOL and event.action == ActionType.CALL:
            args = event.details.get("args", {})
            if isinstance(args, dict) and args:
                # Format key arguments
                arg_parts = []
                for key, value in list(args.items())[:2]:  # First 2 args only
                    if key not in ["kwargs", "_type"] and value is not None:
                        val_str = str(value)[:20] + (
                            "..." if len(str(value)) > 20 else ""
                        )
                        arg_parts.append(f"{key}={val_str}")
                return ", ".join(arg_parts)

        return ""

    @staticmethod
    def get_output_summary(event: TraceEvent) -> str:
        """Extract and format output information from event."""
        # For LLM RESPOND events
        if event.type == TraceType.LLM and event.action == ActionType.RESPOND:
            response = event.details.get("response", "")
            if response:
                response_str = str(response)
                return response_str[:40] + ("..." if len(response_str) > 40 else "")

        # For TOOL RESPOND events
        elif event.type == TraceType.TOOL and event.action == ActionType.RESPOND:
            # Check for error first
            error = event.details.get("error", "")
            if error:
                return f"ERROR: {error[:30]}" + ("..." if len(error) > 30 else "")

            # Otherwise get result
            result = event.details.get("result", "")
            if result:
                if isinstance(result, dict):
                    # For dict results, show key info
                    result_parts = []
                    for key, value in list(result.items())[:2]:  # First 2 keys only
                        val_str = str(value)[:15] + (
                            "..." if len(str(value)) > 15 else ""
                        )
                        result_parts.append(f"{key}:{val_str}")
                    return ", ".join(result_parts)
                elif isinstance(result, list):
                    return f"[{len(result)} items]"
                else:
                    result_str = str(result)
                    return result_str[:40] + ("..." if len(result_str) > 40 else "")

        # For AGENT PROCESS events with response
        elif event.type == TraceType.AGENT and event.action == ActionType.PROCESS:
            response = event.details.get("response", "")
            if response:
                if isinstance(response, dict):
                    # Try to get meaningful output
                    output = response.get("output", response.get("result", ""))
                    if output:
                        output_str = str(output)
                        return output_str[:40] + ("..." if len(output_str) > 40 else "")
                else:
                    response_str = str(response)
                    return response_str[:40] + ("..." if len(response_str) > 40 else "")

        return ""


class HierarchyHelper:
    """Helper class for hierarchy operations."""

    def __init__(self, events: list[TraceEvent]):
        self.events = events
        self.events_by_id = {e.id: e for e in events}

        # Build parent-child relationships
        self.children_map: dict[int, list[int]] = {}
        self.parent_map: dict[int, int] = {}

        for event in events:
            if event.parent_id:
                if event.parent_id not in self.children_map:
                    self.children_map[event.parent_id] = []
                self.children_map[event.parent_id].append(event.id)
                self.parent_map[event.id] = event.parent_id

    def calculate_depth(self, event_id: int) -> int:
        """Calculate depth of event in hierarchy."""
        depth = 0
        current_id = event_id

        while current_id in self.parent_map:
            depth += 1
            current_id = self.parent_map[current_id]
            # Prevent infinite loops
            if depth > 20:
                break

        return depth

    def get_children(self, event_id: int) -> list[int]:
        """Get child event IDs for a given event."""
        return self.children_map.get(event_id, [])

    def has_children(self, event_id: int) -> bool:
        """Check if event has children."""
        return event_id in self.children_map

    def get_root_events(self) -> list[int]:
        """Get all root event IDs (events with no parent)."""
        return [e.id for e in self.events if e.parent_id is None]

    def get_leaf_events(self) -> list[int]:
        """Get all leaf event IDs (events with no children)."""
        return [e.id for e in self.events if e.id not in self.children_map]


class EdgeHelper:
    """Helper class for creating edges and relationships between events."""

    @staticmethod
    def create_edge_label(parent_event: TraceEvent, child_event: TraceEvent) -> str:
        """Create informative label for edge between two events."""
        # LLM request -> respond relationship
        if (
            parent_event.type == TraceType.LLM
            and parent_event.action == ActionType.REQUEST
            and child_event.type == TraceType.LLM
            and child_event.action == ActionType.RESPOND
        ):
            return "response"

        # Tool call -> respond relationship
        elif (
            parent_event.type == TraceType.TOOL
            and parent_event.action == ActionType.CALL
            and child_event.type == TraceType.TOOL
            and child_event.action == ActionType.RESPOND
        ):
            error = child_event.details.get("error", "")
            if error:
                return "error"
            else:
                return "result"

        # Agent start -> process/end relationship
        elif (
            parent_event.type == TraceType.AGENT
            and parent_event.action == ActionType.START
        ):
            if child_event.action == ActionType.PROCESS:
                return "executes"
            elif child_event.action == ActionType.END:
                return "completes"
            else:
                return "invokes"

        # User input -> agent start
        elif (
            parent_event.type == TraceType.USER
            and parent_event.action == ActionType.INPUT
            and child_event.type == TraceType.AGENT
            and child_event.action == ActionType.START
        ):
            return "triggers"

        # Agent -> LLM/Tool relationships
        elif parent_event.type == TraceType.AGENT and child_event.type in [
            TraceType.LLM,
            TraceType.TOOL,
        ]:
            return "uses"

        # Default relationship
        else:
            return "flows to"

    @staticmethod
    def get_edge_color(parent_event: TraceEvent, child_event: TraceEvent) -> str:
        """Get color for edge based on relationship type."""
        # Error relationships in red
        if child_event.details.get("error", ""):
            return "#ff4444"

        # LLM relationships in orange
        elif child_event.type == TraceType.LLM:
            return "#ff9800"

        # Tool relationships in purple
        elif child_event.type == TraceType.TOOL:
            return "#9c27b0"

        # Agent relationships in blue
        elif child_event.type == TraceType.AGENT:
            return "#2196f3"

        # User relationships in green
        elif child_event.type == TraceType.USER:
            return "#4caf50"

        # Default gray
        else:
            return "#666666"


# Common constants
DEFAULT_COLOR_SCHEME = {
    TraceType.USER: "#4CAF50",
    TraceType.AGENT: "#2196F3",
    TraceType.LLM: "#FF9800",
    TraceType.TOOL: "#9C27B0",
}

DEFAULT_ICON_SCHEME = {
    TraceType.USER: "👤",
    TraceType.AGENT: "🤖",
    TraceType.LLM: "🧠",
    TraceType.TOOL: "🔧",
}

VIZ_OPTIONS = [
    "📊 Statistics",
    "🌳 Hierarchical",
    "📅 Timeline",
    "🌊 Flow Diagram",
    "📋 Table View",
]


class VizOption(Enum):
    """Enum for visualization options shown in the app UI."""

    STATISTICS = "📊 Statistics"
    HIERARCHICAL = "🌳 Hierarchical"
    TIMELINE = "📅 Timeline"
    FLOW_DIAGRAM = "🌊 Flow Diagram"
    TABLE_VIEW = "📋 Table View"

    def __str__(self) -> str:
        # Helpful when Streamlit needs to render option values
        return self.value


# Keep VIZ_OPTIONS for backwards compatibility with tests and any external imports
# while encouraging use of VizOption where possible.
VIZ_OPTIONS = [opt.value for opt in VizOption]
