"""
LangGraph agent example.
Demonstrates tracing LangGraph workflows with tool calling.
"""

import os
from typing import TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

import sybil_scope as ss
from sybil_scope.integrations.langchain import SibylScopeCallbackHandler


def example_langgraph_custom_chain():
    """A minimal LangGraph agent with two tools (weather, news), similar in spirit
    to example_langchain_agent but implemented with tool-calling in a small graph.
    """
    # Tracer + callback
    tracer = ss.Tracer()
    callback = SibylScopeCallbackHandler(tracer)

    # Tools (same behavior as the LangChain agent example)
    @tool
    def weather(location: str) -> str:
        """Get weather for a location."""
        return f"The weather in {location} is sunny and 22°C"

    @tool
    def news(topic: str) -> str:
        """Get news about a topic."""
        return f"Latest news about {topic}: Major breakthrough announced"

    tools = [weather, news]

    # Bind tools to the model so it can emit tool_calls
    base_llm = ChatOpenAI(temperature=0)
    model = base_llm.bind_tools(tools)

    # State for the agent
    class AgentState(TypedDict):
        messages: list

    def agent_node(state: AgentState, config=None):
        resp = model.invoke(state["messages"], config=config)
        return {"messages": [resp]}

    tools_node = ToolNode(tools)

    def should_continue(state: AgentState):
        last = state["messages"][-1]
        tool_calls = getattr(last, "tool_calls", None)
        if tool_calls:
            return "tools"
        return END

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tools_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    app = graph.compile()

    # User question
    question = "What's the weather in Tokyo and are there any recent AI news?"
    tracer.log("user", "input", message=question)

    system = SystemMessage(
        content=(
            "You are a helpful assistant. Use tools when needed. "
            "Available tools: weather(location), news(topic)."
        )
    )
    human = HumanMessage(content=question)

    result = app.invoke(
        {"messages": [system, human]},
        config={"callbacks": [callback]},
    )

    # Find the final AI message
    final_ai = None
    for m in reversed(result["messages"]):
        if isinstance(m, AIMessage):
            final_ai = m
            break

    print(f"Agent result: {final_ai.content if final_ai else result}")
    tracer.flush()
    print(f"Traces saved to: {tracer.backend.filepath}")


if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY not set. Examples will fail.")
        print("Set it as an environment variable before running.")
        exit(1)

    print("=== LangGraph Agent Example ===")
    with ss.option_context((ss.ConfigKey.TRACING_FILE_PREFIX, "lg_agent")):
        example_langgraph_custom_chain()
