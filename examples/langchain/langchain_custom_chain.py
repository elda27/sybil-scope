"""
Custom LangChain chain example.
Demonstrates tracing complex multi-step chains.
"""

import os

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

import sybil_scope as ss
from sybil_scope.integrations.langchain import SibylScopeCallbackHandler


def example_langchain_custom_chain():
    """Demonstrate tracing a custom multi-step chain."""
    # Using sequential execution for clarity in this example

    # Create tracer and callback
    tracer = ss.Tracer()
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
    if not os.getenv("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY not set. Examples will fail.")
        print("Set it as an environment variable before running.")
        exit(1)

    print("=== Custom LangChain Chain Example ===")
    with ss.option_context((ss.ConfigKey.TRACING_FILE_PREFIX, "lc_custom")):
        example_langchain_custom_chain()
