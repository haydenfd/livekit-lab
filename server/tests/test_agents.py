from types import SimpleNamespace

import pytest

from agents.conclusion import ConclusionAgent
from agents.discussion import DiscussionAgent
from agents.intro import IntroAgent
from agents.prompts import (
    LEFT_PANEL_LINE,
    RIGHT_SIDE_VIEW_QUESTION,
    build_intro_opening_instructions,
)

EXPECTED_RIGHT_SIDE_VIEW_QUESTION = """\
Given the root of a binary tree, imagine yourself standing on the right side of it, return the values of the nodes you can see ordered from top to bottom.

Example 1:

Input: root = [1,2,3,null,5,null,4]

Output: [1,3,4]

Explanation:

Example 2:

Input: root = [1,2,3,4,null,null,null,5]

Output: [1,3,4,5]

Explanation:

Example 3:

Input: root = [1,null,3]

Output: [1,3]

Example 4:

Input: root = []

Output: []

Constraints:

The number of nodes in the tree is in the range [0, 100].

-100 <= Node.val <= 100
"""


class FakeSpeechHandle:
    def __init__(self, events: list[str], label: str) -> None:
        self._events = events
        self._label = label

    async def wait_for_playout(self) -> None:
        self._events.append(f"wait:{self._label}")

    def __await__(self):
        return self.wait_for_playout().__await__()


class RecordingSession:
    def __init__(self) -> None:
        self.events: list[str] = []
        self.generated_instructions: list[str] = []
        self.generate_kwargs: list[dict[str, object]] = []
        self.spoken: list[tuple[str, dict[str, object]]] = []
        self.shutdown_called = False

    def generate_reply(
        self, *, instructions: str, **kwargs: object
    ) -> FakeSpeechHandle:
        self.events.append("generate_reply")
        self.generated_instructions.append(instructions)
        self.generate_kwargs.append(kwargs)
        return FakeSpeechHandle(self.events, "generate_reply")

    def say(self, text: str, **kwargs: object) -> FakeSpeechHandle:
        self.events.append(f"say:{text}")
        self.spoken.append((text, kwargs))
        return FakeSpeechHandle(self.events, f"say:{text}")

    def shutdown(self) -> None:
        self.shutdown_called = True


def attach_session(agent: object, session: RecordingSession) -> None:
    agent._activity = SimpleNamespace(session=session)  # type: ignore[attr-defined]


def test_discussion_instructions_include_the_verbatim_static_question() -> None:
    agent = DiscussionAgent()

    assert RIGHT_SIDE_VIEW_QUESTION == EXPECTED_RIGHT_SIDE_VIEW_QUESTION
    assert EXPECTED_RIGHT_SIDE_VIEW_QUESTION in agent.instructions


def test_discussion_accepts_an_injected_question() -> None:
    question = "Explain how to merge two sorted linked lists."

    agent = DiscussionAgent(question=question)

    assert question in agent.instructions
    assert RIGHT_SIDE_VIEW_QUESTION not in agent.instructions


def test_discussion_does_not_override_on_enter() -> None:
    assert "on_enter" not in DiscussionAgent.__dict__


def test_intro_opening_instructions_request_a_concise_core_task_summary() -> None:
    question = "Explain how to merge two sorted linked lists."

    instructions = build_intro_opening_instructions(question)

    assert question in instructions
    lowered = instructions.lower()
    assert "right side view" not in lowered
    assert "constraint" in lowered
    assert "example" in lowered
    assert "algorithm" in lowered
    assert "do not ask any questions" in lowered
    assert "do not mention a programming language" in lowered


@pytest.mark.asyncio
async def test_intro_transition_speaks_intro_then_hands_off_to_discussion() -> None:
    agent = IntroAgent()
    session = RecordingSession()
    attach_session(agent, session)

    discussion = await agent.move_to_discussion.__wrapped__(agent, None)

    assert session.events == [
        "generate_reply",
        "wait:generate_reply",
        f"say:{LEFT_PANEL_LINE}",
        f"wait:say:{LEFT_PANEL_LINE}",
    ]
    assert session.generated_instructions == [
        build_intro_opening_instructions(RIGHT_SIDE_VIEW_QUESTION)
    ]
    assert session.generate_kwargs[0]["tool_choice"] == "none"
    assert session.generate_kwargs[0]["allow_interruptions"] is False
    assert session.spoken == [(LEFT_PANEL_LINE, {"allow_interruptions": False})]
    assert isinstance(discussion, DiscussionAgent)
    assert RIGHT_SIDE_VIEW_QUESTION in discussion.instructions


@pytest.mark.asyncio
async def test_intro_transition_forwards_the_injected_question() -> None:
    question = "Explain how to merge two sorted linked lists."
    agent = IntroAgent(question=question)
    session = RecordingSession()
    attach_session(agent, session)

    discussion = await agent.move_to_discussion.__wrapped__(agent, None)

    assert question in session.generated_instructions[0]
    assert question in discussion.instructions
    assert RIGHT_SIDE_VIEW_QUESTION not in discussion.instructions


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
