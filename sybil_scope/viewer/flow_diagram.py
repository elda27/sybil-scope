"""
Flow diagram visualization using Streamlit components.
"""
import streamlit as st
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json

from sybil_scope.core import TraceEvent, TraceType, ActionType


class FlowDiagramRenderer:
    """Renders trace events as interactive flow diagrams."""
    
    def __init__(self, events: List[TraceEvent]):
        self.events = events
        self.events_by_id = {e.id: e for e in events}
        
    def get_event_style(self, event: TraceEvent) -> Dict[str, Any]:
        """Get style configuration for an event node."""
        colors = {
            TraceType.USER: {"bg": "#E8F5E8", "border": "#4CAF50", "text": "#2E7D32"},
            TraceType.AGENT: {"bg": "#E3F2FD", "border": "#2196F3", "text": "#1565C0"},
            TraceType.LLM: {"bg": "#FFF3E0", "border": "#FF9800", "text": "#E65100"},
            TraceType.TOOL: {"bg": "#F3E5F5", "border": "#9C27B0", "text": "#6A1B9A"}
        }
        
        color_scheme = colors.get(event.type, {"bg": "#F5F5F5", "border": "#757575", "text": "#424242"})
        
        # Different shapes based on action
        shapes = {
            ActionType.INPUT: "ellipse",
            ActionType.START: "box",
            ActionType.END: "box",
            ActionType.PROCESS: "diamond",
            ActionType.REQUEST: "circle",
            ActionType.RESPOND: "circle",
            ActionType.CALL: "triangle"
        }
        
        return {
            "color": {
                "background": color_scheme["bg"],
                "border": color_scheme["border"],
                "highlight": {
                    "background": color_scheme["bg"],
                    "border": color_scheme["border"]
                }
            },
            "font": {"color": color_scheme["text"], "size": 12},
            "shape": shapes.get(event.action, "box"),
            "borderWidth": 2,
            "borderWidthSelected": 3
        }
    
    def create_node_label(self, event: TraceEvent) -> str:
        """Create a label for the node."""
        # Get event type icon
        icons = {
            TraceType.USER: "👤",
            TraceType.AGENT: "🤖", 
            TraceType.LLM: "🧠",
            TraceType.TOOL: "🔧"
        }
        
        icon = icons.get(event.type, "📍")
        
        # Get name/label from details
        name = event.details.get("name", "")
        label = event.details.get("label", "")
        function = event.details.get("function", "")
        
        display_name = name or label or function or event.action.value
        
        # Truncate long names
        if len(display_name) > 20:
            display_name = display_name[:17] + "..."
        
        return f"{icon} {display_name}\\n{event.type.value}"
    
    def calculate_node_positions(self) -> Dict[int, Tuple[float, float]]:
        """Calculate positions for nodes based on hierarchy and time."""
        positions = {}
        
        # Sort events by timestamp
        sorted_events = sorted(self.events, key=lambda e: e.timestamp)
        
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
        time_range = max(e.timestamp for e in self.events) - min(e.timestamp for e in self.events)
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
    
    def create_vis_network_data(self) -> Tuple[List[Dict], List[Dict]]:
        """Create nodes and edges data for vis.js network."""
        positions = self.calculate_node_positions()
        
        # Create nodes
        nodes = []
        for event in self.events:
            x, y = positions[event.id]
            
            node = {
                "id": event.id,
                "label": self.create_node_label(event),
                "x": x,
                "y": y,
                "physics": False,  # Fixed positions
                **self.get_event_style(event)
            }
            nodes.append(node)
        
        # Create edges
        edges = []
        for event in self.events:
            if event.parent_id and event.parent_id in self.events_by_id:
                edge = {
                    "from": event.parent_id,
                    "to": event.id,
                    "arrows": "to",
                    "color": {"color": "#666666", "highlight": "#333333"},
                    "width": 2,
                    "smooth": {"type": "curvedCW", "roundness": 0.1}
                }
                edges.append(edge)
        
        return nodes, edges
    
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
            directed=True
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
                shape=node["shape"]
            )
        
        for edge in edges:
            net.add_edge(edge["from"], edge["to"])
        
        # Generate HTML
        html_file = "/tmp/trace_network.html"
        net.save_graph(html_file)
        
        # Display in Streamlit
        with open(html_file, 'r', encoding='utf-8') as f:
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
        dot = graphviz.Digraph(comment='Trace Flow')
        dot.attr(rankdir='TB', splines='ortho')
        
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
                TraceType.TOOL: "plum"
            }
            color = colors.get(event.type, "lightgray")
            
            # Create label
            label = self.create_node_label(event).replace("\\n", "\n")
            
            dot.node(
                str(event.id),
                label,
                shape=shape,
                style="filled",
                fillcolor=color
            )
        
        # Add edges
        for event in self.events:
            if event.parent_id and event.parent_id in self.events_by_id:
                dot.edge(str(event.parent_id), str(event.id))
        
        # Render and display
        try:
            svg_content = dot.pipe(format='svg', encoding='utf-8')
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
            TraceType.TOOL: "🔧"
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
                    is_child_last = (i == len(children) - 1)
                    render_tree(child_id, level + 1, is_child_last)
        
        # Render root nodes
        root_nodes = [e.id for e in self.events if e.parent_id is None]
        for i, root_id in enumerate(root_nodes):
            if i > 0:
                st.markdown("---")
            render_tree(root_id)


def render_flow_diagram(events: List[TraceEvent]):
    """Render flow diagram with multiple visualization options."""
    if not events:
        st.warning("No events to visualize")
        return
    
    st.markdown("### 🌊 Flow Diagram")
    
    # Visualization options
    viz_option = st.selectbox(
        "Choose visualization method:",
        ["Simple Text Tree", "Graphviz", "Interactive Network (pyvis)"],
        help="Different methods for visualizing the trace flow"
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