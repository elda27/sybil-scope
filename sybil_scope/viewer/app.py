"""
Streamlit application for visualizing Sibyl Scope trace data.
"""

import json
from datetime import datetime
from pathlib import Path

import pandas as pd  # type: ignore  # pyright: ignore[reportMissingTypeStubs]
import streamlit as st

from sybil_scope.backend import FileBackend
from sybil_scope.core import ActionType, TraceEvent, TraceType
from sybil_scope.viewer.common import (
    EventStyleHelper,
    TimeHelper,
    TreeStructureBuilder,
    VizOption,
)
from sybil_scope.viewer.flow_diagram import render_flow_diagram
from sybil_scope.viewer.hierarchical_view import render_hierarchical_view
from sybil_scope.viewer.table_view import render_table_view
from sybil_scope.viewer.timeline import render_timeline_visualization

# Page configuration
st.set_page_config(
    page_title="Sibyl Scope Viewer",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)


def load_trace_data(filepath: Path) -> list[TraceEvent]:
    """Load trace data from JSONL file."""
    backend = FileBackend(filepath=filepath)
    return backend.load()


def get_event_color(event_type: TraceType) -> str:
    """Get color for event type."""
    return EventStyleHelper.get_event_color(event_type)


def get_event_icon(event_type: TraceType) -> str:
    """Get icon for event type."""
    return EventStyleHelper.get_event_icon(event_type)


def format_timestamp(ts: datetime) -> str:
    """Format timestamp for display."""
    return TimeHelper.format_timestamp(ts)


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


## Timeline view is implemented in sybil_scope.viewer.timeline as render_timeline_visualization


def render_statistics_view(events: list[TraceEvent]):
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

    # Find paired start/end or request/response events
    pairs = []

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
                events = [
                    TraceEvent(**json.loads(line)) for line in lines if line.strip()
                ]

                st.success(f"Loaded {len(events)} events")

        else:  # File Path option
            file_path = st.text_input(
                "Enter file path:",
                # value="traces_20250724_142712.jsonl",
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

            # Visualization selection (Enum-based)
            viz_options: list[VizOption] = st.multiselect(
                "Select Visualizations:",
                options=list(VizOption),
                default=list(VizOption),
                format_func=lambda v: v.value,
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
        # Build corrected tree structure for hierarchical view
        tree = TreeStructureBuilder.build_corrected_tree_structure(events)

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
            # Dictionary-based dispatch for render functions
            render_functions = {
                VizOption.STATISTICS: lambda: render_statistics_view(events),
                VizOption.HIERARCHICAL: lambda: render_hierarchical_view(events, tree),
                VizOption.TIMELINE: lambda: render_timeline_visualization(events),
                VizOption.FLOW_DIAGRAM: lambda: render_flow_diagram(events),
                VizOption.TABLE_VIEW: lambda: render_table_view(events),
            }

            # Create tabs for selected visualizations
            if len(viz_options) > 1:
                selected_tabs = st.tabs([opt.value for opt in viz_options])

                for i, viz_option in enumerate(viz_options):
                    with selected_tabs[i]:
                        render_functions[viz_option]()
            else:
                # Single visualization, no tabs needed
                viz_option = viz_options[0]
                render_functions[viz_option]()

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
