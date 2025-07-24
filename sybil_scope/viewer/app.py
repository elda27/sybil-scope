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


def merge_paired_events(events: List[TraceEvent]) -> List[Dict]:
    """Merge paired events (request/respond, call/respond, start/end) into single units."""
    # Create a mapping of events by ID
    events_by_id = {e.id: e for e in events}
    
    # Track which events have been processed
    processed = set()
    merged_events = []
    
    for event in events:
        if event.id in processed:
            continue
            
        # Look for paired events
        paired_event = None
        pair_type = None
        
        if event.action in [ActionType.REQUEST, ActionType.CALL, ActionType.START]:
            # Find corresponding respond/end event
            for potential_pair in events:
                if (potential_pair.parent_id == event.id and 
                    ((event.action == ActionType.REQUEST and potential_pair.action == ActionType.RESPOND) or
                     (event.action == ActionType.CALL and potential_pair.action == ActionType.RESPOND) or
                     (event.action == ActionType.START and potential_pair.action == ActionType.END))):
                    paired_event = potential_pair
                    pair_type = f"{event.action.value}/{potential_pair.action.value}"
                    break
        
        if paired_event:
            # Create merged event data
            merged_events.append({
                "type": "merged",
                "primary_event": event,
                "secondary_event": paired_event,
                "pair_type": pair_type,
                "level": None  # Will be set later
            })
            processed.add(event.id)
            processed.add(paired_event.id)
        else:
            # Single event
            merged_events.append({
                "type": "single",
                "primary_event": event,
                "secondary_event": None,
                "pair_type": None,
                "level": None
            })
            processed.add(event.id)
    
    return merged_events


