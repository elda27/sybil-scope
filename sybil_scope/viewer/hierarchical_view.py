"""
Hierarchical view for visualizing Sibyl Scope trace data as an interactive tree.
"""

import streamlit as st

from sybil_scope.core import ActionType, TraceEvent, TraceType
from sybil_scope.viewer.common import (
    EventPairHelper,
    EventStyleHelper,
    TextFormatter,
    TimeHelper,
    TraceEventTree,
)


def render_hierarchical_view(events: list[TraceEvent], tree: TraceEventTree):
    """Render hierarchical tree view of events according to ARCHITECTURE.md specifications."""
    st.markdown("### 🌳 Hierarchical View")

    if not events:
        st.warning("No events to display")
        return

    # Initialize helpers
    pair_helper = EventPairHelper(events)
    pairs = pair_helper.find_paired_events()
    agent_pairs = pair_helper.find_agent_start_end_pairs()

    def render_node(event: TraceEvent, level: int = 0, skip_ids: set = None):
        """Recursively render a node and its children."""
        if skip_ids is None:
            skip_ids = set()

        if event.id in skip_ids:
            return

        indent = "　" * level  # Japanese space for better alignment

        # Check if this event has a pair (request/response or call/response)
        paired_event = pairs.get(event.id)

        if paired_event:
            # This is a paired event - render as single expander
            skip_ids.add(paired_event.id)
            _render_paired_event(event, paired_event, indent, level, agent_pairs)
        else:
            # Regular single event (not paired)
            _render_single_event(event, indent, level, events, agent_pairs)

        # Render children (skip already processed paired events)
        if event.id in tree:
            for child in tree[event.id]:
                render_node(child, level + 1, skip_ids)

    # Render root nodes
    root_events = tree[None]
    for event in root_events:
        render_node(event)


def _render_paired_event(
    event: TraceEvent,
    paired_event: TraceEvent,
    indent: str,
    level: int,
    agent_pairs: dict[int, int],
):
    """Render a paired event (request/response or call/response)."""
    # Build label based on event type
    if event.type == TraceType.LLM:
        label = _build_llm_pair_label(event, paired_event, indent, agent_pairs)
    elif event.type == TraceType.TOOL:
        label = _build_tool_pair_label(event, paired_event, indent, agent_pairs)
    else:
        label = (
            f"{indent}{EventStyleHelper.get_event_icon(event.type)} {event.type.value}"
        )

    # Create expander for paired event
    with st.expander(label, expanded=level < 2):
        _render_paired_event_details(event, paired_event)


def _render_single_event(
    event: TraceEvent,
    indent: str,
    level: int,
    events: list[TraceEvent],
    agent_pairs: dict[int, int],
):
    """Render a single (non-paired) event."""
    # Extract relevant info based on event type
    label_parts = [
        f"{indent}{EventStyleHelper.get_event_icon(event.type)} {event.type.value}"
    ]

    if event.action != ActionType.START and event.action != ActionType.END:
        label_parts.append(f"- {event.action.value}")

    # Add specific info based on event type
    if event.type == TraceType.USER:
        _add_user_event_info(event, label_parts, events)
    elif event.type == TraceType.AGENT:
        _add_agent_event_info(event, label_parts, agent_pairs)

    # Timestamp for single events
    label_parts.append(f"| ({TimeHelper.format_timestamp(event.timestamp)})")

    # Create expander
    with st.expander(" ".join(label_parts), expanded=level < 2):
        _render_single_event_details(event)


