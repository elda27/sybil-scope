"""
Flow diagram visualization using Streamlit components.
"""

from typing import Any

import streamlit as st

from sybil_scope.core import ActionType, TraceEvent, TraceType
from sybil_scope.viewer.common import (
    EventStyleHelper,
    TextFormatter,
    TimeHelper,
)


class FlowDiagramRenderer:
    """Renders trace events as interactive flow diagrams."""

    def __init__(self, events: list[TraceEvent]):
        self.events = events
        self.events_by_id = {e.id: e for e in events}

    def get_event_style(self, event: TraceEvent) -> dict[str, Any]:
        """Get style configuration for an event node."""
        return EventStyleHelper.get_event_style(event)

    def create_node_label(self, event: TraceEvent) -> str:
        """Create a detailed label for the node."""
        # Get event type icon
        icon = EventStyleHelper.get_event_icon(event.type)

        # Get name/label from details
        display_name = TextFormatter.get_display_name(event)

        # Start building label components
        label_parts = [f"{icon} {event.type.value} - {event.action.value}"]

        if display_name and display_name != event.action.value:
            # Truncate long names
            if len(display_name) > 25:
                display_name = display_name[:22] + "..."
            label_parts.append(f"📋 {display_name}")

        # Add timing information
        time_str = TimeHelper.format_timestamp(event.timestamp)
        label_parts.append(f"⏰ {time_str}")

        # Add duration for paired events (LLM request/respond, Tool call/respond)
        duration_str = self._calculate_event_duration(event)
        if duration_str:
            label_parts.append(f"⏱️ {duration_str}")

        # Add input information
        input_info = TextFormatter.get_input_summary(event)
        if input_info:
            label_parts.append(f"📥 {input_info}")

        # Add output information
        output_info = TextFormatter.get_output_summary(event)
        if output_info:
            label_parts.append(f"📤 {output_info}")

        # Add error information if present
        error = event.details.get("error", "")
        if error:
            error_short = TextFormatter.truncate_text(error, 30)
            label_parts.append(f"❌ {error_short}")

        # Add model information for LLM events
        if event.type == TraceType.LLM:
            model = event.details.get("model", "")
            if model:
                label_parts.append(f"🧠 {model}")

        # Add performance metrics if available
        llm_output = event.details.get("llm_output", {})
        if llm_output and isinstance(llm_output, dict):
            token_usage = llm_output.get("token_usage", {})
            if token_usage:
                total_tokens = token_usage.get("total_tokens", 0)
                if total_tokens:
                    label_parts.append(f"🎯 {total_tokens} tokens")

        return "\\n".join(label_parts)

    def _calculate_event_duration(self, event: TraceEvent) -> str:
        """Calculate duration for paired events or event with children."""
        # Find paired response/respond event
        for other_event in self.events:
            if other_event.parent_id == event.id:
                if (
                    event.action == ActionType.REQUEST
                    and other_event.action == ActionType.RESPOND
                ) or (
                    event.action == ActionType.CALL
                    and other_event.action == ActionType.RESPOND
                ):
                    duration = (other_event.timestamp - event.timestamp).total_seconds()
                    return f"{duration:.3f}s"

        # For agent START events, find corresponding END event
        if event.type == TraceType.AGENT and event.action == ActionType.START:
            # Find agent end events with same parent
            for other_event in self.events:
                if (
                    other_event.type == TraceType.AGENT
                    and other_event.action == ActionType.END
                    and other_event.parent_id == event.parent_id
                    and other_event.timestamp > event.timestamp
                ):
                    duration = (other_event.timestamp - event.timestamp).total_seconds()
                    return f"{duration:.3f}s"

        return ""

    def calculate_node_positions(self) -> dict[int, tuple[float, float]]:
        """Calculate positions for nodes based on hierarchy and time."""
        positions = {}

        # Build parent-child relationships
        children_map = {}
        for event in self.events:
            if event.parent_id:
                if event.parent_id not in children_map:
                    children_map[event.parent_id] = []
                children_map[event.parent_id].append(event.id)

        # Calculate depth for each node
        depths = {}

        def calculate_depth(event_id: int, current_depth: int = 0):
            depths[event_id] = max(depths.get(event_id, 0), current_depth)
            if event_id in children_map:
                for child_id in children_map[event_id]:
                    calculate_depth(child_id, current_depth + 1)

        # Start with root nodes (no parent)
        root_nodes = [e.id for e in self.events if e.parent_id is None]
        for root_id in root_nodes:
            calculate_depth(root_id, 0)

        # Position nodes
        time_range = max(e.timestamp for e in self.events) - min(
            e.timestamp for e in self.events
        )
        time_range_seconds = time_range.total_seconds() or 1  # Avoid division by zero

        start_time = min(e.timestamp for e in self.events)

        # Group events by depth level
        levels = {}
        for event_id, depth in depths.items():
            if depth not in levels:
                levels[depth] = []
            levels[depth].append(event_id)

        # Position nodes
        for event in self.events:
            event_id = event.id
            depth = depths.get(event_id, 0)

            # X position based on time
            time_offset = (event.timestamp - start_time).total_seconds()
            x = (time_offset / time_range_seconds) * 800 + 50  # Scale to 800px width

            # Y position based on depth, with some spreading within levels
            level_events = levels[depth]
            level_index = level_events.index(event_id)
            y = depth * 120 + 50 + (level_index % 3) * 30  # Spread within level

            positions[event_id] = (x, y)

        return positions

    def create_vis_network_data(self) -> tuple[list[dict], list[dict]]:
        """Create nodes and edges data for vis.js network."""
        positions = self.calculate_node_positions()

        # Group events by agent for clustering
        agent_groups = self._group_events_by_agent()

        # Create nodes
        nodes = []
        for event in self.events:
            x, y = positions[event.id]

            # Determine if this event belongs to an agent group
            group_id = agent_groups.get(event.id, None)

            node = {
                "id": event.id,
                "label": self.create_node_label(event),
                "x": x,
                "y": y,
                "physics": False,  # Fixed positions
                **self.get_event_style(event),
            }

            # Add group information for clustering
            if group_id:
                node["group"] = group_id
                node["title"] = f"Agent Group: {group_id}"  # Tooltip

            nodes.append(node)

        # Create edges with informative labels
        edges = []
        for event in self.events:
            if event.parent_id and event.parent_id in self.events_by_id:
                parent_event = self.events_by_id[event.parent_id]
                edge_label = self._create_edge_label(parent_event, event)

                # Color edges based on relationship type
                edge_color = self._get_edge_color(parent_event, event)

                edge = {
                    "from": event.parent_id,
                    "to": event.id,
                    "arrows": "to",
                    "label": edge_label,
                    "color": {"color": edge_color, "highlight": "#333333"},
                    "width": 2,
                    "smooth": {"type": "curvedCW", "roundness": 0.1},
                    "font": {"size": 10, "color": "#444444"},
                }
                edges.append(edge)

        return nodes, edges

    def _create_edge_label(
        self, parent_event: TraceEvent, child_event: TraceEvent
    ) -> str:
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

    def _get_edge_color(self, parent_event: TraceEvent, child_event: TraceEvent) -> str:
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

    def _group_events_by_agent(self) -> dict[int, str]:
        """Group events by their associated agent for clustering."""
        agent_groups = {}

        # Find agent START events and their associated events
        for event in self.events:
            if event.type == TraceType.AGENT and event.action == ActionType.START:
                agent_name = event.details.get("name", f"Agent_{event.id}")

                # Add the agent start event itself
                agent_groups[event.id] = agent_name

                # Find all child events that belong to this agent
                self._add_agent_children_to_group(event.id, agent_name, agent_groups)

        return agent_groups

    def _add_agent_children_to_group(
        self, agent_id: int, group_name: str, agent_groups: dict[int, str]
    ):
        """Recursively add all children of an agent to its group."""
        for event in self.events:
            if event.parent_id == agent_id and event.id not in agent_groups:
                # Don't group other agents' START events
                if event.type == TraceType.AGENT and event.action == ActionType.START:
                    continue

                agent_groups[event.id] = group_name
                # Recursively add children (for nested structures)
                self._add_agent_children_to_group(event.id, group_name, agent_groups)

    def render_with_pyvis(self):
        """Render flow diagram using pyvis (if available)."""
        try:
            from pyvis.network import Network
        except ImportError:
            st.error("pyvis not installed. Install with: pip install pyvis")
            return

        # Create network
        net = Network(
            height="600px",
            width="100%",
            bgcolor="#ffffff",
            font_color="black",
            directed=True,
        )

        net.set_options("""
        var options = {
          "physics": {
            "enabled": false
          },
          "interaction": {
            "dragNodes": true,
            "selectConnectedEdges": false
          }
        }
        """)

        # Add nodes and edges
        nodes, edges = self.create_vis_network_data()

        for node in nodes:
            net.add_node(
                node["id"],
                label=node["label"],
                x=node["x"],
                y=node["y"],
                color=node["color"]["background"],
                border_color=node["color"]["border"],
                shape=node["shape"],
            )

        for edge in edges:
            net.add_edge(edge["from"], edge["to"])

        # Generate HTML
        html_file = "/tmp/trace_network.html"
        net.save_graph(html_file)

        # Display in Streamlit
        with open(html_file, "r", encoding="utf-8") as f:
            html_content = f.read()

        st.components.v1.html(html_content, height=650)

    def render_with_graphviz(self):
        """Render flow diagram using Graphviz."""
        try:
            import graphviz
        except ImportError:
            st.error("graphviz not installed. Install with: pip install graphviz")
            return

        # Create directed graph
        dot = graphviz.Digraph(comment="Trace Flow")
        dot.attr(rankdir="TB", splines="ortho")

        # Add nodes
        for event in self.events:
            # Get node attributes
            shape = "box"
            if event.action == ActionType.INPUT:
                shape = "ellipse"
            elif event.action in [ActionType.REQUEST, ActionType.RESPOND]:
                shape = "circle"
            elif event.action == ActionType.PROCESS:
                shape = "diamond"

            # Get color
            colors = {
                TraceType.USER: "lightgreen",
                TraceType.AGENT: "lightblue",
                TraceType.LLM: "orange",
                TraceType.TOOL: "plum",
            }
            color = colors.get(event.type, "lightgray")

            # Create label
            label = self.create_node_label(event).replace("\\n", "\n")

            dot.node(str(event.id), label, shape=shape, style="filled", fillcolor=color)

        # Add edges with labels
        for event in self.events:
            if event.parent_id and event.parent_id in self.events_by_id:
                parent_event = self.events_by_id[event.parent_id]
                edge_label = self._create_edge_label(parent_event, event)
                edge_color = self._get_edge_color(parent_event, event)
                dot.edge(
                    str(event.parent_id),
                    str(event.id),
                    label=edge_label,
                    color=edge_color,
                )

        # Render and display
        try:
            svg_content = dot.pipe(format="svg", encoding="utf-8")
            st.image(svg_content, use_column_width=True)
        except Exception as e:
            st.error(f"Error rendering with Graphviz: {str(e)}")
            # Fallback: show the dot source
            st.code(dot.source, language="dot")

    def render_simple_diagram(self):
        """Render a simple text-based diagram."""
        st.markdown("### Flow Diagram (Text-based)")

        # Build tree structure
        children_map = {}
        for event in self.events:
            if event.parent_id:
                if event.parent_id not in children_map:
                    children_map[event.parent_id] = []
                children_map[event.parent_id].append(event.id)

        # Get icons
        icons = {
            TraceType.USER: "👤",
            TraceType.AGENT: "🤖",
            TraceType.LLM: "🧠",
            TraceType.TOOL: "🔧",
        }

        def render_tree(event_id: int, level: int = 0, is_last: bool = True):
            """Recursively render the tree."""
            event = self.events_by_id[event_id]

            # Create prefix for tree structure
            if level == 0:
                prefix = ""
            else:
                prefix = "│   " * (level - 1)
                prefix += "└── " if is_last else "├── "

            # Format timestamp
            time_str = event.timestamp.strftime("%H:%M:%S.%f")[:-3]

            # Get display name
            name = event.details.get("name", "")
            label = event.details.get("label", "")
            function = event.details.get("function", "")
            display_name = name or label or function or ""

            # Create line
            icon = icons.get(event.type, "📍")
            line = f"{prefix}{icon} **{event.type.value}** - {event.action.value}"
            if display_name:
                line += f" - *{display_name}*"
            line += f" `({time_str})`"

            st.markdown(line)

            # Render children
            if event_id in children_map:
                children = children_map[event_id]
                for i, child_id in enumerate(children):
                    is_child_last = i == len(children) - 1
                    render_tree(child_id, level + 1, is_child_last)

        # Render root nodes
        root_nodes = [e.id for e in self.events if e.parent_id is None]
        for i, root_id in enumerate(root_nodes):
            if i > 0:
                st.markdown("---")
            render_tree(root_id)


