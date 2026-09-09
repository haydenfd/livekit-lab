from types import SimpleNamespace

import pytest

from agents.coding import CodingAgent
from agents.conclusion import ConclusionAgent
from agents.discussion import DiscussionAgent
from agents.intro import IntroAgent
from agents.prompts import (
    LEFT_PANEL_LINE,
    MAXIMUM_DEPTH_QUESTION,
    build_intro_opening_instructions,
)
from interview_question import (
    InterviewQuestion,
    QuestionExample,
    build_discussion_question_context,
    build_intro_question_context,
)


def make_question(**overrides: object) -> InterviewQuestion:
    values: dict[str, object] = {
        "idx": 99,
        "slug": "injected-question",
        "title": "Injected Question",
        "difficulty": "easy",
        "topic_tags": ("Graphs",),
        "prompt": "Explain how to merge two sorted linked lists.",
        "examples": (
            QuestionExample(
                label="Example 1",
                input="list1 = [1], list2 = [2]",
                output="[1,2]",
                explanation=None,
                images=(),
            ),
        ),
        "constraints": ("Both lists are sorted.",),
        "hints": ("use two pointers",),
        "starter_code": {"python": {"raw_code": "def merge(): pass"}},
    }
    values.update(overrides)
    return InterviewQuestion(**values)  # type: ignore[arg-type]


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
        self.delete_room_called = False

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
        self.events.append("shutdown")
        self.shutdown_called = True

    def delete_room(self) -> None:
        self.delete_room_called = True


def attach_session(agent: object, session: RecordingSession) -> None:
    agent._activity = SimpleNamespace(session=session)  # type: ignore[attr-defined]


def test_discussion_does_not_override_on_enter() -> None:
    assert "on_enter" not in DiscussionAgent.__dict__


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
        build_intro_opening_instructions(MAXIMUM_DEPTH_QUESTION)
    ]
    assert session.generate_kwargs[0]["tool_choice"] == "none"
    assert session.generate_kwargs[0]["allow_interruptions"] is False
    assert session.spoken == [(LEFT_PANEL_LINE, {"allow_interruptions": False})]
    assert isinstance(discussion, DiscussionAgent)
    assert discussion._question is agent._question
    assert discussion._question is MAXIMUM_DEPTH_QUESTION
    assert (
        build_intro_question_context(MAXIMUM_DEPTH_QUESTION)
        in (session.generated_instructions[0])
    )
    assert build_discussion_question_context(MAXIMUM_DEPTH_QUESTION) in (
        discussion.instructions
    )


@pytest.mark.asyncio
async def test_intro_transition_forwards_the_injected_question() -> None:
    question = make_question()
    agent = IntroAgent(question=question)
    session = RecordingSession()
    attach_session(agent, session)

    discussion = await agent.move_to_discussion.__wrapped__(agent, None)

    assert discussion._question is question
    assert build_intro_question_context(question) in session.generated_instructions[0]
    assert build_discussion_question_context(question) in discussion.instructions
    assert build_discussion_question_context(MAXIMUM_DEPTH_QUESTION) not in (
        discussion.instructions
    )


def test_discussion_exposes_only_the_explicit_coding_tool() -> None:
    agent = DiscussionAgent()

    assert hasattr(agent, "start_coding")
    assert not hasattr(agent, "conclude_discussion")
    assert not hasattr(agent, "finish_discussion")
    assert len(agent.tools) == 1


def test_discussion_remains_active_until_explicit_completion() -> None:
    clarification = DiscussionAgent()
    approach = DiscussionAgent()

    assert type(clarification) is DiscussionAgent
    assert type(approach) is DiscussionAgent
    assert type(clarification) is not ConclusionAgent
    assert type(approach) is not ConclusionAgent


@pytest.mark.asyncio
async def test_discussion_completion_speaks_transition_then_enters_coding() -> None:
    agent = DiscussionAgent()
    session = RecordingSession()
    attach_session(agent, session)

    coding = await agent.start_coding.__wrapped__(agent, None)

    assert isinstance(coding, CodingAgent)
    assert session.events == [
        "say:Go ahead and start implementing your approach.",
        "wait:say:Go ahead and start implementing your approach.",
    ]
    assert session.spoken == [
        (
            "Go ahead and start implementing your approach.",
            {"allow_interruptions": False},
        )
    ]


@pytest.mark.asyncio
async def test_conclusion_finishes_speech_then_stops_without_deleting_the_room() -> (
    None
):
    agent = ConclusionAgent()
    session = RecordingSession()
    attach_session(agent, session)

    await agent.on_enter()

    closing_line = "We're done for now"
    assert session.events == [
        f"say:{closing_line}",
        f"wait:say:{closing_line}",
        "shutdown",
    ]
    assert session.spoken == [(closing_line, {"allow_interruptions": False})]
    assert session.shutdown_called
    assert not session.delete_room_called
