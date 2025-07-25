"""
Streamlit application for visualizing Sibyl Scope trace data.
"""

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

from sybil_scope.backend import FileBackend
from sybil_scope.core import ActionType, TraceEvent, TraceType
from sybil_scope.viewer.flow_diagram import render_flow_diagram
from sybil_scope.viewer.table_view import render_table_view
from sybil_scope.viewer.timeline import render_timeline_visualization

# Page configuration
st.set_page_config(
    page_title="Sibyl Scope Viewer",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)


def load_trace_data(filepath: Path) -> List[TraceEvent]:
    """Load trace data from JSONL file."""
    backend = FileBackend(filepath=filepath)
    return backend.load()


def build_tree_structure(
    events: List[TraceEvent],
) -> Dict[Optional[int], List[TraceEvent]]:
    """Build parent-child tree structure from events."""
    tree = defaultdict(list)
    for event in events:
        tree[event.parent_id].append(event)
    return tree


def get_event_color(event_type: TraceType) -> str:
    """Get color for event type."""
    colors = {
        TraceType.USER: "#4CAF50",  # Green
        TraceType.AGENT: "#2196F3",  # Blue
        TraceType.LLM: "#FF9800",  # Orange
        TraceType.TOOL: "#9C27B0",  # Purple
    }
    return colors.get(event_type, "#757575")


def get_event_icon(event_type: TraceType) -> str:
    """Get icon for event type."""
    icons = {
        TraceType.USER: "👤",
        TraceType.AGENT: "🤖",
        TraceType.LLM: "🧠",
        TraceType.TOOL: "🔧",
    }
    return icons.get(event_type, "📍")


def format_timestamp(ts: datetime) -> str:
    """Format timestamp for display."""
    return ts.strftime("%H:%M:%S.%f")[:-3]


def render_event_details(event: TraceEvent):
    """Render detailed view of an event."""
    st.markdown(f"### {get_event_icon(event.type)} Event Details")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Basic Info:**")
        st.text(f"ID: {event.id}")
        st.text(f"Type: {event.type.value}")
        st.text(f"Action: {event.action.value}")
        st.text(f"Timestamp: {format_timestamp(event.timestamp)}")
        if event.parent_id:
            st.text(f"Parent ID: {event.parent_id}")

    with col2:
        if event.details:
            st.markdown("**Details:**")
            # Pretty print details
            details_json = json.dumps(event.details, indent=2)
            st.code(details_json, language="json")


