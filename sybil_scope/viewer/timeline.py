"""
Interactive timeline visualization for trace events.
"""

from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from sybil_scope.core import ActionType, TraceEvent, TraceType
from sybil_scope.viewer.common import EventStyleHelper


class TimelineRenderer:
    """Renders trace events as interactive timeline visualizations."""

    def __init__(self, events: list[TraceEvent]):
        self.events = sorted(events, key=lambda e: e.timestamp)
        self.start_time = min(e.timestamp for e in events) if events else datetime.now()
        self.end_time = max(e.timestamp for e in events) if events else datetime.now()

    def get_event_color(self, event_type: TraceType) -> str:
        """Get color for event type."""
        return EventStyleHelper.get_event_color(event_type)

    def create_gantt_data(self) -> pd.DataFrame:
        """Create data for Gantt chart visualization."""
        gantt_data = []

        # Find paired events (start/end, request/respond, call/respond)
        event_pairs = {}

        for event in self.events:
            if event.action in [ActionType.START, ActionType.REQUEST, ActionType.CALL]:
                event_pairs[event.id] = {"start": event, "end": None, "duration": None}

        # Find matching end events
        for event in self.events:
            if event.action in [ActionType.END, ActionType.RESPOND]:
                if event.parent_id and event.parent_id in event_pairs:
                    pair = event_pairs[event.parent_id]
                    pair["end"] = event
                    pair["duration"] = (
                        event.timestamp - pair["start"].timestamp
                    ).total_seconds()

        # Create gantt entries for paired events
        for event_id, pair in event_pairs.items():
            start_event = pair["start"]
            end_event = pair["end"]

            if end_event:
                # Get display name
                name = start_event.details.get("name", "")
                label = start_event.details.get("label", "")
                function = start_event.details.get("function", "")
                model = start_event.details.get("model", "")

                display_name = (
                    name
                    or label
                    or function
                    or model
                    or f"{start_event.type.value}_{start_event.action.value}"
                )

                gantt_data.append(
                    {
                        "Task": display_name,
                        "Start": start_event.timestamp,
                        "Finish": end_event.timestamp,
                        "Duration": pair["duration"],
                        "Type": start_event.type.value,
                        "Resource": f"{start_event.type.value}",
                        "ID": start_event.id,
                        "Parent_ID": start_event.parent_id,
                    }
                )

        # Add single events as instant markers
        single_events = [
            e
            for e in self.events
            if e.action
            not in [
                ActionType.START,
                ActionType.REQUEST,
                ActionType.CALL,
                ActionType.END,
                ActionType.RESPOND,
            ]
        ]

        for event in single_events:
            name = event.details.get("name", "")
            label = event.details.get("label", "")
            function = event.details.get("function", "")

            display_name = (
                name or label or function or f"{event.type.value}_{event.action.value}"
            )

            # Create a very short duration for visualization
            end_time = event.timestamp + timedelta(milliseconds=10)

            gantt_data.append(
                {
                    "Task": display_name,
                    "Start": event.timestamp,
                    "Finish": end_time,
                    "Duration": 0.01,
                    "Type": event.type.value,
                    "Resource": f"{event.type.value}",
                    "ID": event.id,
                    "Parent_ID": event.parent_id,
                }
            )

        return pd.DataFrame(gantt_data)

    def render_gantt_chart(self):
        """Render Gantt chart timeline."""
        st.markdown("#### 📊 Gantt Chart View")

        df = self.create_gantt_data()

        if df.empty:
            st.warning("No paired events found for Gantt chart")
            return

        # Create Gantt chart using Plotly
        fig = px.timeline(
            df,
            x_start="Start",
            x_end="Finish",
            y="Task",
            color="Type",
            hover_data=["Duration", "ID"],
            title="Trace Timeline (Gantt Chart)",
            color_discrete_map={
                "user": "#4CAF50",
                "agent": "#2196F3",
                "llm": "#FF9800",
                "tool": "#9C27B0",
            },
        )

        fig.update_yaxes(autorange="reversed")  # Top to bottom
        fig.update_layout(
            height=max(400, len(df) * 30),
            xaxis_title="Time",
            yaxis_title="Operations",
            showlegend=True,
        )

        st.plotly_chart(fig, use_container_width=True)

        # Show data table
        if st.checkbox("Show Gantt data"):
            st.dataframe(
                df[["Task", "Type", "Duration", "ID", "Parent_ID"]],
                use_container_width=True,
            )

    def render_scatter_timeline(self):
        """Render scatter plot timeline."""
        st.markdown("#### 📍 Event Scatter Plot")

        # Prepare data
        timeline_data = []
        for i, event in enumerate(self.events):
            relative_time = (event.timestamp - self.start_time).total_seconds()

            # Get display info
            name = event.details.get("name", "")
            label = event.details.get("label", "")
            function = event.details.get("function", "")

            display_name = name or label or function or event.action.value

            timeline_data.append(
                {
                    "Time": relative_time,
                    "Y": i,  # Vertical position
                    "Type": event.type.value,
                    "Action": event.action.value,
                    "Name": display_name,
                    "ID": event.id,
                    "Parent_ID": event.parent_id or "",
                    "Timestamp": event.timestamp.strftime("%H:%M:%S.%f")[:-3],
                }
            )

        df = pd.DataFrame(timeline_data)

        # Create scatter plot
        fig = px.scatter(
            df,
            x="Time",
            y="Y",
            color="Type",
            symbol="Action",
            hover_data=["Name", "ID", "Timestamp"],
            title="Event Timeline (Scatter Plot)",
            labels={"Time": "Time (seconds)", "Y": "Event Sequence"},
            color_discrete_map={
                "user": "#4CAF50",
                "agent": "#2196F3",
                "llm": "#FF9800",
                "tool": "#9C27B0",
            },
        )

        fig.update_layout(
            height=500,
            showlegend=True,
            yaxis=dict(showticklabels=False),  # Hide Y-axis labels
        )

        # Add lines connecting parent-child events
        for _, row in df.iterrows():
            if row["Parent_ID"]:
                parent_row = df[df["ID"] == row["Parent_ID"]]
                if not parent_row.empty:
                    parent_data = parent_row.iloc[0]
                    fig.add_shape(
                        type="line",
                        x0=parent_data["Time"],
                        y0=parent_data["Y"],
                        x1=row["Time"],
                        y1=row["Y"],
                        line=dict(color="gray", width=1, dash="dot"),
                    )

        st.plotly_chart(fig, use_container_width=True)

    def render_swimlane_timeline(self):
        """Render swimlane timeline by event type."""
        st.markdown("#### 🏊 Swimlane Timeline")

        # Create subplots for each event type
        event_types = list(set(e.type for e in self.events))
        fig = make_subplots(
            rows=len(event_types),
            cols=1,
            subplot_titles=[f"{et.value.title()} Events" for et in event_types],
            shared_xaxes=True,
            vertical_spacing=0.1,
        )

        colors = {
            TraceType.USER: "#4CAF50",
            TraceType.AGENT: "#2196F3",
            TraceType.LLM: "#FF9800",
            TraceType.TOOL: "#9C27B0",
        }

        for i, event_type in enumerate(event_types, 1):
            type_events = [e for e in self.events if e.type == event_type]

            times = [
                (e.timestamp - self.start_time).total_seconds() for e in type_events
            ]
            actions = [e.action.value for e in type_events]

            # Add scatter trace
            fig.add_trace(
                go.Scatter(
                    x=times,
                    y=[1] * len(times),  # All at same Y level
                    mode="markers+text",
                    marker=dict(
                        color=colors.get(event_type, "#757575"),
                        size=10,
                        symbol="circle",
                    ),
                    text=actions,
                    textposition="top center",
                    name=event_type.value,
                    hovertemplate=f"<b>{event_type.value}</b><br>"
                    + "Action: %{text}<br>"
                    + "Time: %{x:.3f}s<br>"
                    + "<extra></extra>",
                    showlegend=(i == 1),  # Only show legend for first trace
                ),
                row=i,
                col=1,
            )

            # Update Y-axis for this subplot
            fig.update_yaxes(showticklabels=False, range=[0.5, 1.5], row=i, col=1)

        fig.update_xaxes(title_text="Time (seconds)", row=len(event_types), col=1)
        fig.update_layout(
            height=150 * len(event_types),
            title_text="Events by Type (Swimlanes)",
            showlegend=False,
        )

        st.plotly_chart(fig, use_container_width=True)

    def render_performance_timeline(self):
        """Render performance-focused timeline showing durations."""
        st.markdown("#### ⏱️ Performance Timeline")

        # Calculate durations for paired events
        performance_data = []

        for event in self.events:
            if event.action in [ActionType.START, ActionType.REQUEST, ActionType.CALL]:
                # Find matching end event
                end_events = [
                    e
                    for e in self.events
                    if e.parent_id == event.id
                    and e.action in [ActionType.END, ActionType.RESPOND]
                ]

                if end_events:
                    end_event = end_events[0]
                    duration = (end_event.timestamp - event.timestamp).total_seconds()

                    name = event.details.get("name", "")
                    label = event.details.get("label", "")
                    function = event.details.get("function", "")
                    model = event.details.get("model", "")

                    display_name = (
                        name or label or function or model or f"{event.type.value}"
                    )

                    performance_data.append(
                        {
                            "Operation": display_name,
                            "Type": event.type.value,
                            "Duration": duration,
                            "Start_Time": (
                                event.timestamp - self.start_time
                            ).total_seconds(),
                            "ID": event.id,
                        }
                    )

        if not performance_data:
            st.warning("No performance data available (no paired events found)")
            return

        df = pd.DataFrame(performance_data)

        # Create horizontal bar chart showing durations
        fig = px.bar(
            df.sort_values("Duration", ascending=True),
            x="Duration",
            y="Operation",
            color="Type",
            orientation="h",
            title="Operation Durations",
            labels={"Duration": "Duration (seconds)"},
            color_discrete_map={
                "user": "#4CAF50",
                "agent": "#2196F3",
                "llm": "#FF9800",
                "tool": "#9C27B0",
            },
        )

        fig.update_layout(height=max(400, len(df) * 25))
        st.plotly_chart(fig, use_container_width=True)

        # Show statistics
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Average Duration", f"{df['Duration'].mean():.3f}s")
        with col2:
            st.metric("Max Duration", f"{df['Duration'].max():.3f}s")
        with col3:
            st.metric("Total Operations", len(df))

        # Show detailed data
        if st.checkbox("Show performance data"):
            st.dataframe(
                df.sort_values("Duration", ascending=False),
                use_container_width=True,
                column_config={
                    "Duration": st.column_config.NumberColumn(format="%.3f s"),
                    "Start_Time": st.column_config.NumberColumn(format="%.3f s"),
                },
            )


