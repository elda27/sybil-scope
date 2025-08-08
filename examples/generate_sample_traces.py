"""
Generate sample trace data for testing the visualization components.
"""

import time

from sybil_scope import ActionType, FileBackend, Tracer, TraceType


def generate_complex_agent_traces():
    """Generate complex agent traces with multiple levels of nesting."""
    backend = FileBackend(filepath="sample_traces.jsonl")
    tracer = Tracer(backend=backend)

    print("🎯 Generating complex agent traces...")

    # User asks for weather and news
    user_id = tracer.log(
        TraceType.USER,
        ActionType.INPUT,
        message="Can you tell me the weather in Tokyo and any AI news today?",
    )

    # Main orchestrator agent
    with tracer.trace(
        TraceType.AGENT,
        ActionType.START,
        parent_id=user_id,
        name="OrchestratorAgent",
        task="Handle multi-part user request",
    ):
        # Planning phase
        with tracer.trace(
            TraceType.AGENT,
            ActionType.PROCESS,
            label="Planning",
            args={"user_query": "weather + news request"},
        ):
            # LLM call for planning
            with tracer.trace(
                TraceType.LLM,
                ActionType.REQUEST,
                model="gpt-4",
                args={
                    "prompt": "Plan how to handle weather and news request",
                    "temperature": 0.2,
                },
            ) as llm_planning:
                time.sleep(0.05)  # Simulate API delay
                tracer.log(
                    TraceType.LLM,
                    ActionType.RESPOND,
                    parent_id=llm_planning.id,
                    model="gpt-4",
                    response="Need to: 1) Get weather for Tokyo, 2) Search for AI news, 3) Combine results",
                )

        # Tool selection
        tracer.log(
            TraceType.AGENT,
            ActionType.PROCESS,
            label="Task Breakdown",
            strategy="parallel_execution",
            tasks=["weather_lookup", "news_search"],
        )

        # Parallel execution of weather and news tasks
        # Weather Agent
        with tracer.trace(
            TraceType.AGENT,
            ActionType.START,
            name="WeatherAgent",
            args={"location": "Tokyo"},
        ):
            # Weather API call
            with tracer.trace(
                TraceType.TOOL,
                ActionType.CALL,
                name="weather_api",
                args={"city": "Tokyo", "units": "metric"},
            ) as weather_tool:
                time.sleep(0.1)  # Simulate API delay
                tracer.log(
                    TraceType.TOOL,
                    ActionType.RESPOND,
                    parent_id=weather_tool.id,
                    name="weather_api",
                    result={
                        "temperature": 24,
                        "condition": "partly_cloudy",
                        "humidity": 65,
                        "wind_speed": 12,
                    },
                )

            # Format weather data
            tracer.log(
                TraceType.AGENT,
                ActionType.PROCESS,
                label="Format Weather Data",
                formatted_data="24°C, partly cloudy, 65% humidity",
            )

        # News Agent (with some complications)
        with tracer.trace(
            TraceType.AGENT,
            ActionType.START,
            name="NewsAgent",
            args={"topic": "AI news", "timeframe": "today"},
        ):
            # First attempt - search fails
            with tracer.trace(
                TraceType.TOOL,
                ActionType.CALL,
                name="news_search",
                args={"query": "AI news today", "sources": ["techcrunch", "arxiv"]},
            ) as news_tool1:
                time.sleep(0.08)
                tracer.log(
                    TraceType.TOOL,
                    ActionType.RESPOND,
                    parent_id=news_tool1.id,
                    name="news_search",
                    error="Rate limit exceeded",
                    error_type="APIError",
                )

            # Error handling
            tracer.log(
                TraceType.AGENT,
                ActionType.PROCESS,
                label="Error Recovery",
                error="Rate limit hit, trying alternative source",
            )

            # Retry with different source
            with tracer.trace(
                TraceType.TOOL,
                ActionType.CALL,
                name="alternative_news_api",
                args={"query": "artificial intelligence", "limit": 3},
            ) as news_tool2:
                time.sleep(0.06)
                tracer.log(
                    TraceType.TOOL,
                    ActionType.RESPOND,
                    parent_id=news_tool2.id,
                    name="alternative_news_api",
                    result=[
                        {
                            "title": "OpenAI releases new model",
                            "summary": "Major breakthrough in reasoning",
                        },
                        {
                            "title": "AI ethics debate continues",
                            "summary": "New regulations proposed",
                        },
                        {
                            "title": "Google AI advances",
                            "summary": "Improved efficiency algorithms",
                        },
                    ],
                )

            # Summarize news
            with tracer.trace(
                TraceType.LLM,
                ActionType.REQUEST,
                model="gpt-3.5-turbo",
                args={"prompt": "Summarize these AI news articles", "max_tokens": 150},
            ) as news_llm:
                time.sleep(0.04)
                tracer.log(
                    TraceType.LLM,
                    ActionType.RESPOND,
                    parent_id=news_llm.id,
                    model="gpt-3.5-turbo",
                    response="Today's AI news highlights: OpenAI's new reasoning model, ongoing ethics discussions about AI regulations, and Google's efficiency improvements.",
                )

        # Synthesis phase
        tracer.log(
            TraceType.AGENT,
            ActionType.PROCESS,
            label="Information Synthesis",
            inputs=["weather_data", "news_summary"],
        )

        # Final response generation
        with tracer.trace(
            TraceType.LLM,
            ActionType.REQUEST,
            model="gpt-4",
            args={
                "prompt": "Combine weather and news into user-friendly response",
                "temperature": 0.3,
            },
        ) as final_llm:
            time.sleep(0.07)
            tracer.log(
                TraceType.LLM,
                ActionType.RESPOND,
                parent_id=final_llm.id,
                model="gpt-4",
                response="Here's your update: Tokyo weather is 24°C and partly cloudy with 65% humidity. In AI news today: OpenAI released a new reasoning model, AI ethics debates continue with new regulation proposals, and Google announced efficiency improvements in their algorithms.",
            )

        # Final orchestrator response
        tracer.log(
            TraceType.AGENT,
            ActionType.PROCESS,
            label="Final Response",
            response="Successfully provided weather and news information",
            execution_time="0.3s",
            tasks_completed=2,
        )

    tracer.flush()
    print(f"✅ Generated sample traces saved to: {backend.filepath}")
    return backend.filepath