def render_hierarchical_view(
    events: List[TraceEvent], tree: Dict[Optional[int], List[TraceEvent]]
):
    """Render hierarchical tree view of events according to ARCHITECTURE.md specifications."""
    st.markdown("### 🌳 Hierarchical View")

    def find_paired_events(events_list: List[TraceEvent]) -> Dict[int, TraceEvent]:
        """Find request/respond and call/respond pairs for LLM and Tool events."""
        pairs = {}
        for event in events_list:
            # LLM request/respond pairs
            if event.action == ActionType.REQUEST and event.type == TraceType.LLM:
                for potential_respond in events_list:
                    if (potential_respond.action == ActionType.RESPOND and 
                        potential_respond.type == TraceType.LLM and
                        potential_respond.parent_id == event.id):
                        pairs[event.id] = potential_respond
                        break
            # Tool call/respond pairs
            elif event.action == ActionType.CALL and event.type == TraceType.TOOL:
                for potential_respond in events_list:
                    if (potential_respond.action == ActionType.RESPOND and 
                        potential_respond.type == TraceType.TOOL and
                        potential_respond.parent_id == event.id):
                        pairs[event.id] = potential_respond
                        break
        return pairs

    def calculate_duration(start_event: TraceEvent, end_event: TraceEvent = None) -> str:
        """Calculate duration between two events."""
        if end_event:
            duration = (end_event.timestamp - start_event.timestamp).total_seconds()
            return f"{duration:.3f}s"
        else:
            # For agent events, try to find corresponding end event
            if start_event.type == TraceType.AGENT and start_event.action == ActionType.START:
                # Find agent end with same parent
                for potential_end in events:
                    if (potential_end.type == TraceType.AGENT and 
                        potential_end.action == ActionType.END and
                        potential_end.parent_id == start_event.parent_id and
                        potential_end.id != start_event.id):
                        duration = (potential_end.timestamp - start_event.timestamp).total_seconds()
                        return f"{duration:.3f}s"
            # If no end event, calculate from children
            children = tree.get(start_event.id, [])
            if children:
                latest_child = max(children, key=lambda x: x.timestamp)
                duration = (latest_child.timestamp - start_event.timestamp).total_seconds()
                return f"{duration:.3f}s"
            return "0.000s"

    def format_args_for_display(args: dict, max_length: int = 50) -> str:
        """Format arguments dict for display in expander label."""
        if not args:
            return ""
        arg_parts = []
        for key, value in args.items():
            if key not in ["kwargs", "args", "_type"] and value:
                if isinstance(value, list):
                    if len(value) > 0 and isinstance(value[0], str):
                        # For lists, show first element
                        str_val = str(value[0])[:max_length] + ("..." if len(str(value[0])) > max_length else "")
                    else:
                        str_val = str(value)[:max_length] + ("..." if len(str(value)) > max_length else "")
                else:
                    str_val = str(value)[:max_length] + ("..." if len(str(value)) > max_length else "")
                arg_parts.append(f"{key}: {str_val}")
        return ", ".join(arg_parts[:2])  # Show only first 2 args

    def format_result_for_display(result: any, error: str = None) -> str:
        """Format result or error for display in expander label."""
        if error:
            return f"❌error: {error[:50]}..." if len(error) > 50 else f"❌error: {error}"
        
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

    def render_node(event: TraceEvent, level: int = 0, skip_ids: set = None):
        """Recursively render a node and its children."""
        if skip_ids is None:
            skip_ids = set()
            
        if event.id in skip_ids:
            return
            
        indent = "　" * level  # Japanese space for better alignment
        
        # Check if this event has a pair (request/respond or call/respond)
        pairs = find_paired_events(events)
        paired_event = pairs.get(event.id)
        
        if paired_event:
            # This is a paired event - render as single expander
            skip_ids.add(paired_event.id)
            
            # Build label based on event type
            if event.type == TraceType.LLM:
                # Extract prompt from request
                prompt_text = ""
                args = event.details.get("args", {})
                if isinstance(args, dict):
                    prompts = args.get("prompts", [])
                    if prompts and isinstance(prompts, list) and len(prompts) > 0:
                        prompt_text = prompts[0][:100] + ("..." if len(prompts[0]) > 100 else "")
                    else:
                        prompt_text = args.get("prompt", "")[:100] + ("..." if len(args.get("prompt", "")) > 100 else "")
                
                # Extract response
                response_text = paired_event.details.get("response", "")[:100]
                if len(paired_event.details.get("response", "")) > 100:
                    response_text += "..."
                
                duration = calculate_duration(event, paired_event)
                
                label = f"{indent}{get_event_icon(event.type)} {event.type.value}"
                if prompt_text:
                    label += f" | 📝prompt: \"{prompt_text}\""
                if response_text:
                    label += f" | 📝respond: {response_text}"
                label += f" | ({duration})"
                
            elif event.type == TraceType.TOOL:
                # Tool call/respond pair
                tool_name = event.details.get("name", "")
                args_text = format_args_for_display(event.details.get("args", {}))
                
                # Check for error or result in respond
                error = paired_event.details.get("error", "")
                result = paired_event.details.get("result", "")
                result_text = format_result_for_display(result, error)
                
                duration = calculate_duration(event, paired_event)
                
                label = f"{indent}{get_event_icon(event.type)} {event.type.value}"
                if tool_name:
                    label += f" | name: {tool_name}"
                if args_text:
                    label += f" | 📝args: {args_text}"
                if result_text:
                    label += f" | {'📝result' if not error else ''}: {result_text}"
                label += f" | ({duration})"
            
            # Create expander for paired event
            with st.expander(label, expanded=level < 2):
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    if event.type == TraceType.LLM:
                        st.markdown(f"**Request ID:** `{event.id}`")
                        st.markdown(f"**Respond ID:** `{paired_event.id}`")
                    else:  # Tool
                        st.markdown(f"**Call ID:** `{event.id}`")
                        st.markdown(f"**Respond ID:** `{paired_event.id}`")
                    
                    if event.parent_id:
                        st.markdown(f"**Parent:** `{event.parent_id}`")
                    
                    # Model info for LLM
                    if event.type == TraceType.LLM:
                        model = event.details.get("model", "")
                        if model:
                            st.markdown(f"**model:** {model}")
                    
                    # Tool name
                    if event.type == TraceType.TOOL:
                        tool_name = event.details.get("name", "")
                        if tool_name:
                            st.markdown(f"**Tool name:** {tool_name}")
                
                with col2:
                    # Show full details
                    if event.type == TraceType.LLM:
                        args = event.details.get("args", {})
                        if args:
                            st.markdown("**Args:**")
                            # Show important LLM parameters
                            for key in ["temperature", "max_tokens", "model_name"]:
                                if key in args:
                                    st.text(f"  {key}: {args[key]}")
                        
                        st.markdown("**Response:**")
                        st.text(paired_event.details.get("response", "")[:500])
                        
                        # Show token usage if available
                        llm_output = paired_event.details.get("llm_output", {})
                        if llm_output:
                            st.markdown("**LLM Output:**")
                            st.json(llm_output)
                    
                    elif event.type == TraceType.TOOL:
                        # Show args
                        args = event.details.get("args", {})
                        if args:
                            st.markdown("**Args:**")
                            st.json(args)
                        
                        # Show result or error
                        error = paired_event.details.get("error", "")
                        if error:
                            st.markdown("**Error:**")
                            st.error(error)
                            error_type = paired_event.details.get("error_type", "")
                            if error_type:
                                st.text(f"Error Type: {error_type}")
                        else:
                            result = paired_event.details.get("result", "")
                            if result:
                                st.markdown("**Result:**")
                                if isinstance(result, (dict, list)):
                                    st.json(result)
                                else:
                                    st.text(str(result))
        
        else:
            # Regular single event (not paired)
            # Extract relevant info based on event type
            label_parts = [f"{indent}{get_event_icon(event.type)} {event.type.value}"]
            
            if event.action != ActionType.START and event.action != ActionType.END:
                label_parts.append(f"- {event.action.value}")
            
            # Add specific info based on event type
            if event.type == TraceType.USER:
                message = event.details.get("message", "")
                if message:
                    label_parts.append(f": 📝 {message[:100]}{'...' if len(message) > 100 else ''}")
                # Check if there's a response in a sibling end event
                if event.parent_id is None:  # Root user event
                    for e in events:
                        if e.type == TraceType.AGENT and e.action == ActionType.PROCESS and e.details.get("label") == "Final Response":
                            resp = e.details.get("response", {})
                            if isinstance(resp, dict) and "output" in resp:
                                label_parts.append(f"| response: {resp['output'][:50]}...")
                            break
            
            elif event.type == TraceType.AGENT:
                name = event.details.get("name", "")
                if name:
                    label_parts.append(f"| Name: {name}")
                
                if event.action == ActionType.START:
                    duration = calculate_duration(event)
                    label_parts.append(f"| ({duration})")
                elif event.action == ActionType.PROCESS:
                    label_text = event.details.get("label", "")
                    if label_text:
                        label_parts.append(f"| Label: {label_text}")
                    response = event.details.get("response", "")
                    if response:
                        if isinstance(response, dict):
                            label_parts.append(f"| response: {str(response)[:50]}...")
                        else:
                            label_parts.append(f"| response: 📝 {response[:50]}...")
            
            # Timestamp for single events
            label_parts.append(f"| ({format_timestamp(event.timestamp)})")
            
            # Create expander
            with st.expander(" ".join(label_parts), expanded=level < 2):
                st.markdown(f"**ID:** `{event.id}`")
                if event.parent_id:
                    st.markdown(f"**Parent:** `{event.parent_id}`")
                
                # Show all non-empty details
                for key, value in event.details.items():
                    if value and key not in ["args", "kwargs"] and not key.startswith("_"):
                        st.markdown(f"**{key}:**")
                        if isinstance(value, (dict, list)):
                            st.json(value)
                        else:
                            st.text(str(value))

        # Render children (skip already processed paired events)
        if event.id in tree:
            for child in tree[event.id]:
                render_node(child, level + 1, skip_ids)

    # Render root nodes
    root_events = tree[None]
    for event in root_events:
        render_node(event)


