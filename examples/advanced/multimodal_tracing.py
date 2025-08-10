"""
Multi-modal tracing example.
Demonstrates tracing AI operations involving text, image, and audio.
"""

import time

import sybil_scope as ss


def example_multimodal_tracing():
    """Demonstrate tracing multi-modal AI operations."""
    tracer = ss.Tracer()

    # User uploads image
    user_id = tracer.log(
        ss.TraceType.USER,
        ss.ActionType.INPUT,
        message="Analyze this image",
        attachments=[{"type": "image", "path": "/tmp/user_image.jpg"}],
    )

    # Vision model analysis
    with tracer.trace(
        ss.TraceType.AGENT, ss.ActionType.START, parent_id=user_id, name="VisionAgent"
    ):
        # Image preprocessing
        tracer.log(
            ss.TraceType.AGENT,
            ss.ActionType.PROCESS,
            label="Preprocessing",
            operations=["resize", "normalize"],
            image_size=(1024, 1024),
        )

        # Vision model call
        with tracer.trace(
            ss.TraceType.LLM,
            ss.ActionType.REQUEST,
            model="gpt-4-vision",
            args={"image_path": "/tmp/user_image.jpg", "prompt": "Describe this image"},
        ) as vision_ctx:
            time.sleep(0.2)  # Simulate processing
            tracer.log(
                ss.TraceType.LLM,
                ss.ActionType.RESPOND,
                parent_id=vision_ctx.id,
                model="gpt-4-vision",
                response="The image shows a sunset over mountains",
                detected_objects=["sun", "mountains", "clouds"],
            )

        # Generate audio description
        tracer.log(
            ss.TraceType.AGENT,
            ss.ActionType.PROCESS,
            label="Generate Audio",
            text="The image shows a sunset over mountains",
        )

        with tracer.trace(
            ss.TraceType.TOOL,
            ss.ActionType.CALL,
            name="text_to_speech",
            args={
                "text": "The image shows a sunset over mountains",
                "voice": "natural",
            },
        ) as tts_ctx:
            time.sleep(0.1)
            tracer.log(
                ss.TraceType.TOOL,
                ss.ActionType.RESPOND,
                parent_id=tts_ctx.id,
                name="text_to_speech",
                result={"audio_path": "/tmp/description.mp3", "duration": 3.5},
            )

        # Final multi-modal response
        tracer.log(
            ss.TraceType.AGENT,
            ss.ActionType.PROCESS,
            label="Multi-modal Response",
            response={
                "text": "The image shows a sunset over mountains",
                "audio": "/tmp/description.mp3",
                "metadata": {
                    "detected_objects": ["sun", "mountains", "clouds"],
                    "dominant_colors": ["orange", "purple", "blue"],
                },
            },
        )

    tracer.flush()
    print(f"Multi-modal traces saved to: {tracer.backend.filepath}")


if __name__ == "__main__":
    print("=== Multi-modal Tracing Example ===")
    with ss.option_context((ss.ConfigKey.TRACING_FILE_PREFIX, "multimodal")):
        example_multimodal_tracing()
