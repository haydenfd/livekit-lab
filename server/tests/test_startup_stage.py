import pytest

import agent as agent_module
from agents.coding import CodingAgent
from agents.intro import IntroAgent
from agents.prompts import REVERSE_LINKED_LIST_QUESTION
from config.env import get_interview_start_stage


class Speech:
    def __init__(self, events: list[str]) -> None:
        self._events = events

    async def wait_for_playout(self) -> None:
        self._events.append("approval_played")


class RecordingAgentSession:
    def __init__(self) -> None:
        self.events: list[str] = []
        self.start_calls: list[dict[str, object]] = []
        self.say_calls: list[tuple[str, dict[str, object]]] = []

    async def start(self, **kwargs: object) -> None:
        self.events.append("session_started")
        self.start_calls.append(kwargs)

    def say(self, text: str, **kwargs: object) -> Speech:
        self.events.append("approval_spoken")
        self.say_calls.append((text, kwargs))
        return Speech(self.events)

    def generate_reply(self, **kwargs: object) -> None:
        raise AssertionError(f"startup must not run an LLM turn: {kwargs}")


def test_start_stage_defaults_to_intro() -> None:
    assert get_interview_start_stage({}) == "intro"


@pytest.mark.parametrize("stage", ["intro", "coding"])
def test_start_stage_accepts_supported_values(stage: str) -> None:
    assert get_interview_start_stage({"INTERVIEW_START_STAGE": stage}) == stage


def test_start_stage_rejects_unknown_values() -> None:
    with pytest.raises(
        ValueError,
        match=(
            "Invalid INTERVIEW_START_STAGE='discussion'; accepted values are: "
            "intro, coding"
        ),
    ):
        get_interview_start_stage({"INTERVIEW_START_STAGE": "discussion"})


@pytest.mark.asyncio
async def test_intro_mode_preserves_existing_startup_without_history() -> None:
    session = RecordingAgentSession()
    room = object()
    room_options = object()

    await agent_module.start_interview(
        agent_session=session,
        room=room,
        room_options=room_options,
        start_stage="intro",
    )

    assert session.events == ["session_started"]
    assert session.say_calls == []
    assert len(session.start_calls) == 1
    call = session.start_calls[0]
    assert isinstance(call["agent"], IntroAgent)
    assert call["agent"]._question is REVERSE_LINKED_LIST_QUESTION
    assert call["agent"].chat_ctx.items == []
    assert call["room"] is room
    assert call["room_options"] is room_options


@pytest.mark.asyncio
async def test_coding_mode_starts_with_seeded_approach_and_approval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = RecordingAgentSession()
    room = object()
    room_options = object()

    def unexpected_agent(*args: object, **kwargs: object) -> None:
        raise AssertionError("intro/discussion agents must not be constructed")

    monkeypatch.setattr(agent_module, "IntroAgent", unexpected_agent)
    monkeypatch.setattr(
        agent_module,
        "DiscussionAgent",
        unexpected_agent,
        raising=False,
    )

    await agent_module.start_interview(
        agent_session=session,
        room=room,
        room_options=room_options,
        start_stage="coding",
    )

    assert session.events == [
        "session_started",
        "approval_spoken",
        "approval_played",
    ]
    assert session.say_calls == [
        (
            "That approach works. Go ahead and start implementing it.",
            {"allow_interruptions": False},
        )
    ]
    assert len(session.start_calls) == 1
    coding = session.start_calls[0]["agent"]
    assert isinstance(coding, CodingAgent)
    assert coding._question is REVERSE_LINKED_LIST_QUESTION
    assert [(item.role, item.text_content) for item in coding.chat_ctx.items] == [
        (
            "user",
            "Use a dummy head and a tail pointer. Compare the current nodes from "
            "both sorted lists, link the smaller node to the tail, and advance "
            "that list. When one list is exhausted, attach the other list and "
            "return dummy.next.",
        )
    ]
    assert session.start_calls[0]["room"] is room
    assert session.start_calls[0]["room_options"] is room_options


def test_process_wide_start_stage_was_loaded_at_module_startup() -> None:
    assert agent_module.INTERVIEW_START_STAGE in {"intro", "coding"}
