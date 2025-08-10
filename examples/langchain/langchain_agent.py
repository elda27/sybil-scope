"""
LangChain agent with tools example.
Demonstrates tracing ReAct agents with tool usage.
"""

import os

from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

import sybil_scope as ss
from sybil_scope.integrations.langchain import SibylScopeCallbackHandler


def build_react_prompt() -> ChatPromptTemplate:
    """Build a ChatPromptTemplate compatible with create_react_agent.

    The prompt must include the input variables: "input", "tools", "tool_names",
    and a MessagesPlaceholder named "agent_scratchpad".
    """
    instructions = (
        "You are a helpful assistant. Use tools to answer questions.\n\n"
        "You have access to the following tools:\n{tools}\n\n"
        "The available tool names are: {tool_names}.\n\n"
        "When you need to use a tool, follow EXACTLY this format:\n\n"
        "Thought: think about what to do next\n"
        "Action: the action to take, one of [{tool_names}]\n"
        "Action Input: the input to the action (as JSON or plain text appropriate for the tool)\n"
        "Observation: the result of the action\n"
        "... (you can repeat Thought/Action/Action Input/Observation multiple times)\n"
        "Thought: I now know the final answer\n"
        "Final Answer: the final answer to the original input question\n"
    )

    return ChatPromptTemplate.from_messages(
        [
            ("system", instructions),
            ("human", "{input}"),
            # String scratchpad that accumulates prior Thoughts/Actions/Observations
            ("assistant", "{agent_scratchpad}"),
        ]
    )


def example_langchain_agent():
    """Demonstrate tracing a LangChain agent with tools."""

    # Create tracer and callback
    tracer = ss.Tracer()
    callback = SibylScopeCallbackHandler(tracer)

    # Create custom tools
    @tool
    def weather(location: str) -> str:
        """Get weather for a location."""
        return f"The weather in {location} is sunny and 22°C"

    @tool
    def news(topic: str) -> str:
        """Get news about a topic."""
        return f"Latest news about {topic}: Major breakthrough announced"

    tools = [weather, news]

    # Create a ReAct agent
    llm = ChatOpenAI(temperature=0, callbacks=[callback])
    react_prompt = build_react_prompt()
    agent = create_react_agent(llm, tools, react_prompt)
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        callbacks=[callback],
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=3,
    )

    # Log user input
    tracer.log("user", "input", message="What's the weather in Tokyo and any AI news?")

    # Run agent
    result = agent_executor.invoke(
        {
            "input": "What's the weather in Tokyo and are there any recent AI news?",
            # Start with empty scratchpad string for first turn
            "agent_scratchpad": "",
        }
    )
    print(f"Agent result: {result.get('output', result)}")

    # Flush traces
    tracer.flush()
    print(f"Traces saved to: {tracer.backend.filepath}")


if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY not set. Examples will fail.")
        print("Set it as an environment variable before running.")
        exit(1)

    print("=== LangChain Agent with Tools Example ===")
    with ss.option_context((ss.ConfigKey.TRACING_FILE_PREFIX, "lc_agent")):
        example_langchain_agent()