def generate_error_scenario_traces():
    """Generate traces with various error scenarios."""
    backend = FileBackend(filepath="error_scenario_traces.jsonl")
    tracer = Tracer(backend=backend)

    print("⚠️ Generating error scenario traces...")

    # User request
    user_id = tracer.log(
        TraceType.USER,
        ActionType.INPUT,
        message="Calculate the square root of -1 and get stock prices",
    )

    # Error-prone agent
    with tracer.trace(
        TraceType.AGENT, ActionType.START, parent_id=user_id, name="MathAndFinanceAgent"
    ):
        # Math calculation - will fail
        with tracer.trace(
            TraceType.TOOL,
            ActionType.CALL,
            name="math_calculator",
            args={"operation": "sqrt", "value": -1},
        ) as math_tool:
            time.sleep(0.02)
            tracer.log(
                TraceType.TOOL,
                ActionType.RESPOND,
                parent_id=math_tool.id,
                name="math_calculator",
                error="Cannot calculate square root of negative number",
                error_type="ValueError",
            )

        # Error handling
        tracer.log(
            TraceType.AGENT,
            ActionType.PROCESS,
            label="Math Error Recovery",
            strategy="return_complex_number",
        )

        # Complex number calculation
        with tracer.trace(
            TraceType.TOOL,
            ActionType.CALL,
            name="complex_math",
            args={"operation": "complex_sqrt", "value": -1},
        ) as complex_tool:
            time.sleep(0.01)
            tracer.log(
                TraceType.TOOL,
                ActionType.RESPOND,
                parent_id=complex_tool.id,
                name="complex_math",
                result="i (imaginary unit)",
            )

        # Stock price lookup - network error
        with tracer.trace(
            TraceType.TOOL,
            ActionType.CALL,
            name="stock_api",
            args={"symbols": ["AAPL", "GOOGL", "MSFT"]},
        ) as stock_tool:
            time.sleep(0.05)
            tracer.log(
                TraceType.TOOL,
                ActionType.RESPOND,
                parent_id=stock_tool.id,
                name="stock_api",
                error="Network connection timeout",
                error_type="NetworkError",
            )

        # Fallback strategy
        tracer.log(
            TraceType.AGENT,
            ActionType.PROCESS,
            label="Stock Data Fallback",
            strategy="use_cached_data",
        )

        # Use cached data
        with tracer.trace(
            TraceType.TOOL,
            ActionType.CALL,
            name="cache_lookup",
            args={"key": "stock_prices", "max_age": "1h"},
        ) as cache_tool:
            time.sleep(0.005)
            tracer.log(
                TraceType.TOOL,
                ActionType.RESPOND,
                parent_id=cache_tool.id,
                name="cache_lookup",
                result={"AAPL": 150.25, "GOOGL": 2800.50, "MSFT": 420.75},
                data_age="45 minutes",
            )

        # Final response despite errors
        tracer.log(
            TraceType.AGENT,
            ActionType.PROCESS,
            label="Partial Success Response",
            response="Square root of -1 is i (imaginary unit). Stock prices from cache: AAPL $150.25, GOOGL $2800.50, MSFT $420.75",
            warnings=["Used cached stock data due to network error"],
        )

    tracer.flush()
    print(f"✅ Generated error scenario traces saved to: {backend.filepath}")
    return backend.filepath


