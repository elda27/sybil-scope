# Sibyl Scope Examples

This directory contains comprehensive examples demonstrating how to use Sibyl Scope for tracing AI agent workflows, LLM interactions, and complex multi-step processes.

## 📁 Directory Structure

```
examples/
├── basic/                     # 🌱 Basic examples for beginners
│   ├── simple_tracing.py     # Context manager usage
│   ├── decorators.py         # Decorator-based tracing
│   └── nested_agents.py      # Hierarchical agent interactions
│
├── advanced/                  # 🚀 Advanced patterns and techniques
│   ├── custom_backend.py     # Custom backend implementations
│   ├── async_tracing.py      # Asynchronous operations
│   ├── performance_monitoring.py  # Performance analysis
│   ├── error_tracking.py     # Error handling patterns
│   └── multimodal_tracing.py # Multi-modal AI workflows
│
├── integrations/              # 🔗 Framework integrations
│   ├── langchain_simple_chain.py    # Basic LangChain chains
│   ├── langchain_agent.py           # ReAct agents with tools
│   ├── langchain_custom_chain.py    # Multi-step workflows
│   └── langgraph_agent.py           # LangGraph workflows
│
├── utilities/                 # 🛠️ Helper scripts
│   └── generate_sample_traces.py    # Generate test data
│
├── run_basic_examples.py      # Run all basic examples
├── run_advanced_examples.py   # Run all advanced examples
├── run_integration_examples.py # Run all integration examples
└── run_all_examples.py        # Main runner (interactive)
```

## 🚀 Quick Start

### Option 1: Interactive Runner (Recommended)
```bash
cd examples
python run_all_examples.py
```

This will show an interactive menu where you can choose which category of examples to run.

### Option 2: Run Specific Categories
```bash
# Run basic examples (good for beginners)
python run_basic_examples.py

# Run advanced examples
python run_advanced_examples.py

# Run integration examples (requires OpenAI API key)
python run_integration_examples.py
```

### Option 3: Run Individual Examples
```bash
# Basic examples
python basic/simple_tracing.py
python basic/decorators.py
python basic/nested_agents.py

# Advanced examples
python advanced/custom_backend.py
python advanced/async_tracing.py
python advanced/performance_monitoring.py
python advanced/error_tracking.py
python advanced/multimodal_tracing.py

# Integration examples (require OpenAI API key)
python integrations/langchain_simple_chain.py
python integrations/langchain_agent.py
python integrations/langchain_custom_chain.py
python integrations/langgraph_agent.py
```

## 📖 Example Categories

### 🌱 Basic Examples
Perfect for beginners. These examples demonstrate:
- **Simple Tracing**: Using context managers for basic tracing
- **Decorators**: Automatic tracing with function decorators
- **Nested Agents**: Hierarchical agent interactions and sub-tasks

### 🚀 Advanced Examples
For experienced users exploring sophisticated patterns:
- **Custom Backend**: Creating specialized storage backends
- **Async Tracing**: Handling concurrent and asynchronous operations
- **Performance Monitoring**: Using traces for performance analysis
- **Error Tracking**: Tracing error scenarios and recovery strategies
- **Multi-modal Tracing**: Tracing AI workflows involving text, images, and audio

### 🔗 Integration Examples
Framework-specific examples:
- **LangChain**: Simple chains, ReAct agents, custom workflows
- **LangGraph**: Graph-based agent workflows with tool calling

## 🔧 Prerequisites

### Basic and Advanced Examples
- Python 3.8+
- Sibyl Scope installed (`pip install -e .` from project root)

### Integration Examples
- All basic requirements
- OpenAI API key set as environment variable:
  ```bash
  export OPENAI_API_KEY="your-key-here"
  ```
- Required packages (automatically installed with Sibyl Scope):
  - `langchain`
  - `langchain-openai`
  - `langgraph`

## 📊 Output

All examples generate trace files in the `traces/` directory (created automatically). Files are named with prefixes indicating the example type:

```
traces/
├── basic_tracing_YYYYMMDD_HHMMSS_XXXXX.jsonl
├── decorators_YYYYMMDD_HHMMSS_XXXXX.jsonl
├── lc_agent_YYYYMMDD_HHMMSS_XXXXX.jsonl
└── ... (other trace files)
```

## 🔍 Viewing Traces

After running examples, you can visualize the traces using the built-in viewer:

```bash
# From the project root
python -m sybil_scope.viewer

# Or from examples directory
python ../sybil_scope/viewer/__main__.py
```

This opens a web interface where you can:
- Load and explore trace files
- View hierarchical agent interactions
- Analyze performance metrics
- Examine error scenarios

## 🛠️ Generating Test Data

Use the utilities to generate sample trace data for testing:

```bash
python utilities/generate_sample_traces.py
```

This creates various trace scenarios useful for testing the viewer and understanding different patterns.

## 📝 Example Patterns

### Basic Tracing Pattern
```python
import sybil_scope as ss

tracer = ss.Tracer()

# Log user input
user_id = tracer.log(ss.TraceType.USER, ss.ActionType.INPUT, message="Hello")

# Trace agent work
with tracer.trace(ss.TraceType.AGENT, ss.ActionType.START, parent_id=user_id):
    # ... agent work here ...
    pass

tracer.flush()
```

### Decorator Pattern
```python
@ss.trace_function(tracer=tracer)
def my_function():
    return "result"

@ss.trace_llm(model="gpt-4", tracer=tracer)
def llm_call(prompt):
    # ... LLM call here ...
    return "response"
```

### Integration Pattern
```python
from sybil_scope.integrations.langchain import SibylScopeCallbackHandler

tracer = ss.Tracer()
callback = SibylScopeCallbackHandler(tracer)

# Use with any LangChain component
llm = ChatOpenAI(callbacks=[callback])
```

## 🤝 Contributing

When adding new examples:

1. Choose the appropriate category (basic/advanced/integrations)
2. Follow the naming convention: `category_description.py`
3. Include proper docstrings and comments
4. Add the example to the relevant runner script
5. Update this README if adding a new category

## 📚 Learn More

- [Sibyl Scope Documentation](../docs/)
- [API Reference](../sybil_scope/)
- [Viewer Documentation](../docs/viewer.md)

---

Happy tracing! 🎭✨
