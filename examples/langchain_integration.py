"""
Example of using Sibyl Scope with LangChain (v0.3+ APIs).
"""

import os

from sybil_scope import Tracer
from sybil_scope.integrations.langchain import SibylScopeCallbackHandler

# Check if langchain is available
try:
    # Modern LC imports
    from langchain.agents import AgentExecutor, create_react_agent
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
    from langchain_core.tools import tool
    from langchain_openai import ChatOpenAI

    LANGCHAIN_AVAILABLE = True
except Exception:
    LANGCHAIN_AVAILABLE = False
    print(
        "LangChain v0.3+ not installed. Install with: pip install langchain langchain-openai"
    )


def example_langchain_simple_chain():
    """Demonstrate tracing a simple LangChain chain."""
    if not LANGCHAIN_AVAILABLE:
        print("Skipping LangChain example - not installed")
        return

    # Create tracer and callback
    tracer = Tracer()  # default FileBackend now writes to traces/ folder
    callback = SibylScopeCallbackHandler(tracer)

    # Create a simple chain (Runnable)
    llm = ChatOpenAI(temperature=0.7, callbacks=[callback])
    prompt = PromptTemplate(
        input_variables=["topic"], template="Write a short poem about {topic}."
    )
    chain = prompt | llm | StrOutputParser()

    # Run the chain
    result = chain.invoke({"topic": "artificial intelligence"})
    print(f"Result: {result}")

    # Flush traces
    tracer.flush()
    print(f"Traces saved to: {tracer.backend.filepath}")


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
    if not LANGCHAIN_AVAILABLE:
        print("Skipping LangChain agent example - not installed")
        return

    # Create tracer and callback
    tracer = Tracer()
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


def example_langchain_custom_chain():
    """Demonstrate tracing a custom multi-step chain."""
    if not LANGCHAIN_AVAILABLE:
        print("Skipping custom chain example - not installed")
        return

    # Using sequential execution for clarity in this example

    # Create tracer and callback
    tracer = Tracer()
    callback = SibylScopeCallbackHandler(tracer)

    # Create LLM
    llm = ChatOpenAI(temperature=0.7, callbacks=[callback])

    # Chain 1: Generate outline
    outline_prompt = PromptTemplate(
        input_variables=["topic"],
        template="Create an outline for a blog post about {topic}. List 3 main points.",
    )
    outline_chain = outline_prompt | llm | StrOutputParser()

    # Chain 2: Write introduction
    intro_prompt = PromptTemplate(
        input_variables=["topic", "outline"],
        template="Write an introduction for a blog post about {topic} based on this outline:\n{outline}",
    )
    intro_chain = intro_prompt | llm | StrOutputParser()

    # Chain 3: Generate summary
    summary_prompt = PromptTemplate(
        input_variables=["outline", "introduction"],
        template="Create a 2-sentence summary based on:\nOutline: {outline}\nIntro: {introduction}",
    )
    summary_chain = summary_prompt | llm | StrOutputParser()

    # Combine chains
    # Wire chains: first compute outline, then intro/summary in parallel
    def make_intro_inputs(inputs):
        return {"topic": inputs["topic"], "outline": inputs["outline"]}

    def make_summary_inputs(inputs):
        return {"outline": inputs["outline"], "introduction": inputs["introduction"]}

    # Step 1
    def step1(inputs):
        outline = outline_chain.invoke({"topic": inputs["topic"]})
        return {"topic": inputs["topic"], "outline": outline}

    # Step 2: compute intro then summary

    # Log user request
    tracer.log("user", "input", message="Write about machine learning")

    # Run the chain
    # Execute
    step1_out = step1({"topic": "machine learning"})
    intro_text = intro_chain.invoke(make_intro_inputs(step1_out))
    summary_text = summary_chain.invoke(
        {"outline": step1_out["outline"], "introduction": intro_text}
    )

    print("Outline:", step1_out["outline"])
    print("\nIntroduction:", intro_text)
    print("\nSummary:", summary_text)

    # Flush traces
    tracer.flush()
    print(f"\nTraces saved to: {tracer.backend.filepath}")


if __name__ == "__main__":
    # Note: These examples require OpenAI API key to be set
    # export OPENAI_API_KEY="your-key-here"

    if not os.getenv("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY not set. Examples will fail.")
        print("Set it as an environment variable before running.")

    print("=== Example 1: Simple Chain ===")
    example_langchain_simple_chain()
    print("\n" + "=" * 50 + "\n")

    print("=== Example 2: Agent with Tools ===")
    example_langchain_agent()
    print("\n" + "=" * 50 + "\n")

    print("=== Example 3: Custom Multi-Step Chain ===")
    example_langchain_custom_chain()