def generate_performance_test_traces():
    """Generate traces for performance testing visualization."""
    backend = FileBackend(filepath="performance_test_traces.jsonl")
    tracer = Tracer(backend=backend)

    print("🚀 Generating performance test traces...")

    # Simulate a performance-intensive workflow
    user_id = tracer.log(
        TraceType.USER,
        ActionType.INPUT,
        message="Process large dataset and generate report",
    )

    with tracer.trace(
        TraceType.AGENT, ActionType.START, parent_id=user_id, name="DataProcessingAgent"
    ):
        # Data loading (slow)
        with tracer.trace(
            TraceType.TOOL,
            ActionType.CALL,
            name="data_loader",
            args={"source": "big_dataset.csv", "size": "10GB"},
        ) as loader:
            time.sleep(0.3)  # Simulate slow loading
            tracer.log(
                TraceType.TOOL,
                ActionType.RESPOND,
                parent_id=loader.id,
                name="data_loader",
                result={"rows": 1000000, "columns": 50},
            )

        # Parallel processing
        for i in range(3):
            with tracer.trace(
                TraceType.TOOL,
                ActionType.CALL,
                name=f"processor_{i}",
                args={"chunk": i, "rows": 333333},
            ) as processor:
                time.sleep(0.1 + i * 0.02)  # Variable processing time
                tracer.log(
                    TraceType.TOOL,
                    ActionType.RESPOND,
                    parent_id=processor.id,
                    name=f"processor_{i}",
                    result={"processed_rows": 333333, "errors": i},
                )

        # Aggregation (medium speed)
        with tracer.trace(
            TraceType.TOOL,
            ActionType.CALL,
            name="aggregator",
            args={"method": "sum", "group_by": "category"},
        ) as aggregator:
            time.sleep(0.08)
            tracer.log(
                TraceType.TOOL,
                ActionType.RESPOND,
                parent_id=aggregator.id,
                name="aggregator",
                result={"categories": 15, "total_sum": 25000000},
            )

        # Report generation (fast)
        with tracer.trace(
            TraceType.LLM,
            ActionType.REQUEST,
            model="report-generator",
            args={"template": "executive_summary", "data": "aggregated_results"},
        ) as report_llm:
            time.sleep(0.02)
            tracer.log(
                TraceType.LLM,
                ActionType.RESPOND,
                parent_id=report_llm.id,
                model="report-generator",
                response="Executive summary report generated with key insights and visualizations",
            )

        # Export (very fast)
        with tracer.trace(
            TraceType.TOOL,
            ActionType.CALL,
            name="exporter",
            args={"format": "pdf", "destination": "reports/"},
        ) as exporter:
            time.sleep(0.01)
            tracer.log(
                TraceType.TOOL,
                ActionType.RESPOND,
                parent_id=exporter.id,
                name="exporter",
                result={"file": "report_2025.pdf", "size": "2.5MB"},
            )

    tracer.flush()
    print(f"✅ Generated performance test traces saved to: {backend.filepath}")
    return backend.filepath


if __name__ == "__main__":
    print("🎭 Generating sample trace data for visualization testing...\n")

    # Generate different types of sample data
    complex_file = generate_complex_agent_traces()
    print()

    error_file = generate_error_scenario_traces()
    print()

    perf_file = generate_performance_test_traces()
    print()

    print("🎉 All sample trace files generated!")
    print("📁 Files created:")
    print(f"   • {complex_file} - Complex agent interactions")
    print(f"   • {error_file} - Error handling scenarios")
    print(f"   • {perf_file} - Performance testing workflow")
    print()
    print("🔍 Use these files with the Sibyl Scope viewer:")
    print("   python run_viewer.py")
    print("   Then load any of the generated .jsonl files")
