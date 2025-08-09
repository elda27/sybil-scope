"""
Decorators for easy tracing of functions and methods.
"""

from functools import wraps
from typing import Any, Callable, cast

from sybil_scope.api import Tracer
from sybil_scope.core import ActionType, TraceType


def trace_function(
    trace_type: TraceType | str = TraceType.AGENT,
    action: ActionType | str = ActionType.PROCESS,
    capture_args: bool = True,
    capture_result: bool = True,
    tracer: Tracer | None = None,
):
    """Decorator to trace function execution.

    Args:
        trace_type: Type of trace event
        action: Action type for the trace
        capture_args: Whether to capture function arguments
        capture_result: Whether to capture function result
        tracer: Tracer instance to use (defaults to global tracer)
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Get tracer (explicit only)
            active_tracer = tracer
            if not active_tracer:
                # No tracer configured, just execute function
                return func(*args, **kwargs)

            # Prepare details
            details: dict[str, Any] = {"function": func.__name__}
            if capture_args:
                details["args"] = args
                details["kwargs"] = kwargs

            # Execute with tracing
            with active_tracer.trace(
                trace_type=trace_type, action=action, **details
            ) as context:
                try:
                    result = func(*args, **kwargs)
                    if capture_result:
                        # Log result
                        active_tracer.log(
                            trace_type,
                            ActionType.RESPOND,
                            parent_id=context.id,
                            result=result,
                        )
                    return result
                except Exception as e:
                    # Log error
                    active_tracer.log(
                        trace_type,
                        ActionType.RESPOND,
                        parent_id=context.id,
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    raise

        return wrapper

    return decorator


def trace_llm(model: str = "unknown", tracer: Tracer | None = None):
    """Decorator specifically for LLM calls.

    Args:
        model: Name of the LLM model
        tracer: Tracer instance to use
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Get tracer (explicit only)
            active_tracer = tracer
            if not active_tracer:
                return func(*args, **kwargs)

            # Extract prompt from args/kwargs
            prompt = None
            if args:
                prompt = args[0]
            elif "prompt" in kwargs:
                prompt = kwargs["prompt"]

            # Prepare details
            details: dict[str, Any] = {
                "model": model,
                "function": func.__name__,
                "args": {"prompt": prompt} if prompt else {},
            }

            # Add other LLM parameters
            for key in [
                "temperature",
                "max_tokens",
                "top_p",
                "frequency_penalty",
                "presence_penalty",
            ]:
                if key in kwargs:
                    args_dict = cast(dict[str, Any], details.setdefault("args", {}))
                    args_dict[key] = kwargs[key]

            # Execute with tracing
            with active_tracer.trace(
                trace_type=TraceType.LLM, action=ActionType.REQUEST, **details
            ) as context:
                try:
                    response = func(*args, **kwargs)

                    # Log response
                    active_tracer.log(
                        TraceType.LLM,
                        ActionType.RESPOND,
                        parent_id=context.id,
                        model=model,
                        response=response,
                    )

                    return response
                except Exception as e:
                    active_tracer.log(
                        TraceType.LLM,
                        ActionType.RESPOND,
                        parent_id=context.id,
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    raise

        return wrapper

    return decorator


def trace_tool(tool_name: str, tracer: Tracer | None = None):
    """Decorator for tool/function calls.

    Args:
        tool_name: Name of the tool
        tracer: Tracer instance to use
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Get tracer (explicit only)
            active_tracer = tracer
            if not active_tracer:
                return func(*args, **kwargs)

            # Prepare details
            details: dict[str, Any] = {
                "name": tool_name,
                "args": dict(zip(func.__code__.co_varnames, args)) if args else kwargs,
            }

            # Execute with tracing
            with active_tracer.trace(
                trace_type=TraceType.TOOL, action=ActionType.CALL, **details
            ) as context:
                try:
                    result = func(*args, **kwargs)

                    # Log result
                    active_tracer.log(
                        TraceType.TOOL,
                        ActionType.RESPOND,
                        parent_id=context.id,
                        name=tool_name,
                        result=result,
                    )

                    return result
                except Exception as e:
                    active_tracer.log(
                        TraceType.TOOL,
                        ActionType.RESPOND,
                        parent_id=context.id,
                        name=tool_name,
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    raise

        return wrapper

    return decorator
