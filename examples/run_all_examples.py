"""
Run all examples.
This is the main entry point for running all Sibyl Scope examples.
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import sybil_scope
sys.path.insert(0, str(Path(__file__).parent.parent))

from run_advanced_examples import run_all_advanced_examples
from run_basic_examples import run_all_basic_examples
from run_integration_examples import run_all_integration_examples


def main():
    """Run all examples in sequence."""
    print("🎭 Sibyl Scope Examples Runner")
    print("=" * 50)
    print()

    print("Choose which examples to run:")
    print("1. Basic examples (recommended for beginners)")
    print("2. Advanced examples")
    print("3. Integration examples (requires OpenAI API key)")
    print("4. All examples")
    print("5. Exit")
    print()

    choice = input("Enter your choice (1-5): ").strip()

    if choice == "1":
        run_all_basic_examples()
    elif choice == "2":
        run_all_advanced_examples()
    elif choice == "3":
        run_all_integration_examples()
    elif choice == "4":
        print("🚀 Running ALL examples...\n")
        run_all_basic_examples()
        print("\n" + "🔗" * 25 + "\n")
        run_all_advanced_examples()
        print("\n" + "🔗" * 25 + "\n")
        run_all_integration_examples()
        print("\n🎉 All examples completed!")
    elif choice == "5":
        print("👋 Goodbye!")
        sys.exit(0)
    else:
        print("❌ Invalid choice. Please run the script again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