def render_hierarchical_view(
    events: List[TraceEvent], tree: Dict[Optional[int], List[TraceEvent]]
):
    """Render hierarchical tree view of events."""
    st.markdown("### 🌳 Hierarchical View")
    
    # Merge paired events
    merged_events = merge_paired_events(events)
    
    # Rebuild tree structure with merged events
    merged_tree = {}
    for merged_item in merged_events:
        primary_event = merged_item["primary_event"]
        parent_id = primary_event.parent_id
        
        if parent_id not in merged_tree:
            merged_tree[parent_id] = []
        merged_tree[parent_id].append(merged_item)

    def render_merged_node(merged_item: Dict, level: int = 0):
        """Recursively render a merged node and its children."""
        indent = "　" * level  # Japanese space for better alignment
        
        primary_event = merged_item["primary_event"]
        secondary_event = merged_item["secondary_event"]
        is_merged = merged_item["type"] == "merged"
        
        # Extract information from both events for merged display
        if is_merged:
            # Get input from primary event (request/call/start)
            input_message = primary_event.details.get("message", "")
            input_prompt = primary_event.details.get("prompt", "")
            input_args = primary_event.details.get("args", {})
            
            if not input_prompt and isinstance(input_args, dict):
                input_prompt = input_args.get("prompt", "")
            if not input_message and isinstance(input_args, dict):
                input_message = input_args.get("message", "") or input_args.get("user_query", "")
            
            # Get output from secondary event (respond/end)
            output_response = secondary_event.details.get("response", "")
            output_result = secondary_event.details.get("result", "")
            output_error = secondary_event.details.get("error", "")
            
            # Build title for merged event
            event_icon = get_event_icon(primary_event.type)
            pair_type = merged_item["pair_type"]
            
            title_parts = [f"{indent}{event_icon} {primary_event.type.value} - {pair_type}"]
            
            # Add input info
            if input_message:
                short_input = input_message[:40] + "..." if len(input_message) > 40 else input_message
                title_parts.append(f"📝 {short_input}")
            elif input_prompt:
                short_input = input_prompt[:40] + "..." if len(input_prompt) > 40 else input_prompt
                title_parts.append(f"💭 {short_input}")
            elif primary_event.type == TraceType.TOOL and isinstance(input_args, dict):
                tool_info = []
                for key, value in input_args.items():
                    if key not in ['kwargs', 'args'] and value:
                        str_val = str(value)[:20] + "..." if len(str(value)) > 20 else str(value)
                        tool_info.append(f"{key}:{str_val}")
                if tool_info:
                    title_parts.append(f"🔧 {tool_info[0]}")
            
            # Add output info
            if output_error:
                short_error = output_error[:30] + "..." if len(output_error) > 30 else output_error
                title_parts.append(f"❌ {short_error}")
            elif output_response:
                short_output = output_response[:40] + "..." if len(output_response) > 40 else output_response
                title_parts.append(f"💬 {short_output}")
            elif output_result and str(output_result) != "":
                short_output = str(output_result)[:40] + "..." if len(str(output_result)) > 40 else str(output_result)
                title_parts.append(f"✅ {short_output}")
            
            # Add timing info
            start_time = format_timestamp(primary_event.timestamp)
            end_time = format_timestamp(secondary_event.timestamp)
            duration = (secondary_event.timestamp - primary_event.timestamp).total_seconds()
            title_parts.append(f"⏱️ {duration:.3f}s ({start_time}-{end_time})")
            
        else:
            # Single event - use original logic
            event = primary_event
            message = event.details.get("message", "")
            response = event.details.get("response", "")
            result = event.details.get("result", "")
            prompt = event.details.get("prompt", "")
            error = event.details.get("error", "")
            
            args = event.details.get("args", {})
            if not prompt and isinstance(args, dict):
                prompt = args.get("prompt", "")
            if not message and isinstance(args, dict):
                message = args.get("message", "") or args.get("user_query", "")
            
            title_parts = [f"{indent}{get_event_icon(event.type)} {event.type.value} - {event.action.value}"]
            
            if message:
                short_message = message[:40] + "..." if len(message) > 40 else message
                title_parts.append(f"📝 {short_message}")
            elif prompt:
                short_prompt = prompt[:40] + "..." if len(prompt) > 40 else prompt
                title_parts.append(f"💭 {short_prompt}")
            elif event.type == TraceType.TOOL and isinstance(args, dict):
                tool_info = []
                for key, value in args.items():
                    if key not in ['kwargs', 'args'] and value:
                        str_val = str(value)[:20] + "..." if len(str(value)) > 20 else str(value)
                        tool_info.append(f"{key}:{str_val}")
                if tool_info:
                    title_parts.append(f"🔧 {tool_info[0]}")
            
            if error:
                short_error = error[:30] + "..." if len(error) > 30 else error
                title_parts.append(f"❌ {short_error}")
            elif response:
                short_response = response[:40] + "..." if len(response) > 40 else response
                title_parts.append(f"💬 {short_response}")
            elif result and str(result) != "":
                short_result = str(result)[:40] + "..." if len(str(result)) > 40 else str(result)
                title_parts.append(f"✅ {short_result}")
            elif event.action == ActionType.PROCESS:
                strategy = event.details.get("strategy", "")
                if strategy:
                    title_parts.append(f"📋 {strategy}")
            
            title_parts.append(f"({format_timestamp(event.timestamp)})")
        
        # Create expandable section
        title = " | ".join(title_parts)
        with st.expander(title, expanded=level < 2):
            if is_merged:
                # Show merged event details
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**🚀 開始: {primary_event.action.value}**")
                    st.markdown(f"**ID:** `{primary_event.id}`")
                    st.markdown(f"**時刻:** {format_timestamp(primary_event.timestamp)}")
                    if primary_event.parent_id:
                        st.markdown(f"**親ID:** `{primary_event.parent_id}`")
                    
                    if primary_event.details:
                        st.markdown("**入力詳細:**")
                        input_details = json.dumps(primary_event.details, indent=2, ensure_ascii=False)
                        st.code(input_details, language="json")
                
                with col2:
                    st.markdown(f"**🏁 終了: {secondary_event.action.value}**")
                    st.markdown(f"**ID:** `{secondary_event.id}`")
                    st.markdown(f"**時刻:** {format_timestamp(secondary_event.timestamp)}")
                    duration = (secondary_event.timestamp - primary_event.timestamp).total_seconds()
                    st.markdown(f"**処理時間:** `{duration:.3f}秒`")
                    
                    if secondary_event.details:
                        st.markdown("**出力詳細:**")
                        output_details = json.dumps(secondary_event.details, indent=2, ensure_ascii=False)
                        st.code(output_details, language="json")
            else:
                # Show single event details (original logic)
                event = primary_event
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
                    if event.details:
                        details_json = json.dumps(event.details, indent=2)
                        st.code(details_json, language="json")
            
            # Render children
            event_id = primary_event.id
            if event_id in merged_tree:
                for child_item in merged_tree[event_id]:
                    render_merged_node(child_item, level + 1)
    
    # Render root nodes
    root_merged_items = merged_tree.get(None, [])
    for merged_item in root_merged_items:
        render_merged_node(merged_item)


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
