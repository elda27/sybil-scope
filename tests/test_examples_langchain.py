"""Tests for LangChain example utilities.

These tests focus on validating the prompt construction used by the ReAct agent
to avoid runtime errors like AttributeError: 'str' object has no attribute 'input_variables'.
"""

import os

import pytest


@pytest.mark.skipif(
    not os.environ.get("RUN_LANGCHAIN_EXAMPLE_TESTS"),
    reason="Optional: set RUN_LANGCHAIN_EXAMPLE_TESTS=1 to run LangChain example tests",
)
def test_build_react_prompt_has_required_variables():
    # Import from example module
    from examples.langchain_integration import build_react_prompt

    prompt = build_react_prompt()

    # Required input variables for create_react_agent
    for var in ("input", "tools", "tool_names"):
        assert var in prompt.input_variables, f"Missing input var: {var}"

    # Ensure agent_scratchpad variable exists in the prompt inputs
    assert "agent_scratchpad" in prompt.input_variables


@pytest.mark.skipif(
    not os.environ.get("RUN_LANGCHAIN_EXAMPLE_TESTS"),
    reason="Optional: set RUN_LANGCHAIN_EXAMPLE_TESTS=1 to run LangChain example tests",
)
def test_can_construct_agent_without_running():
    """Smoke test that we can construct the agent with the prompt and tools.

    Does not call the LLM or require API keys.
    """
    try:
        from langchain.agents import AgentExecutor, create_react_agent
        from langchain_core.tools import tool
        from langchain_openai import ChatOpenAI
    except Exception:
        pytest.skip("LangChain packages not installed")

    from examples.langchain_integration import build_react_prompt

    @tool
    def echo(text: str) -> str:
        """Echo the provided text."""
        return text

    tools = [echo]
    prompt = build_react_prompt()

    # Should not raise
    llm = ChatOpenAI(temperature=0)  # won't be invoked
    agent = create_react_agent(llm, tools, prompt)
    AgentExecutor(agent=agent, tools=tools)  # construct executor as smoke
