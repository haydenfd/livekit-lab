from types import SimpleNamespace

import pytest

from agents.conclusion import ConclusionAgent
from agents.discussion import DiscussionAgent
from agents.prompts.discussion import build_discussion_opening
from agents.prompts.questions import RIGHT_SIDE_VIEW_QUESTION
from interview_context import InterviewContext

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


def test_discussion_instructions_include_the_verbatim_static_question() -> None:
    agent = DiscussionAgent()

    assert RIGHT_SIDE_VIEW_QUESTION == EXPECTED_RIGHT_SIDE_VIEW_QUESTION
    assert EXPECTED_RIGHT_SIDE_VIEW_QUESTION in agent.instructions


def test_discussion_accepts_an_injected_question() -> None:
    question = "Explain how to merge two sorted linked lists."

    agent = DiscussionAgent(question=question)

    assert question in agent.instructions
    assert RIGHT_SIDE_VIEW_QUESTION not in agent.instructions


@pytest.mark.asyncio
async def test_discussion_opener_summarizes_the_full_task_and_confirms_language() -> None:
    agent = DiscussionAgent()
    session = RecordingSession()
    session.userdata = InterviewContext(programming_language="python")
    attach_session(agent, session)

    await agent.on_enter()

    assert session.generated_instructions == []
    assert session.spoken == [
        (
            build_discussion_opening("python"),
            {"allow_interruptions": False},
        )
    ]

    opener = session.spoken[0][0].lower()
    assert "binary tree" in opener
    assert "right side" in opener
    assert "top to bottom" in opener
    assert "empty" in opener
    assert "one hundred" in opener
    assert "left panel" in opener
    assert "you're using python, correct?" in opener


@pytest.mark.asyncio
async def test_discussion_opener_asks_for_language_when_session_has_none() -> None:
    agent = DiscussionAgent()
    session = RecordingSession()
    session.userdata = InterviewContext()
    attach_session(agent, session)

    await agent.on_enter()

    assert session.spoken == [
        (
            build_discussion_opening(None),
            {"allow_interruptions": False},
        )
    ]
    assert "which programming language will you use?" in session.spoken[0][0].lower()


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