def render_flow_diagram(events: list[TraceEvent]):
    """Render flow diagram with multiple visualization options."""
    if not events:
        st.warning("No events to visualize")
        return

    st.markdown("### 🌊 Flow Diagram")

    # Visualization options
    viz_option = st.selectbox(
        "Choose visualization method:",
        ["Simple Text Tree", "Graphviz", "Interactive Network (pyvis)"],
        help="Different methods for visualizing the trace flow",
    )

    renderer = FlowDiagramRenderer(events)

    if viz_option == "Simple Text Tree":
        renderer.render_simple_diagram()
    elif viz_option == "Graphviz":
        renderer.render_with_graphviz()
    elif viz_option == "Interactive Network (pyvis)":
        renderer.render_with_pyvis()

    # Show legend
    with st.expander("🏷️ Legend"):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Event Types:**")
            st.markdown("👤 User - User interactions")
            st.markdown("🤖 Agent - AI agent operations")
            st.markdown("🧠 LLM - Language model calls")
            st.markdown("🔧 Tool - Tool/function calls")

        with col2:
            st.markdown("**Actions:**")
            st.markdown("• **Input** - User input events")
            st.markdown("• **Start/End** - Agent lifecycle")
            st.markdown("• **Process** - Processing steps")
            st.markdown("• **Request/Respond** - LLM interactions")
            st.markdown("• **Call** - Tool invocations")
