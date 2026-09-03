"""Opt-in semantic evaluations for coding-stage silence decisions.

These tests intentionally stay out of the default suite: constructing the real
LLM and running them incurs provider charges.
"""

import os

import pytest

pytestmark = pytest.mark.integration

if os.environ.get("RUN_LIVEKIT_EVALS") != "1":
    pytest.skip("set RUN_LIVEKIT_EVALS=1 to run paid LiveKit evaluations", allow_module_level=True)

from config.env import load_environment  # noqa: E402

load_environment()
if not os.environ.get("OPENAI_API_KEY"):
    pytest.skip(
        "OPENAI_API_KEY is not configured for paid LiveKit evaluations",
        allow_module_level=True,
    )

from livekit.agents import AgentSession  # noqa: E402
from livekit.agents.utils import http_context  # noqa: E402
from livekit.plugins import openai  # noqa: E402

from agents.coding import CodingAgent  # noqa: E402

SILENT_UTTERANCES = (
    "I'll start by defining a pointer for each list.",
    "Now I'm writing the loop and handling the remaining nodes.",
    "Let me correct that condition and continue implementing.",
    "The code is almost done; I'm checking the pointer update.",
)
RESPONSE_UTTERANCES = (
    "Can you clarify whether the input lists may be empty?",
    "I'm confused about what the output should be here. Can you help?",
    "Should I ask you a question about the implementation?",
    "What does this constraint mean for my solution?",
)


async def _run_coding_turn(utterance: str):
    """Run one text turn through a real AgentSession (requires provider setup)."""
    async with http_context.open():
        session = AgentSession(llm=openai.responses.LLM(model="gpt-5.6"))
        await session.start(agent=CodingAgent(), capture_run=False)
        try:
            return await session.run(user_input=utterance)
        finally:
            await session.aclose()


@pytest.mark.parametrize("utterance", SILENT_UTTERANCES)
@pytest.mark.asyncio
async def test_narration_uses_continue_silently(utterance: str) -> None:
    result = await _run_coding_turn(utterance)
    result.expect.contains_function_call(name="continue_silently")
    call_index = next(
        i for i, event in enumerate(result.events)
        if event.type == "function_call" and event.item.name == "continue_silently"
    )
    assert not any(
        event.type == "message" and event.item.role == "assistant"
        for event in result.events[call_index + 1 :]
    )


@pytest.mark.parametrize("utterance", RESPONSE_UTTERANCES)
@pytest.mark.asyncio
async def test_questions_receive_an_assistant_response(utterance: str) -> None:
    result = await _run_coding_turn(utterance)
    result.expect.contains_message(role="assistant")
    assert not any(
        event.type == "function_call" and event.item.name == "continue_silently"
        for event in result.events
    )