def render_timeline_view(events: List[TraceEvent]):
    """Render timeline view of events."""
    st.markdown("### 📅 Timeline View")

    if not events:
        st.warning("No events to display")
        return

    # Calculate time range
    start_time = min(e.timestamp for e in events)
    end_time = max(e.timestamp for e in events)
    total_duration = (end_time - start_time).total_seconds()

    st.markdown(f"**Total Duration:** {total_duration:.3f} seconds")

    # Create timeline data
    timeline_data = []
    for event in events:
        relative_time = (event.timestamp - start_time).total_seconds()
        timeline_data.append(
            {
                "Time (s)": f"{relative_time:.3f}",
                "Type": get_event_icon(event.type) + " " + event.type.value,
                "Action": event.action.value,
                "Label": event.details.get("label", event.details.get("name", "")),
                "ID": event.id,
                "Parent ID": event.parent_id or "",
            }
        )

    # Display as dataframe
    df = pd.DataFrame(timeline_data)

    # Add filtering options
    col1, col2 = st.columns(2)
    with col1:
        type_filter = st.multiselect(
            "Filter by Type",
            options=[t.value for t in TraceType],
            default=[t.value for t in TraceType],
        )
    with col2:
        action_filter = st.multiselect(
            "Filter by Action",
            options=[a.value for a in ActionType],
            default=[a.value for a in ActionType],
        )

    # Apply filters
    mask = df["Type"].str.contains("|".join(type_filter)) & df["Action"].isin(
        action_filter
    )
    filtered_df = df[mask]

    # Display filtered dataframe
    st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ID": st.column_config.NumberColumn(format="%d"),
            "Parent ID": st.column_config.NumberColumn(format="%d"),
        },
    )


