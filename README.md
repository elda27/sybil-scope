# Sibyl Scope

A comprehensive tracing and observability toolkit for Python AI/LLM applications, designed to provide powerful tracing capabilities with minimal overhead for production use.

## Features

- **Easy-to-use API**: Simple context managers and decorators for tracing
- **Multiple trace types**: Support for User, Agent, LLM, and Tool traces
- **Hierarchical tracing**: Parent-child relationships between trace events
- **Flexible backends**: File-based (JSONL) and in-memory storage options
- **Framework integrations**: Built-in support for LangChain
- **Low overhead**: Designed for production use with buffered writes
- **Type-safe**: Full type hints and Pydantic models

## Installation

```bash
pip install sibyl-scope
```

For LangChain integration:
```bash
pip install sibyl-scope[langchain]
```

For visualization components:
```bash
pip install sibyl-scope[viewer]
```

## Quick Start

### Basic Usage

```python
from sybil_scope import Tracer, TraceType, ActionType

# Create a tracer
tracer = Tracer()

# Log a simple event
tracer.log(TraceType.USER, ActionType.INPUT, message="Hello AI!")

# Use context manager for hierarchical traces
with tracer.trace(TraceType.AGENT, ActionType.START, name="MyAgent") as ctx:
    # This event will be a child of the agent
    tracer.log(TraceType.LLM, ActionType.REQUEST, 
               prompt="Generate a response",
               model="gpt-4")
    
    # Simulate processing
    tracer.log(TraceType.LLM, ActionType.RESPOND,
               response="Hello! How can I help you?")

# Ensure all traces are written
tracer.flush()
```

### Show Viewer (Quick Link)

- See the full guide: [docs/viewer.md](docs/viewer.md)
- Quick start (from repo root):
  - Generate sample data: `python examples/generate_sample_traces.py`
  - Launch: `python -m sybil_scope.viewer` or `python run_viewer.py`
  - Open http://localhost:8501

### Using Decorators

```python
from sybil_scope import trace_function, trace_llm, trace_tool, set_global_tracer

# Set up global tracer
tracer = Tracer()
set_global_tracer(tracer)

@trace_tool("calculator")
def calculate(expression: str) -> float:
    return eval(expression)

@trace_llm(model="gpt-3.5-turbo")
def call_llm(prompt: str) -> str:
    # Your LLM call here
    return f"Response to: {prompt}"

@trace_function()
def process_request(user_input: str):
    # Traces will be automatically created
    llm_response = call_llm(user_input)
    if "calculate" in user_input:
        result = calculate("2 + 2")
        return f"{llm_response}. Result: {result}"
    return llm_response
```

### LangChain Integration

```python
from langchain.chat_models import ChatOpenAI
from langchain.agents import initialize_agent, load_tools
from sybil_scope.integrations.langchain import SibylScopeCallbackHandler

# Create callback handler
callback = SibylScopeCallbackHandler()

# Use with LangChain
llm = ChatOpenAI(callbacks=[callback])
tools = load_tools(["calculator"], llm=llm)
agent = initialize_agent(tools, llm, callbacks=[callback])

# All LangChain operations will be traced
result = agent.run("What is 25 * 4?")
```

## Trace Event Structure

Each trace event contains:
- `timestamp`: When the event occurred
- `type`: User, Agent, LLM, or Tool
- `action`: Input, Start, End, Process, Request, Respond, or Call
- `id`: Unique identifier for the event
- `parent_id`: ID of the parent event (for hierarchical traces)
- `details`: Additional event-specific data

## Backends

### FileBackend (Default)
Writes traces to JSONL files with automatic buffering:

```python
from sybil_scope import Tracer, FileBackend

backend = FileBackend(filepath="my_traces.jsonl")
tracer = Tracer(backend=backend)
```

### InMemoryBackend
Keeps traces in memory (useful for testing):

```python
from sybil_scope import Tracer, InMemoryBackend

backend = InMemoryBackend()
tracer = Tracer(backend=backend)

# Later, retrieve traces
events = backend.load()
```

## Advanced Features

### Custom Backends
Create your own backend by inheriting from the `Backend` base class:

```python
from sybil_scope.backend import Backend

class MyCustomBackend(Backend):
    def save(self, event):
        # Your implementation
        pass
    
    def flush(self):
        # Your implementation
        pass
    
    def load(self):
        # Your implementation
        pass
```

### Error Handling
Traces automatically capture exceptions:

```python
@trace_function()
def risky_operation():
    raise ValueError("Something went wrong")

try:
    risky_operation()
except ValueError:
    pass  # Error was traced
```

### Performance Monitoring
Use traces to measure execution time:

```python
events = tracer.backend.load()

# Find paired start/end events and calculate duration
for event in events:
    if event.action == ActionType.START:
        # Find corresponding end event
        end_event = next((e for e in events 
                         if e.parent_id == event.parent_id 
                         and e.action == ActionType.END), None)
        if end_event:
            duration = (end_event.timestamp - event.timestamp).total_seconds()
            print(f"Operation took {duration:.3f}s")
```

### Running the Viewer

```bash
# Install viewer dependencies
pip install sibyl-scope[viewer]

# Generate sample data (optional)
python examples/generate_sample_traces.py

# Start the viewer
python run_viewer.py
```

Then open http://localhost:8501 in your browser.

### Visualization Features
Visualization features are only available for preview implementations.
There are improvements planned for future releases to implement more rich visualization using React/TypeScript implementations.

1. **📊 Statistics View**: Overview metrics, event type distribution, performance analysis
2. **🌳 Hierarchical View**: Expandable tree structure showing parent-child relationships
3. **📅 Timeline View**: Multiple timeline visualizations including:
   - Gantt charts for operation durations
   - Scatter plots for event sequences
   - Swimlane views by event type
   - Performance-focused timeline
4. **🌊 Flow Diagram**: Interactive flow charts showing trace structure with:
   - Simple text-based tree view
   - Graphviz-generated diagrams
   - Interactive network visualizations (pyvis)
5. **📋 Table View**: Detailed tabular data with:
   - Flat table with filtering
   - Hierarchical expandable rows
   - Export capabilities (CSV, JSON)

### Visualization Screenshots

The viewer provides multiple ways to explore your trace data:
- **Event Inspector**: Click on any event to see detailed information
- **Filtering Options**: Filter by event type, action, depth, and more
- **Interactive Elements**: Expandable sections, clickable nodes, hover tooltips
- **Export Features**: Download data in various formats

## Examples

See the `examples/` directory for more detailed examples:
- `basic_usage.py`: Basic tracing patterns
- `langchain_integration.py`: Using with LangChain
- `advanced_patterns.py`: Advanced usage including async, parallel operations, and custom backends
- `generate_sample_traces.py`: Generate sample data for testing visualizations
