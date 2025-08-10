"""
Run all integration examples.
This script executes all framework integration examples in sequence.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path so we can import sybil_scope
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import example functions
from langchain.langchain_agent import example_langchain_agent
from langchain.langchain_custom_chain import example_langchain_custom_chain
from langchain.langchain_simple_chain import example_langchain_simple_chain
from langchain.langgraph_agent import example_langgraph_custom_chain

import sybil_scope as ss


def run_all_integration_examples():
    """Run all integration examples in sequence."""
    print("🚀 Running all integration examples...\n")

    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Warning: OPENAI_API_KEY not set.")
        print("Integration examples require an OpenAI API key.")
        print("Set it as an environment variable before running:")
        print("export OPENAI_API_KEY='your-key-here'")
        return

    examples = [
        ("LangChain Simple Chain", "lc_simple", example_langchain_simple_chain),
        ("LangChain Agent", "lc_agent", example_langchain_agent),
        ("LangChain Custom Chain", "lc_custom", example_langchain_custom_chain),
        ("LangGraph Agent", "lg_agent", example_langgraph_custom_chain),
    ]

    for name, prefix, example_func in examples:
        print(f"=== {name} Example ===")
        try:
            with ss.option_context((ss.ConfigKey.TRACING_FILE_PREFIX, prefix)):
                example_func()
            print("✅ Completed successfully")
        except Exception as e:
            print(f"❌ Failed with error: {e}")
        print("\n" + "=" * 50 + "\n")

    print("🎉 All integration examples completed!")


if __name__ == "__main__":
    run_all_integration_examples()
