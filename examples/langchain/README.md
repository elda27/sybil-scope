# LangChain Integration Examples

## Files

- **`langchain_simple_chain.py`** - Basic LangChain chain tracing with PromptTemplate | LLM | OutputParser
- **`langchain_agent.py`** - ReAct agent with tools using AgentExecutor and SibylScopeCallbackHandler
- **`langchain_custom_chain.py`** - Multi-step chain workflow with sequential LLM calls
- **`langgraph_agent.py`** - LangGraph-based agent with tool calling and state management

## Prerequisites

Set OpenAI API key:
```bash
export OPENAI_API_KEY="your-key-here"
```

## Usage

```bash
python langchain_simple_chain.py
python langchain_agent.py
python langchain_custom_chain.py
python langgraph_agent.py
```
