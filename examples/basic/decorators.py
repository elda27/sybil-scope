"""
Decorator usage examples for Sibyl Scope.
Shows how to use the built-in decorators for tracing functions.
"""

import time

import sybil_scope as ss


def example_decorator_usage():
    """Demonstrate tracing with decorators."""
    tracer = ss.Tracer()

    @ss.trace_tool("calculator", tracer=tracer)
    def calculate(expression: str) -> float:
        """Simple calculator tool."""
        return eval(expression)  # Note: eval is unsafe in production!

    @ss.trace_llm(model="gpt-3.5-turbo", tracer=tracer)
    def call_llm(prompt: str, temperature: float = 0.7) -> str:
        """Simulate LLM call."""
        time.sleep(0.1)
        return f"Response to: {prompt}"

    @ss.trace_function(
        trace_type=ss.TraceType.AGENT, action=ss.ActionType.PROCESS, tracer=tracer
    )
    def process_math_query(query: str) -> str:
        """Process a math query."""
        # Extract math expression (simplified)
        if "plus" in query:
            expression = (
                query.replace("What is ", "")
                .replace("plus", "+")
                .replace("?", "")
                .strip()
            )
        else:
            expression = "2 + 2"  # default

        # Use calculator
        result = calculate(expression)

        # Format response
        response = call_llm(f"Format this result nicely: {result}")

        return response

    # Log user input
    tracer.log(ss.TraceType.USER, ss.ActionType.INPUT, message="What is 10 plus 25?")

    # Process query
    result = process_math_query("What is 10 plus 25?")
    print(f"Result: {result}")

    tracer.flush()
    print(f"Traces saved to: {tracer.backend.filepath}")


if __name__ == "__main__":
    print("=== Decorator Usage Example ===")
    with ss.option_context((ss.ConfigKey.TRACING_FILE_PREFIX, "decorators")):
        example_decorator_usage()