def render_timeline_visualization(events: list[TraceEvent]):
    """Render timeline visualization with multiple view options."""
    if not events:
        st.warning("No events to visualize")
        return

    st.markdown("### ⏰ Timeline Visualization")

    renderer = TimelineRenderer(events)

    # Timeline options
    timeline_tabs = st.tabs(
        ["📊 Gantt Chart", "📍 Scatter Plot", "🏊 Swimlanes", "⏱️ Performance"]
    )

    with timeline_tabs[0]:
        renderer.render_gantt_chart()

    with timeline_tabs[1]:
        renderer.render_scatter_timeline()

    with timeline_tabs[2]:
        renderer.render_swimlane_timeline()

    with timeline_tabs[3]:
        renderer.render_performance_timeline()

    # Timeline statistics
    with st.expander("📈 Timeline Statistics"):
        total_duration = (renderer.end_time - renderer.start_time).total_seconds()
        st.metric("Total Timeline Duration", f"{total_duration:.3f} seconds")

        # Event counts by type
        type_counts = {}
        for event in events:
            type_counts[event.type.value] = type_counts.get(event.type.value, 0) + 1

        st.markdown("**Event Counts by Type:**")
        for event_type, count in type_counts.items():
            st.text(f"{event_type}: {count}")

        # Event rate
        event_rate = len(events) / total_duration if total_duration > 0 else 0
        st.metric("Event Rate", f"{event_rate:.2f} events/second")
