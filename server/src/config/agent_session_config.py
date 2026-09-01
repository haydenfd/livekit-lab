"""Shared LiveKit AgentSession configuration factory."""

from livekit.agents import TurnHandlingOptions, inference
from livekit.plugins import deepgram, openai


def build_agent_session_config() -> dict[str, object]:
    """Build fresh AgentSession keyword arguments for one agent job."""
    return {
        "stt": deepgram.STT(
            model="nova-3",
            language="en-US",
            smart_format=True,
        ),
        # GPT-5.6 function tools require OpenAI's Responses API, not Chat Completions.
        # The plugin reads OPENAI_API_KEY.
        "llm": openai.responses.LLM(model="gpt-5.6"),
        "tts": deepgram.TTS(model="aura-2-asteria-en"),
        "turn_handling": TurnHandlingOptions(
            turn_detection=inference.TurnDetector(),
            # Endpointing controls when the agent treats a pause as the end of
            # a user turn. Leave this unset to preserve the SDK defaults.
            # endpointing={
            #     "mode": "fixed",  # Or "dynamic" to adapt from pauses.
            #     "min_delay": 0.5,  # Shortest pause before ending a turn.
            #     "max_delay": 3.0,  # Longest wait before ending a turn.
            #     "alpha": 0.9,  # Dynamic endpointing's history weighting.
            # },
            interruption={
                "mode": "adaptive",
                # "enabled": False,  # Prevent users from interrupting speech.
                # "min_duration": 0.5,  # Minimum speech for an interruption.
                # "min_words": 0,  # Minimum STT words for an interruption.
                # "discard_audio_if_uninterruptible": True,  # Drop audio then.
                # "false_interruption_timeout": 2.0,  # Silence before false flag.
                # "resume_false_interruption": True,  # Resume after a false flag.
            },
            preemptive_generation={
                "enabled": False,
                # "preemptive_tts": True,  # Start TTS before the turn confirms.
                # "max_speech_duration": 10.0,  # Skip long user turns.
                # "max_retries": 3,  # Attempts allowed in one user turn.
            },
        ),
        "expressive": False,
        # "min_consecutive_speech_delay": 0.0,  # Minimum gap between replies.
    }
