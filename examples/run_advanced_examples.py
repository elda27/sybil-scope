"""
Run all advanced examples.
This script executes all advanced tracing examples in sequence.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path so we can import sybil_scope
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import example functions
from advanced.async_tracing import example_async_tracing
from advanced.custom_backend import example_custom_backend
from advanced.error_tracking import example_error_tracking
from advanced.multimodal_tracing import example_multimodal_tracing
from advanced.performance_monitoring import example_performance_monitoring

import sybil_scope as ss


def run_all_advanced_examples():
    """Run all advanced examples in sequence."""
    print("🚀 Running all advanced examples...\n")

    sync_examples = [
        ("Custom Backend", "custom_backend", example_custom_backend),
        ("Performance Monitoring", "performance", example_performance_monitoring),
        ("Error Tracking", "error_tracking", example_error_tracking),
        ("Multi-modal Tracing", "multimodal", example_multimodal_tracing),
    ]

    async_examples = [
        ("Async Tracing", "async", example_async_tracing),
    ]

    # Run synchronous examples
    for name, prefix, example_func in sync_examples:
        print(f"=== {name} Example ===")
        try:
            with ss.option_context((ss.ConfigKey.TRACING_FILE_PREFIX, prefix)):
                example_func()
            print("✅ Completed successfully")
        except Exception as e:
            print(f"❌ Failed with error: {e}")
        print("\n" + "=" * 50 + "\n")

    # Run asynchronous examples
    for name, prefix, example_func in async_examples:
        print(f"=== {name} Example ===")
        try:
            with ss.option_context((ss.ConfigKey.TRACING_FILE_PREFIX, prefix)):
                asyncio.run(example_func())
            print("✅ Completed successfully")
        except Exception as e:
            print(f"❌ Failed with error: {e}")
        print("\n" + "=" * 50 + "\n")

    print("🎉 All advanced examples completed!")


if __name__ == "__main__":
    run_all_advanced_examples()