def _build_llm_pair_label(
    event: TraceEvent,
    paired_event: TraceEvent,
    indent: str,
    agent_pairs: dict[int, int],
) -> str:
    """Build label for LLM request/response pair."""
    # Extract prompt from request
    prompt_text = ""
    args = event.details.get("args", {})
    if isinstance(args, dict):
        prompts = args.get("prompts", [])
        if prompts and isinstance(prompts, list) and len(prompts) > 0:
            prompt_text = prompts[0][:100] + ("..." if len(prompts[0]) > 100 else "")
        else:
            prompt_text = args.get("prompt", "")[:100] + (
                "..." if len(args.get("prompt", "")) > 100 else ""
            )

    # Extract response
    response_text = paired_event.details.get("response", "")[:100]
    if len(paired_event.details.get("response", "")) > 100:
        response_text += "..."

    duration = TimeHelper.calculate_duration(
        event, paired_event, agent_pairs=agent_pairs
    )

    label = f"{indent}{EventStyleHelper.get_event_icon(event.type)} {event.type.value}"
    if prompt_text:
        label += f' | 📝prompt: "{prompt_text}"'
    if response_text:
        label += f" | 📝response: {response_text}"
    label += f" | ({duration})"

    return label


def _build_tool_pair_label(
    event: TraceEvent,
    paired_event: TraceEvent,
    indent: str,
    agent_pairs: dict[int, int],
) -> str:
    """Build label for Tool call/response pair."""
    tool_name = event.details.get("name", "")
    args_text = TextFormatter.format_args_for_display(event.details.get("args", {}))

    # Check for error or result in response
    error = paired_event.details.get("error", "")
    result = paired_event.details.get("result", "")
    result_text = TextFormatter.format_result_for_display(result, error)

    duration = TimeHelper.calculate_duration(
        event, paired_event, agent_pairs=agent_pairs
    )

    label = f"{indent}{EventStyleHelper.get_event_icon(event.type)} {event.type.value}"
    if tool_name:
        label += f" | name: {tool_name}"
    if args_text:
        label += f" | 📝args: {args_text}"
    if result_text:
        label += f" | {'📝result' if not error else ''}: {result_text}"
    label += f" | ({duration})"

    return label


def _add_user_event_info(
    event: TraceEvent, label_parts: list[str], events: list[TraceEvent]
):
    """Add user event specific information to label."""
    message = event.details.get("message", "")
    if message:
        label_parts.append(f": 📝 {message[:100]}{'...' if len(message) > 100 else ''}")

    # Check if there's a response in a sibling end event
    if event.parent_id is None:  # Root user event
        for e in events:
            if (
                e.type == TraceType.AGENT
                and e.action == ActionType.PROCESS
                and e.details.get("label") == "Final Response"
            ):
                resp = e.details.get("response", {})
                if isinstance(resp, dict) and "output" in resp:
                    label_parts.append(f"| response: {resp['output'][:50]}...")
                break


def _add_agent_event_info(
    event: TraceEvent, label_parts: list[str], agent_pairs: dict[int, int]
):
    """Add agent event specific information to label."""
    name = event.details.get("name", "")
    if name:
        label_parts.append(f"| Name: {name}")

    if event.action == ActionType.START:
        duration = TimeHelper.calculate_duration(event, None, agent_pairs=agent_pairs)
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


def _render_paired_event_details(event: TraceEvent, paired_event: TraceEvent):
    """Render details for a paired event."""
    col1, col2 = st.columns([1, 1])

    with col1:
        if event.type == TraceType.LLM:
            st.markdown(f"**Request ID:** `{event.id}`")
            st.markdown(f"**Response ID:** `{paired_event.id}`")
        else:  # Tool
            st.markdown(f"**Call ID:** `{event.id}`")
            st.markdown(f"**Response ID:** `{paired_event.id}`")

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
            _render_llm_details(event, paired_event)
        elif event.type == TraceType.TOOL:
            _render_tool_details(event, paired_event)


def _render_llm_details(event: TraceEvent, paired_event: TraceEvent):
    """Render LLM-specific details."""
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


def _render_tool_details(event: TraceEvent, paired_event: TraceEvent):
    """Render Tool-specific details."""
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


def _render_single_event_details(event: TraceEvent):
    """Render details for a single event."""
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
