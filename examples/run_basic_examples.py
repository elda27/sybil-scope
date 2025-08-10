"""
Run all basic examples.
This script executes all basic tracing examples in sequence.
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import sybil_scope
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import example functions
from basic.decorators import example_decorator_usage
from basic.nested_agents import example_nested_agents
from basic.simple_tracing import example_basic_tracing

import sybil_scope as ss


def run_all_basic_examples():
    """Run all basic examples in sequence."""
    print("🚀 Running all basic examples...\n")

    examples = [
        ("Simple Tracing", "basic_tracing", example_basic_tracing),
        ("Decorators", "decorators", example_decorator_usage),
        ("Nested Agents", "nested_agents", example_nested_agents),
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

    print("🎉 All basic examples completed!")


if __name__ == "__main__":
    run_all_basic_examples()
