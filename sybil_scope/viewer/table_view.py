"""
Expandable table view for trace events.
"""

import json
from datetime import datetime

import pandas as pd
import streamlit as st

from sybil_scope.core import ActionType, TraceEvent, TraceType
from sybil_scope.viewer.common import (
    EventStyleHelper,
    TimeHelper,
)


class TableRenderer:
    """Renders trace events as expandable hierarchical tables."""

    def __init__(self, events: list[TraceEvent]):
        self.events = events
        self.events_by_id = {e.id: e for e in events}

        # Build parent-child relationships
        self.children_map = {}
        self.parent_map = {}

        for event in events:
            if event.parent_id:
                if event.parent_id not in self.children_map:
                    self.children_map[event.parent_id] = []
                self.children_map[event.parent_id].append(event.id)
                self.parent_map[event.id] = event.parent_id

    def get_event_icon(self, event_type: TraceType) -> str:
        """Get icon for event type."""
        return EventStyleHelper.get_event_icon(event_type)

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

    def format_timestamp(self, ts: datetime) -> str:
        """Format timestamp for display."""
        return TimeHelper.format_timestamp(ts)

    def get_event_duration(self, event: TraceEvent) -> float | None:
        """Get duration for events that have corresponding end events."""
        if event.action in [ActionType.START, ActionType.REQUEST, ActionType.CALL]:
            # Find matching end event
            if event.id in self.children_map:
                for child_id in self.children_map[event.id]:
                    child = self.events_by_id[child_id]
                    if child.action in [ActionType.END, ActionType.RESPOND]:
                        return (child.timestamp - event.timestamp).total_seconds()
        return None

    def prepare_table_data(self) -> pd.DataFrame:
        """Prepare data for hierarchical table view."""
        table_data = []

        for event in sorted(self.events, key=lambda e: e.timestamp):
            depth = self.calculate_depth(event.id)
            duration = self.get_event_duration(event)

            # Get important details
            name = event.details.get("name", "")
            label = event.details.get("label", "")
            function = event.details.get("function", "")
            model = event.details.get("model", "")

            # Get error info
            error = event.details.get("error", "")

            # Get response/result info
            response = event.details.get("response", "")
            result = event.details.get("result", "")

            # Truncate long text
            def truncate_text(text, max_length=50):
                if isinstance(text, str) and len(text) > max_length:
                    return text[:max_length] + "..."
                return str(text) if text else ""

            table_data.append(
                {
                    "ID": event.id,
                    "Depth": depth,
                    "Icon": self.get_event_icon(event.type),
                    "Type": event.type.value,
                    "Action": event.action.value,
                    "Name/Label": name or label or function or model or "",
                    "Timestamp": self.format_timestamp(event.timestamp),
                    "Duration (s)": f"{duration:.3f}" if duration else "",
                    "Parent ID": event.parent_id or "",
                    "Response": truncate_text(response or result),
                    "Error": truncate_text(error),
                    "Details Count": len(event.details),
                    "_event": event,  # Store original event for details
                }
            )

        return pd.DataFrame(table_data)

    def render_flat_table(self):
        """Render flat table view with all events."""
        st.markdown("#### 📋 Flat Table View")

        df = self.prepare_table_data()

        # Filtering options
        col1, col2, col3 = st.columns(3)

        with col1:
            type_filter = st.multiselect(
                "Filter by Type",
                options=list(set(df["Type"])),
                default=list(set(df["Type"])),
                key="flat_type_filter",
            )

        with col2:
            action_filter = st.multiselect(
                "Filter by Action",
                options=list(set(df["Action"])),
                default=list(set(df["Action"])),
                key="flat_action_filter",
            )

        with col3:
            depth_filter = st.select_slider(
                "Max Depth",
                options=list(range(max(df["Depth"]) + 1)),
                value=max(df["Depth"]),
                key="flat_depth_filter",
            )

        # Apply filters
        filtered_df = df[
            (df["Type"].isin(type_filter))
            & (df["Action"].isin(action_filter))
            & (df["Depth"] <= depth_filter)
        ]

        # Display table
        display_columns = [
            "Icon",
            "Type",
            "Action",
            "Name/Label",
            "Timestamp",
            "Duration (s)",
            "Parent ID",
            "Response",
            "Error",
        ]

        st.dataframe(
            filtered_df[display_columns],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Icon": st.column_config.TextColumn(width="small"),
                "Type": st.column_config.TextColumn(width="small"),
                "Action": st.column_config.TextColumn(width="small"),
                "Duration (s)": st.column_config.TextColumn(width="small"),
                "Parent ID": st.column_config.NumberColumn(format="%d", width="small"),
            },
        )

        st.caption(f"Showing {len(filtered_df)} of {len(df)} events")

    def render_hierarchical_table(self):
        """Render hierarchical table with expandable rows."""
        st.markdown("#### 🌳 Hierarchical Table View")

        # Use session state to track expanded rows
        if "expanded_rows" not in st.session_state:
            st.session_state.expanded_rows = set()

        def render_tree_table(event_id: int, level: int = 0):
            """Recursively render hierarchical table rows."""
            event = self.events_by_id[event_id]
            indent = "　" * level  # Japanese space for better alignment

            # Calculate duration
            duration = self.get_event_duration(event)

            # Get display info
            name = event.details.get("name", "")
            label = event.details.get("label", "")
            function = event.details.get("function", "")
            display_name = name or label or function or ""

            # Check if this event has children
            has_children = event_id in self.children_map

            # Create row
            col1, col2, col3, col4, col5, col6, col7 = st.columns([1, 3, 2, 2, 3, 2, 2])

            with col1:
                if has_children:
                    # Expandable button
                    is_expanded = event_id in st.session_state.expanded_rows
                    expand_button = st.button(
                        "▼" if is_expanded else "▶",
                        key=f"expand_{event_id}",
                        help="Click to expand/collapse",
                    )
                    if expand_button:
                        if is_expanded:
                            st.session_state.expanded_rows.remove(event_id)
                        else:
                            st.session_state.expanded_rows.add(event_id)
                        st.rerun()
                else:
                    st.write("　")  # Empty space

            with col2:
                st.write(f"{indent}{self.get_event_icon(event.type)} {display_name}")

            with col3:
                st.write(f"{event.type.value}")

            with col4:
                st.write(f"{event.action.value}")

            with col5:
                st.write(self.format_timestamp(event.timestamp))

            with col6:
                if duration:
                    st.write(f"{duration:.3f}s")
                else:
                    st.write("-")

            with col7:
                # Details button
                if st.button(
                    "Details", key=f"details_{event_id}", help="View event details"
                ):
                    st.session_state.selected_event = event_id

            # Show children if expanded
            if has_children and event_id in st.session_state.expanded_rows:
                for child_id in self.children_map[event_id]:
                    render_tree_table(child_id, level + 1)

        # Table header
        st.markdown("**Hierarchical Event Table**")
        col1, col2, col3, col4, col5, col6, col7 = st.columns([1, 3, 2, 2, 3, 2, 2])

        with col1:
            st.write("**Toggle**")
        with col2:
            st.write("**Event**")
        with col3:
            st.write("**Type**")
        with col4:
            st.write("**Action**")
        with col5:
            st.write("**Timestamp**")
        with col6:
            st.write("**Duration**")
        with col7:
            st.write("**Actions**")

        st.divider()

        # Render root events
        root_events = [e.id for e in self.events if e.parent_id is None]
        for root_id in root_events:
            render_tree_table(root_id)

        # Show selected event details
        if hasattr(st.session_state, "selected_event"):
            event_id = st.session_state.selected_event
            if event_id in self.events_by_id:
                event = self.events_by_id[event_id]
                self.render_event_details_modal(event)

    def render_event_details_modal(self, event: TraceEvent):
        """Render detailed view of a selected event."""
        with st.expander(f"📋 Event Details - ID: {event.id}", expanded=True):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Basic Information:**")
                st.text(f"ID: {event.id}")
                st.text(f"Type: {self.get_event_icon(event.type)} {event.type.value}")
                st.text(f"Action: {event.action.value}")
                st.text(f"Timestamp: {event.timestamp}")
                if event.parent_id:
                    st.text(f"Parent ID: {event.parent_id}")

                # Calculate and show depth
                depth = self.calculate_depth(event.id)
                st.text(f"Hierarchy Depth: {depth}")

                # Show duration if available
                duration = self.get_event_duration(event)
                if duration:
                    st.text(f"Duration: {duration:.3f} seconds")

            with col2:
                st.markdown("**Event Details:**")
                if event.details:
                    # Pretty print details
                    details_json = json.dumps(event.details, indent=2, default=str)
                    st.code(details_json, language="json")
                else:
                    st.text("No additional details")

            # Show child events if any
            if event.id in self.children_map:
                st.markdown("**Child Events:**")
                children = self.children_map[event.id]
                child_data = []

                for child_id in children:
                    child = self.events_by_id[child_id]
                    child_data.append(
                        {
                            "ID": child.id,
                            "Type": f"{self.get_event_icon(child.type)} {child.type.value}",
                            "Action": child.action.value,
                            "Timestamp": self.format_timestamp(child.timestamp),
                        }
                    )

                if child_data:
                    st.dataframe(
                        pd.DataFrame(child_data),
                        use_container_width=True,
                        hide_index=True,
                    )

    def render_summary_statistics(self):
        """Render summary statistics table."""
        st.markdown("#### 📊 Summary Statistics")

        # Event type statistics
        type_stats = {}
        for event in self.events:
            event_type = event.type.value
            if event_type not in type_stats:
                type_stats[event_type] = {
                    "count": 0,
                    "actions": set(),
                    "avg_depth": [],
                    "has_errors": 0,
                }

            type_stats[event_type]["count"] += 1
            type_stats[event_type]["actions"].add(event.action.value)
            type_stats[event_type]["avg_depth"].append(self.calculate_depth(event.id))

            if "error" in event.details:
                type_stats[event_type]["has_errors"] += 1

        # Create summary table
        summary_data = []
        for event_type, stats in type_stats.items():
            icon = self.get_event_icon(TraceType(event_type))
            avg_depth = (
                sum(stats["avg_depth"]) / len(stats["avg_depth"])
                if stats["avg_depth"]
                else 0
            )

            summary_data.append(
                {
                    "Type": f"{icon} {event_type}",
                    "Count": stats["count"],
                    "Unique Actions": len(stats["actions"]),
                    "Actions": ", ".join(sorted(stats["actions"])),
                    "Avg Depth": f"{avg_depth:.1f}",
                    "Errors": stats["has_errors"],
                    "Error Rate": f"{(stats['has_errors'] / stats['count'] * 100):.1f}%"
                    if stats["count"] > 0
                    else "0%",
                }
            )

        summary_df = pd.DataFrame(summary_data)
        st.dataframe(
            summary_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Count": st.column_config.NumberColumn(format="%d"),
                "Unique Actions": st.column_config.NumberColumn(format="%d"),
                "Errors": st.column_config.NumberColumn(format="%d"),
            },
        )

        # Hierarchy statistics
        st.markdown("**Hierarchy Statistics:**")
        max_depth = max((self.calculate_depth(e.id) for e in self.events), default=0)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Max Depth", max_depth)
        with col2:
            root_count = len([e for e in self.events if e.parent_id is None])
            st.metric("Root Events", root_count)
        with col3:
            leaf_count = len([e for e in self.events if e.id not in self.children_map])
            st.metric("Leaf Events", leaf_count)


def render_table_view(events: list[TraceEvent]):
    """Render table views with multiple options."""
    if not events:
        st.warning("No events to display in table")
        return

    st.markdown("### 📊 Table View")

    renderer = TableRenderer(events)

    # Table view options
    table_tabs = st.tabs(["📋 Flat Table", "🌳 Hierarchical", "📊 Statistics"])

    with table_tabs[0]:
        renderer.render_flat_table()

    with table_tabs[1]:
        renderer.render_hierarchical_table()

    with table_tabs[2]:
        renderer.render_summary_statistics()

    # Export options
    with st.expander("💾 Export Options"):
        df = renderer.prepare_table_data()

        col1, col2 = st.columns(2)

        with col1:
            # CSV export
            csv_data = df.drop(columns=["_event"]).to_csv(index=False)
            st.download_button(
                label="📄 Download as CSV",
                data=csv_data,
                file_name="trace_events.csv",
                mime="text/csv",
            )

        with col2:
            # JSON export
            json_data = []
            for event in events:
                json_data.append(event.model_dump())

            json_str = json.dumps(json_data, indent=2, default=str)
            st.download_button(
                label="📝 Download as JSON",
                data=json_str,
                file_name="trace_events.json",
                mime="application/json",
            )
