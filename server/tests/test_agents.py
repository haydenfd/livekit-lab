from types import SimpleNamespace

import pytest

from agents.conclusion import ConclusionAgent
from agents.discussion import DiscussionAgent
from agents.intro import IntroAgent
from agents.prompts import (
    LEFT_PANEL_LINE,
    MERGE_TWO_SORTED_LISTS_QUESTION,
    build_discussion_prompt,
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


def test_discussion_instructions_include_discussion_context() -> None:
    agent = DiscussionAgent()
    context = build_discussion_question_context(MERGE_TWO_SORTED_LISTS_QUESTION)

    assert context in agent.instructions
    assert "Example 1:" in agent.instructions
    assert "-100 <= Node.val <= 100" in agent.instructions
    assert "Linked List" not in agent.instructions
    assert "use two pointers" not in agent.instructions


def test_discussion_accepts_an_injected_question() -> None:
    question = make_question()

    agent = DiscussionAgent(question=question)

    assert question.prompt in agent.instructions
    assert build_discussion_question_context(question) in agent.instructions
    assert build_discussion_question_context(MERGE_TWO_SORTED_LISTS_QUESTION) not in (
        agent.instructions
    )


def test_discussion_does_not_override_on_enter() -> None:
    assert "on_enter" not in DiscussionAgent.__dict__


def test_intro_opening_instructions_request_a_concise_core_task_summary() -> None:
    question = make_question()

    instructions = build_intro_opening_instructions(question)

    assert build_intro_question_context(question) in instructions
    assert question.prompt in instructions
    assert "Example 1" not in instructions
    lowered = instructions.lower()
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
        build_intro_opening_instructions(MERGE_TWO_SORTED_LISTS_QUESTION)
    ]
    assert session.generate_kwargs[0]["tool_choice"] == "none"
    assert session.generate_kwargs[0]["allow_interruptions"] is False
    assert session.spoken == [(LEFT_PANEL_LINE, {"allow_interruptions": False})]
    assert isinstance(discussion, DiscussionAgent)
    assert discussion._question is agent._question
    assert discussion._question is MERGE_TWO_SORTED_LISTS_QUESTION
    assert (
        build_intro_question_context(MERGE_TWO_SORTED_LISTS_QUESTION)
        in (session.generated_instructions[0])
    )
    assert build_discussion_question_context(MERGE_TWO_SORTED_LISTS_QUESTION) in (
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
    assert build_discussion_question_context(MERGE_TWO_SORTED_LISTS_QUESTION) not in (
        discussion.instructions
    )


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


def test_build_discussion_prompt_uses_discussion_context() -> None:
    prompt = build_discussion_prompt(MERGE_TWO_SORTED_LISTS_QUESTION)
    context = build_discussion_question_context(MERGE_TWO_SORTED_LISTS_QUESTION)

    assert context in prompt
    assert "https://assets.leetcode.com" not in prompt
    assert prompt.index("You are currently in the discussion stage.") < prompt.index(
        context
    )