def render_statistics_view(events: List[TraceEvent]):
    """Render statistics and metrics view."""
    st.markdown("### 📊 Statistics")

    if not events:
        st.warning("No events to analyze")
        return

    # Basic metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Events", len(events))

    with col2:
        event_types = [e.type.value for e in events]
        unique_types = len(set(event_types))
        st.metric("Event Types", unique_types)

    with col3:
        start_time = min(e.timestamp for e in events)
        end_time = max(e.timestamp for e in events)
        duration = (end_time - start_time).total_seconds()
        st.metric("Duration (s)", f"{duration:.3f}")

    with col4:
        # Count errors
        error_count = sum(1 for e in events if "error" in e.details)
        st.metric("Errors", error_count)

    # Event type distribution
    st.markdown("#### Event Type Distribution")
    type_counts = pd.Series([e.type.value for e in events]).value_counts()
    st.bar_chart(type_counts)

    # Action distribution
    st.markdown("#### Action Distribution")
    action_counts = pd.Series([e.action.value for e in events]).value_counts()
    st.bar_chart(action_counts)

    # Performance analysis for paired events
    st.markdown("#### Performance Analysis")

    # Find paired start/end or request/respond events
    pairs = []
    event_dict = {e.id: e for e in events}

    for event in events:
        if event.action in [ActionType.START, ActionType.REQUEST, ActionType.CALL]:
            # Find matching end event
            for potential_end in events:
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

    if pairs:
        perf_df = pd.DataFrame(pairs)
        perf_df = perf_df.sort_values("Duration (s)", ascending=False)

        # Show top 10 slowest operations
        st.markdown("**Top 10 Slowest Operations:**")
        st.dataframe(
            perf_df.head(10),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Duration (s)": st.column_config.NumberColumn(format="%.3f")
            },
        )

        # Average duration by type
        avg_by_type = (
            perf_df.groupby("Type")["Duration (s)"].mean().sort_values(ascending=False)
        )
        st.markdown("**Average Duration by Type:**")
        st.bar_chart(avg_by_type)


