"""
Basic usage example of Sibyl Scope tracing library.
"""
import time
from sybil_scope import (
    Tracer, TraceType, ActionType,
    trace_function, trace_llm, trace_tool,
    set_global_tracer
)


# Example 1: Basic tracing with context manager
def example_basic_tracing():
    """Demonstrate basic tracing with context manager."""
    tracer = Tracer()
    
    # Trace a user input
    user_id = tracer.log(TraceType.USER, ActionType.INPUT, message="What's the weather in Tokyo?")
    
    # Trace agent processing
    with tracer.trace(TraceType.AGENT, ActionType.START, parent_id=user_id, 
                      args={"task": "Answer weather query"}) as agent_ctx:
        
        # Trace planning step
        with tracer.trace(TraceType.AGENT, ActionType.PROCESS, 
                          label="Planning", args={"user_query": "What's the weather in Tokyo?"}):
            
            # Simulate LLM call for planning
            with tracer.trace(TraceType.LLM, ActionType.REQUEST,
                              model="gpt-4", 
                              args={"prompt": "Plan how to answer weather query", 
                                    "temperature": 0.2}) as llm_ctx:
                time.sleep(0.1)  # Simulate API call
                tracer.log(TraceType.LLM, ActionType.RESPOND, 
                           parent_id=llm_ctx.id,
                           model="gpt-4",
                           response="Use weather tool to get Tokyo weather")
        
        # Trace tool selection
        tracer.log(TraceType.AGENT, ActionType.PROCESS,
                   label="Tool Selection", response="weather")
        
        # Trace tool call
        with tracer.trace(TraceType.TOOL, ActionType.CALL,
                          name="weather", args={"location": "Tokyo"}) as tool_ctx:
            time.sleep(0.1)  # Simulate API call
            tracer.log(TraceType.TOOL, ActionType.RESPOND,
                       parent_id=tool_ctx.id,
                       name="weather",
                       result={"temperature": "22°C", "condition": "sunny", "humidity": "60%"})
        
        # Trace response generation
        with tracer.trace(TraceType.AGENT, ActionType.PROCESS,
                          label="Generate Response",
                          args={"tool_result": {"temperature": "22°C", "condition": "sunny", "humidity": "60%"}}):
            
            # Another LLM call for response
            with tracer.trace(TraceType.LLM, ActionType.REQUEST,
                              model="gpt-4",
                              args={"prompt": "Format weather data for user", "max_tokens": 50}) as llm_ctx:
                time.sleep(0.1)
                tracer.log(TraceType.LLM, ActionType.RESPOND,
                           parent_id=llm_ctx.id,
                           model="gpt-4", 
                           response="Currently in Tokyo: 22°C, sunny, 60% humidity")
        
        # Log final answer
        tracer.log(TraceType.AGENT, ActionType.PROCESS,
                   label="Final Answer",
                   response="Currently in Tokyo: 22°C, sunny, 60% humidity")
    
    # Ensure all traces are written
    tracer.flush()
    print(f"Traces saved to: {tracer.backend.filepath}")


# Example 2: Using decorators
def example_decorator_usage():
    """Demonstrate tracing with decorators."""
    tracer = Tracer()
    set_global_tracer(tracer)
    
    @trace_tool("calculator")
    def calculate(expression: str) -> float:
        """Simple calculator tool."""
        return eval(expression)  # Note: eval is unsafe in production!
    
    @trace_llm(model="gpt-3.5-turbo")
    def call_llm(prompt: str, temperature: float = 0.7) -> str:
        """Simulate LLM call."""
        time.sleep(0.1)
        return f"Response to: {prompt}"
    
    @trace_function(trace_type=TraceType.AGENT, action=ActionType.PROCESS)
    def process_math_query(query: str) -> str:
        """Process a math query."""
        # Extract math expression (simplified)
        if "plus" in query:
            expression = query.replace("What is ", "").replace("plus", "+").replace("?", "").strip()
        else:
            expression = "2 + 2"  # default
        
        # Use calculator
        result = calculate(expression)
        
        # Format response
        response = call_llm(f"Format this result nicely: {result}")
        
        return response
    
    # Log user input
    tracer.log(TraceType.USER, ActionType.INPUT, message="What is 10 plus 25?")
    
    # Process query
    result = process_math_query("What is 10 plus 25?")
    print(f"Result: {result}")
    
    tracer.flush()
    print(f"Traces saved to: {tracer.backend.filepath}")


# Example 3: Nested agents
def example_nested_agents():
    """Demonstrate nested agent tracing."""
    tracer = Tracer()
    
    # User asks for news summary
    user_id = tracer.log(TraceType.USER, ActionType.INPUT, 
                         message="Summarize AI news from last week")
    
    # Main agent starts
    with tracer.trace(TraceType.AGENT, ActionType.START, parent_id=user_id,
                      args={"task": "Summarize AI news"}) as main_agent:
        
        # Call search agent
        tracer.log(TraceType.AGENT, ActionType.PROCESS,
                   label="Calling SearchAgent",
                   args={"query": "AI news last week"})
        
        # Search agent starts
        with tracer.trace(TraceType.AGENT, ActionType.START,
                          name="SearchAgent",
                          args={"query": "AI news last week"}) as search_agent:
            
            # Search tool call
            with tracer.trace(TraceType.TOOL, ActionType.CALL,
                              name="search",
                              args={"query": "AI news last week"}) as tool_ctx:
                time.sleep(0.1)
                tracer.log(TraceType.TOOL, ActionType.RESPOND,
                           parent_id=tool_ctx.id,
                           name="search",
                           result=["Article 1: New LLM breakthrough",
                                   "Article 2: AI ethics debate"])
            
            # Summarize articles
            tracer.log(TraceType.AGENT, ActionType.PROCESS,
                       label="Summarizing articles",
                       args={"articles": ["Article 1: New LLM breakthrough",
                                          "Article 2: AI ethics debate"]})
            
            # LLM call for summary
            with tracer.trace(TraceType.LLM, ActionType.REQUEST,
                              model="gpt-4",
                              args={"prompt": "Summarize these articles"}) as llm_ctx:
                time.sleep(0.1)
                tracer.log(TraceType.LLM, ActionType.RESPOND,
                           parent_id=llm_ctx.id,
                           model="gpt-4",
                           response="Recent AI news covers LLM breakthroughs and ethics debates")
            
            # Return summary
            tracer.log(TraceType.AGENT, ActionType.PROCESS,
                       label="Return summary",
                       response="Recent AI news covers LLM breakthroughs and ethics debates")
        
        # Main agent integrates results
        tracer.log(TraceType.AGENT, ActionType.PROCESS,
                   label="Integrate SearchAgent results",
                   response="Recent AI news covers LLM breakthroughs and ethics debates")
    
    tracer.flush()
    print(f"Traces saved to: {tracer.backend.filepath}")


if __name__ == "__main__":
    print("=== Example 1: Basic Tracing ===")
    example_basic_tracing()
    print("\n" + "="*50 + "\n")
    
    print("=== Example 2: Decorator Usage ===")
    example_decorator_usage()
    print("\n" + "="*50 + "\n")
    
    print("=== Example 3: Nested Agents ===")
    example_nested_agents()