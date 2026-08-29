from types import SimpleNamespace

import pytest

from agents.conclusion import ConclusionAgent
from agents.discussion import DiscussionAgent
from agents.prompts.questions import FIRST_BAD_VERSION_QUESTION


class RecordingSession:
    def __init__(self) -> None:
        self.generated_instructions: list[str] = []
        self.spoken: list[tuple[str, dict[str, object]]] = []
        self.shutdown_called = False

    async def generate_reply(self, *, instructions: str) -> None:
        self.generated_instructions.append(instructions)

    async def say(self, text: str, **kwargs: object) -> None:
        self.spoken.append((text, kwargs))

    def shutdown(self) -> None:
        self.shutdown_called = True


def attach_session(agent: object, session: RecordingSession) -> None:
    agent._activity = SimpleNamespace(session=session)  # type: ignore[attr-defined]


def test_discussion_instructions_include_the_full_static_question() -> None:
    agent = DiscussionAgent()

    assert FIRST_BAD_VERSION_QUESTION in agent.instructions


def test_discussion_accepts_an_injected_question() -> None:
    question = "Explain how to merge two sorted linked lists."

    agent = DiscussionAgent(question=question)

    assert question in agent.instructions
    assert FIRST_BAD_VERSION_QUESTION not in agent.instructions


@pytest.mark.asyncio
async def test_discussion_setup_requests_a_concise_left_panel_summary() -> None:
    agent = DiscussionAgent()
    session = RecordingSession()
    attach_session(agent, session)

    await agent.on_enter()

    assert len(session.generated_instructions) == 1
    setup = session.generated_instructions[0].lower()
    assert "earliest bad version" in setup
    assert "left panel" in setup
    assert "do not recite" in setup
    assert FIRST_BAD_VERSION_QUESTION.lower() not in setup


@pytest.mark.asyncio
async def test_one_discussion_turn_hands_off_to_context_free_conclusion() -> None:
    agent = DiscussionAgent()

    conclusion = await agent.finish_discussion.__wrapped__(agent, None)

    assert isinstance(conclusion, ConclusionAgent)
    assert conclusion.instructions == ""


@pytest.mark.asyncio
async def test_conclusion_keeps_uninterruptible_closing_and_shutdown() -> None:
    agent = ConclusionAgent()
    session = RecordingSession()
    attach_session(agent, session)

    await agent.on_enter()

    assert session.spoken == [
        ("We're done for now. Let's call it.", {"allow_interruptions": False})
    ]
    assert session.shutdown_called
