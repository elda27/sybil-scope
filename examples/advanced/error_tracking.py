"""
Error tracking and recovery example.
Demonstrates how to trace errors and recovery strategies.
"""

import sybil_scope as ss


def example_error_tracking():
    """Demonstrate error tracking and recovery patterns."""
    tracer = ss.Tracer()

    def risky_operation(should_fail: bool = False):
        """Operation that might fail."""
        if should_fail:
            raise ValueError("Simulated error")
        return "Success"

    # Start agent with error handling
    with tracer.trace(
        ss.TraceType.AGENT, ss.ActionType.START, name="ErrorHandlingAgent"
    ):
        # Try operation that succeeds
        try:
            with tracer.trace(
                ss.TraceType.AGENT, ss.ActionType.PROCESS, label="Attempt 1"
            ) as attempt_ctx:
                result = risky_operation(should_fail=False)
                tracer.log(
                    ss.TraceType.AGENT,
                    ss.ActionType.PROCESS,
                    parent_id=attempt_ctx.id,
                    label="Success",
                    result=result,
                )
        except Exception as e:
            tracer.log(
                ss.TraceType.AGENT,
                ss.ActionType.PROCESS,
                parent_id=attempt_ctx.id,
                label="Error",
                error=str(e),
                error_type=type(e).__name__,
            )

        # Try operation that fails with recovery
        try:
            with tracer.trace(
                ss.TraceType.AGENT, ss.ActionType.PROCESS, label="Attempt 2"
            ) as attempt_ctx:
                result = risky_operation(should_fail=True)
                tracer.log(
                    ss.TraceType.AGENT,
                    ss.ActionType.PROCESS,
                    parent_id=attempt_ctx.id,
                    label="Success",
                    result=result,
                )
        except Exception as e:
            tracer.log(
                ss.TraceType.AGENT,
                ss.ActionType.PROCESS,
                parent_id=attempt_ctx.id,
                label="Error Caught",
                error=str(e),
                error_type=type(e).__name__,
            )

            # Recovery strategy
            with tracer.trace(
                ss.TraceType.AGENT,
                ss.ActionType.PROCESS,
                parent_id=attempt_ctx.id,
                label="Recovery Strategy",
            ):
                # Try alternative approach
                tracer.log(
                    ss.TraceType.AGENT,
                    ss.ActionType.PROCESS,
                    label="Using Fallback",
                    strategy="default_value",
                )
                result = "Fallback result"

        # Log final status
        tracer.log(
            ss.TraceType.AGENT,
            ss.ActionType.PROCESS,
            label="Final Result",
            result=result,
            had_errors=True,
        )

    tracer.flush()
    print(f"Error tracking traces saved to: {tracer.backend.filepath}")


if __name__ == "__main__":
    print("=== Error Tracking Example ===")
    with ss.option_context((ss.ConfigKey.TRACING_FILE_PREFIX, "error_tracking")):
        example_error_tracking()
