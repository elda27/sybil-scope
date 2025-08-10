"""
Simple LangChain chain tracing example.
Demonstrates basic integration with LangChain pipelines.
"""

import os

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

import sybil_scope as ss
from sybil_scope.integrations.langchain import SibylScopeCallbackHandler


def example_langchain_simple_chain():
    """Demonstrate tracing a simple LangChain chain."""
    # Create tracer and callback
    tracer = ss.Tracer()  # default FileBackend writes to traces/
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


if __name__ == "__main__":
    # Note: These examples require OpenAI API key to be set
    # export OPENAI_API_KEY="your-key-here"

    if not os.getenv("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY not set. Examples will fail.")
        print("Set it as an environment variable before running.")
        exit(1)

    print("=== Simple LangChain Chain Example ===")
    with ss.option_context((ss.ConfigKey.TRACING_FILE_PREFIX, "lc_simple")):
        example_langchain_simple_chain()