def main():
    """Main Streamlit application."""
    st.title("🔍 Sibyl Scope Viewer")
    st.markdown("Interactive visualization for AI/LLM application traces")

    # Sidebar for file selection
    with st.sidebar:
        st.header("📁 Data Source")

        # File upload or path input
        upload_option = st.radio("Choose input method:", ["Upload File", "File Path"])

        events = []

        if upload_option == "Upload File":
            uploaded_file = st.file_uploader(
                "Choose a JSONL file",
                type=["jsonl"],
                help="Upload a trace file in JSONL format",
            )

            if uploaded_file is not None:
                # Read uploaded file
                lines = uploaded_file.read().decode("utf-8").strip().split("\n")
                events = []
                for line in lines:
                    if line.strip():
                        data = json.loads(line)
                        events.append(TraceEvent(**data))

                st.success(f"Loaded {len(events)} events")

        else:  # File Path option
            file_path = st.text_input(
                "Enter file path:",
                value="traces_20250724_142712.jsonl",
                help="Path to JSONL trace file",
            )

            if st.button("Load File"):
                try:
                    path = Path(file_path)
                    if path.exists():
                        events = load_trace_data(path)
                        st.success(f"Loaded {len(events)} events from {path.name}")
                    else:
                        st.error(f"File not found: {file_path}")
                except Exception as e:
                    st.error(f"Error loading file: {str(e)}")

        # Display options
        if events:
            st.header("🎨 Display Options")

            # Visualization selection
            viz_options = st.multiselect(
                "Select Visualizations:",
                [
                    "📊 Statistics",
                    "🌳 Hierarchical",
                    "📅 Timeline",
                    "🌊 Flow Diagram",
                    "📋 Table View",
                ],
                default=["📊 Statistics", "🌳 Hierarchical"],
                help="Choose which visualization types to show",
            )

    # Main content area
    if not events:
        st.info("👈 Please load a trace file using the sidebar")

        # Show example
        with st.expander("📖 Example Usage"):
            st.markdown("""
            1. Generate trace data using Sibyl Scope:
            ```python
            from sybil_scope import Tracer
            
            tracer = Tracer()
            tracer.log("user", "input", message="Hello!")
            tracer.flush()
            ```
            
            2. Load the generated JSONL file in this viewer
            
            3. Explore your traces using different visualization modes
            """)
    else:
        # Build tree structure for hierarchical view
        tree = build_tree_structure(events)

        # Show file info
        st.info(
            f"📄 Loaded {len(events)} events | Time range: {events[0].timestamp.strftime('%H:%M:%S')} - {events[-1].timestamp.strftime('%H:%M:%S')}"
        )

        # Render selected visualizations
        if not viz_options:
            st.warning(
                "👈 Please select at least one visualization type from the sidebar"
            )
        else:
            # Create tabs for selected visualizations
            if len(viz_options) > 1:
                selected_tabs = st.tabs(viz_options)

                for i, viz_option in enumerate(viz_options):
                    with selected_tabs[i]:
                        if viz_option == "📊 Statistics":
                            render_statistics_view(events)
                        elif viz_option == "🌳 Hierarchical":
                            render_hierarchical_view(events, tree)
                        elif viz_option == "📅 Timeline":
                            render_timeline_visualization(events)
                        elif viz_option == "🌊 Flow Diagram":
                            render_flow_diagram(events)
                        elif viz_option == "📋 Table View":
                            render_table_view(events)
            else:
                # Single visualization, no tabs needed
                viz_option = viz_options[0]
                if viz_option == "📊 Statistics":
                    render_statistics_view(events)
                elif viz_option == "🌳 Hierarchical":
                    render_hierarchical_view(events, tree)
                elif viz_option == "📅 Timeline":
                    render_timeline_visualization(events)
                elif viz_option == "🌊 Flow Diagram":
                    render_flow_diagram(events)
                elif viz_option == "📋 Table View":
                    render_table_view(events)

        # Event details viewer (in sidebar)
        with st.sidebar:
            st.header("🔎 Event Inspector")
            event_id = st.number_input(
                "Enter Event ID:",
                min_value=0,
                value=0,
                step=1,
                help="Enter an event ID to view its details",
            )

            if st.button("View Event"):
                event = next((e for e in events if e.id == event_id), None)
                if event:
                    render_event_details(event)
                else:
                    st.error(f"Event with ID {event_id} not found")


if __name__ == "__main__":
    main()
