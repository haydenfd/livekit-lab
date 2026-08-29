"""Shared LiveKit AgentSession configuration."""

from livekit.agents import AgentSession, TurnHandlingOptions, inference
from livekit.plugins import deepgram, groq


def create_agent_session() -> AgentSession[None]:
    """Create the lab's shared voice pipeline configuration."""
    return AgentSession(
        stt=deepgram.STT(model="nova-3", language="en-US", smart_format=True),
        llm=groq.LLM(model="openai/gpt-oss-120b"),
        tts=deepgram.TTS(model="aura-2-asteria-en"),
        turn_handling=TurnHandlingOptions(
            turn_detection=inference.TurnDetector(),
            interruption={"mode": "adaptive"},
            preemptive_generation={"enabled": False},
        ),
        expressive=False,
    )
