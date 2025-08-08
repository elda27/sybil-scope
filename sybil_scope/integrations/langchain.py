"""
LangChain integration for Sibyl Scope.
"""

from typing import Any
from uuid import UUID

from sybil_scope.api import Tracer
from sybil_scope.core import ActionType, TraceType

try:
    from langchain.callbacks.base import BaseCallbackHandler
    from langchain.schema import AgentAction, AgentFinish, LLMResult

    LANGCHAIN_AVAILABLE = True
except ImportError:
    BaseCallbackHandler = object
    LANGCHAIN_AVAILABLE = False


class SibylScopeCallbackHandler(BaseCallbackHandler):
    """LangChain callback handler for Sibyl Scope tracing."""

    def __init__(self, tracer: Tracer | None = None):
        """Initialize callback handler.

        Args:
            tracer: Tracer instance to use. Creates new one if not provided.
        """
        if not LANGCHAIN_AVAILABLE:
            raise ImportError(
                "LangChain is not installed. Install with: pip install langchain"
            )

        super().__init__()
        self.tracer = tracer or Tracer()
        self._run_id_to_trace_id: dict[UUID, int] = {}

    def on_llm_start(
        self, serialized: dict[str, Any], prompts: list[str], **kwargs: Any
    ) -> None:
        """Run when LLM starts running."""
        run_id = kwargs.get("run_id", "unknown")
        parent_run_id = kwargs.get("parent_run_id")

        if serialized is None:
            serialized = {}  # Avoid unexpected behavior of langchain

        # Get parent trace ID
        parent_trace_id = None
        if parent_run_id and parent_run_id in self._run_id_to_trace_id:
            parent_trace_id = self._run_id_to_trace_id[parent_run_id]

        # Log LLM request
        trace_id = self.tracer.log(
            TraceType.LLM,
            ActionType.REQUEST,
            parent_id=parent_trace_id,
            model=serialized.get("name", "unknown"),
            args={"prompts": prompts, **kwargs.get("invocation_params", {})},
        )

        # Store mapping
        self._run_id_to_trace_id[run_id] = trace_id

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Run when LLM ends running."""
        run_id = kwargs.get("run_id", "unknown")

        # Get parent trace ID
        parent_trace_id = self._run_id_to_trace_id.get(run_id)

        # Extract text from response
        texts = []
        for generation_list in response.generations:
            for generation in generation_list:
                texts.append(generation.text)

        # Log LLM response
        self.tracer.log(
            TraceType.LLM,
            ActionType.RESPOND,
            parent_id=parent_trace_id,
            response=texts[0] if len(texts) == 1 else texts,
            llm_output=response.llm_output,
        )

    def on_llm_error(
        self,
        error: Exception | KeyboardInterrupt,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """Run when LLM errors."""
        parent_trace_id = self._run_id_to_trace_id.get(run_id)

        self.tracer.log(
            TraceType.LLM,
            ActionType.RESPOND,
            parent_id=parent_trace_id,
            error=str(error),
            error_type=type(error).__name__,
        )

    def on_chain_start(
        self, serialized: dict[str, Any], inputs: dict[str, Any], **kwargs: Any
    ) -> None:
        """Run when chain starts running."""
        run_id = kwargs.get("run_id", "unknown")
        parent_run_id = kwargs.get("parent_run_id")

        if serialized is None:
            serialized = {}  # Avoid unexpected behavior of langchain

        # Get parent trace ID
        parent_trace_id = None
        if parent_run_id and parent_run_id in self._run_id_to_trace_id:
            parent_trace_id = self._run_id_to_trace_id[parent_run_id]

        # Log agent start
        trace_id = self.tracer.log(
            TraceType.AGENT,
            ActionType.START,
            parent_id=parent_trace_id,
            name=serialized.get("name", "Chain"),
            args=inputs,
        )

        self._run_id_to_trace_id[run_id] = trace_id

    def on_chain_end(self, outputs: dict[str, Any], **kwargs: Any) -> None:
        """Run when chain ends running."""
        run_id = kwargs.get("run_id", "unknown")
        parent_trace_id = self._run_id_to_trace_id.get(run_id)

        # Get original parent to log end event
        if parent_trace_id:
            # Find the parent of the start event
            original_parent = None
            for event in self.tracer.backend.load():
                if event.id == parent_trace_id and event.action == ActionType.START:
                    original_parent = event.parent_id
                    break

            self.tracer.log(TraceType.AGENT, ActionType.END, parent_id=original_parent)

    def on_chain_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """Run when chain errors."""
        parent_trace_id = self._run_id_to_trace_id.get(run_id)

        self.tracer.log(
            TraceType.AGENT,
            ActionType.PROCESS,
            parent_id=parent_trace_id,
            label="Error",
            error=str(error),
            error_type=type(error).__name__,
        )

    def on_tool_start(
        self, serialized: dict[str, Any], input_str: str, **kwargs: Any
    ) -> None:
        """Run when tool starts running."""
        run_id = kwargs.get("run_id", "unknown")
        parent_run_id = kwargs.get("parent_run_id")

        if serialized is None:
            serialized = {}  # Avoid unexpected behavior of langchain

        # Get parent trace ID
        parent_trace_id = None
        if parent_run_id and parent_run_id in self._run_id_to_trace_id:
            parent_trace_id = self._run_id_to_trace_id[parent_run_id]

        # Log tool call
        trace_id = self.tracer.log(
            TraceType.TOOL,
            ActionType.CALL,
            parent_id=parent_trace_id,
            name=serialized.get("name", "Tool"),
            args={"input": input_str},
        )

        self._run_id_to_trace_id[run_id] = trace_id

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """Run when tool ends running."""
        run_id = kwargs.get("run_id", "unknown")
        parent_trace_id = self._run_id_to_trace_id.get(run_id)

        self.tracer.log(
            TraceType.TOOL, ActionType.RESPOND, parent_id=parent_trace_id, result=output
        )

    def on_tool_error(
        self,
        error: Exception | KeyboardInterrupt,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """Run when tool errors."""
        parent_trace_id = self._run_id_to_trace_id.get(run_id)

        self.tracer.log(
            TraceType.TOOL,
            ActionType.RESPOND,
            parent_id=parent_trace_id,
            error=str(error),
            error_type=type(error).__name__,
        )

    def on_agent_action(self, action: AgentAction, **kwargs: Any) -> None:
        """Run on agent action."""
        run_id = kwargs.get("run_id", "unknown")
        parent_trace_id = self._run_id_to_trace_id.get(run_id)

        self.tracer.log(
            TraceType.AGENT,
            ActionType.PROCESS,
            parent_id=parent_trace_id,
            label="Tool Selection",
            response=action.tool,
            tool_input=action.tool_input,
            log=action.log,
        )

    def on_agent_finish(self, finish: AgentFinish, **kwargs: Any) -> None:
        """Run on agent finish."""
        run_id = kwargs.get("run_id", "unknown")
        parent_trace_id = self._run_id_to_trace_id.get(run_id)

        self.tracer.log(
            TraceType.AGENT,
            ActionType.PROCESS,
            parent_id=parent_trace_id,
            label="Final Answer",
            response=finish.return_values,
            log=finish.log,
        )
