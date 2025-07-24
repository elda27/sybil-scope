"""
Example of using Sibyl Scope with LangChain.
"""
import os
from sybil_scope import Tracer
from sybil_scope.integrations.langchain import SibylScopeCallbackHandler

# Check if langchain is available
try:
    from langchain.agents import AgentType, initialize_agent, load_tools
    from langchain.llms import OpenAI
    from langchain.chat_models import ChatOpenAI
    from langchain.chains import LLMChain
    from langchain.prompts import PromptTemplate
    from langchain.tools import Tool
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    print("LangChain not installed. Install with: pip install langchain langchain-openai")


def example_langchain_simple_chain():
    """Demonstrate tracing a simple LangChain chain."""
    if not LANGCHAIN_AVAILABLE:
        print("Skipping LangChain example - not installed")
        return
    
    # Create tracer and callback
    tracer = Tracer()
    callback = SibylScopeCallbackHandler(tracer)
    
    # Create a simple chain
    llm = OpenAI(temperature=0.7, callbacks=[callback])
    prompt = PromptTemplate(
        input_variables=["topic"],
        template="Write a short poem about {topic}."
    )
    chain = LLMChain(llm=llm, prompt=prompt, callbacks=[callback])
    
    # Run the chain
    result = chain.run(topic="artificial intelligence")
    print(f"Result: {result}")
    
    # Flush traces
    tracer.flush()
    print(f"Traces saved to: {tracer.backend.filepath}")


def example_langchain_agent():
    """Demonstrate tracing a LangChain agent with tools."""
    if not LANGCHAIN_AVAILABLE:
        print("Skipping LangChain agent example - not installed")
        return
    
    # Create tracer and callback
    tracer = Tracer()
    callback = SibylScopeCallbackHandler(tracer)
    
    # Create custom tools
    def weather_tool(location: str) -> str:
        """Get weather for a location."""
        # Simulate weather API
        return f"The weather in {location} is sunny and 22°C"
    
    def news_tool(topic: str) -> str:
        """Get news about a topic."""
        # Simulate news API
        return f"Latest news about {topic}: Major breakthrough announced"
    
    tools = [
        Tool(
            name="Weather",
            func=weather_tool,
            description="Get current weather for a location"
        ),
        Tool(
            name="News", 
            func=news_tool,
            description="Get latest news about a topic"
        )
    ]
    
    # Create agent
    llm = ChatOpenAI(temperature=0, callbacks=[callback])
    agent = initialize_agent(
        tools, 
        llm, 
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        callbacks=[callback],
        verbose=True
    )
    
    # Log user input
    tracer.log("user", "input", message="What's the weather in Tokyo and any AI news?")
    
    # Run agent
    result = agent.run("What's the weather in Tokyo and are there any recent AI news?")
    print(f"Agent result: {result}")
    
    # Flush traces
    tracer.flush()
    print(f"Traces saved to: {tracer.backend.filepath}")


def example_langchain_custom_chain():
    """Demonstrate tracing a custom multi-step chain."""
    if not LANGCHAIN_AVAILABLE:
        print("Skipping custom chain example - not installed")
        return
        
    from langchain.chains import SequentialChain
    
    # Create tracer and callback
    tracer = Tracer()
    callback = SibylScopeCallbackHandler(tracer)
    
    # Create LLM
    llm = ChatOpenAI(temperature=0.7, callbacks=[callback])
    
    # Chain 1: Generate outline
    outline_prompt = PromptTemplate(
        input_variables=["topic"],
        template="Create an outline for a blog post about {topic}. List 3 main points."
    )
    outline_chain = LLMChain(
        llm=llm, 
        prompt=outline_prompt,
        output_key="outline",
        callbacks=[callback]
    )
    
    # Chain 2: Write introduction
    intro_prompt = PromptTemplate(
        input_variables=["topic", "outline"],
        template="Write an introduction for a blog post about {topic} based on this outline:\n{outline}"
    )
    intro_chain = LLMChain(
        llm=llm,
        prompt=intro_prompt, 
        output_key="introduction",
        callbacks=[callback]
    )
    
    # Chain 3: Generate summary
    summary_prompt = PromptTemplate(
        input_variables=["outline", "introduction"],
        template="Create a 2-sentence summary based on:\nOutline: {outline}\nIntro: {introduction}"
    )
    summary_chain = LLMChain(
        llm=llm,
        prompt=summary_prompt,
        output_key="summary",
        callbacks=[callback]
    )
    
    # Combine chains
    overall_chain = SequentialChain(
        chains=[outline_chain, intro_chain, summary_chain],
        input_variables=["topic"],
        output_variables=["outline", "introduction", "summary"],
        callbacks=[callback]
    )
    
    # Log user request
    tracer.log("user", "input", message="Write about machine learning")
    
    # Run the chain
    result = overall_chain({"topic": "machine learning"})
    
    print("Outline:", result["outline"])
    print("\nIntroduction:", result["introduction"])
    print("\nSummary:", result["summary"])
    
    # Flush traces
    tracer.flush()
    print(f"\nTraces saved to: {tracer.backend.filepath}")


if __name__ == "__main__":
    # Note: These examples require OpenAI API key to be set
    # export OPENAI_API_KEY="your-key-here"
    
    if not os.getenv("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY not set. Examples will fail.")
        print("Set it with: export OPENAI_API_KEY='your-key-here'")
    
    print("=== Example 1: Simple Chain ===")
    example_langchain_simple_chain()
    print("\n" + "="*50 + "\n")
    
    print("=== Example 2: Agent with Tools ===") 
    example_langchain_agent()
    print("\n" + "="*50 + "\n")
    
    print("=== Example 3: Custom Multi-Step Chain ===")
    example_langchain_custom_chain()