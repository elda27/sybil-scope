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
    """Render hierarchical tree view of events."""
    st.markdown("### 🌳 Hierarchical View")

    def render_node(event: TraceEvent, level: int = 0):
        """Recursively render a node and its children."""
        indent = "　" * level  # Japanese space for better alignment

        # Always show message, response, result if available
        message = event.details.get("message", "")
        response = event.details.get("response", "")
        result = event.details.get("result", "")
        prompt = event.details.get("prompt", "")
        error = event.details.get("error", "")
        # Create expandable section for each node
        # Prepare input text
        input_text = ""
        if message:
            input_text = message[:100] + ("..." if len(message) > 100 else "")
        elif prompt:
            input_text = prompt[:100] + ("..." if len(prompt) > 100 else "")
        else:
            # Check in args for prompt/message (for LLM calls)
            args = event.details.get("args", {})
            if isinstance(args, dict):
                arg_message = args.get("message", "") or args.get("user_query", "") or args.get("prompt", "")
                if arg_message:
                    input_text = arg_message[:100] + ("..." if len(arg_message) > 100 else "")
        
        # Prepare output text
        output_text = ""
        if response:
            output_text = response[:100] + ("..." if len(response) > 100 else "")
        elif result and result != "":
            output_text = str(result)[:100] + ("..." if len(str(result)) > 100 else "")
        
        # Build label with input and output
        label_parts = [
            f"{indent}{get_event_icon(event.type)} {event.type.value} - {event.action.value}"
        ]
        
        if input_text:
            label_parts.append(f"📝 {input_text}")
        
        if output_text:
            label_parts.append(f"output: 📝 {output_text}")
        
        label_parts.append(f"({format_timestamp(event.timestamp)})")
        
        with st.expander(
            " | ".join(label_parts),
            expanded=level < 2,  # Expand first two levels by default
        ):
            # Show event details
            col1, col2, col3 = st.columns([2, 2, 3])

            with col1:
                st.markdown(f"**ID:** `{event.id}`")
                if event.parent_id:
                    st.markdown(f"**Parent:** `{event.parent_id}`")

            with col2:
                label = event.details.get("label", "")
                if label:
                    st.markdown(f"**Label:** {label}")

                name = event.details.get("name", "")
                if name:
                    st.markdown(f"**Name:** {name}")

            with col3:
                # Also check in args for prompt/message (for LLM calls)
                args = event.details.get("args", {})
                if not prompt and isinstance(args, dict):
                    prompt = args.get("prompt", "")
                if not message and isinstance(args, dict):
                    message = args.get("message", "")
                    # Also check for user_query in args (for planning steps)
                    if not message:
                        message = args.get("user_query", "")

                # Show input message/prompt
                if message:
                    display_message = (
                        message[:100] + "..." if len(message) > 100 else message
                    )
                    st.markdown(f"**入力:** {display_message}")
                elif prompt:
                    display_prompt = (
                        prompt[:100] + "..." if len(prompt) > 100 else prompt
                    )
                    st.markdown(f"**プロンプト:** {display_prompt}")
                elif event.type == TraceType.TOOL and isinstance(args, dict):
                    # For tools, show the main argument values
                    tool_args = []
                    for key, value in args.items():
                        if key not in ["kwargs", "args"] and value:
                            str_val = (
                                str(value)[:30] + "..."
                                if len(str(value)) > 30
                                else str(value)
                            )
                            tool_args.append(f"{key}: {str_val}")
                    if tool_args:
                        st.markdown(f"**引数:** {', '.join(tool_args[:2])}")

                # Show output response/result
                if response:
                    display_response = (
                        response[:100] + "..." if len(response) > 100 else response
                    )
                    st.markdown(f"**出力:** {display_response}")
                elif result and result != "":
                    display_result = (
                        str(result)[:100] + "..."
                        if len(str(result)) > 100
                        else str(result)
                    )
                    st.markdown(f"**結果:** {display_result}")
                elif event.action == ActionType.PROCESS:
                    # For process actions, show the label or strategy if no response
                    strategy = event.details.get("strategy", "")
                    if strategy:
                        st.markdown(f"**戦略:** {strategy}")

                # Show error if present
                if error:
                    display_error = error[:100] + "..." if len(error) > 100 else error
                    st.markdown(f"**エラー:** :red[{display_error}]")

                # Show other important details if space allows
                exclude_keys = {
                    "label",
                    "name",
                    "function",
                    "args",
                    "kwargs",
                    "message",
                    "response",
                    "result",
                    "prompt",
                    "error",
                }
                other_details = {
                    k: v
                    for k, v in event.details.items()
                    if k not in exclude_keys and not k.startswith("_")
                }

                if other_details:
                    # Show up to 2 additional details
                    for key, value in list(other_details.items())[:2]:
                        if isinstance(value, str) and len(value) > 50:
                            value = value[:50] + "..."
                        st.markdown(f"**{key}:** {value}")

            # Render children
            if event.id in tree:
                for child in tree[event.id]:
                    render_node(child, level + 1)

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
