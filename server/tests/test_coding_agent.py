import logging
from types import SimpleNamespace

import pytest
from livekit import rtc
from livekit.agents import ChatContext, ChatMessage, StopResponse
from test_agents import make_question

from agents.coding import CodingAgent
from agents.conclusion import ConclusionAgent
from agents.discussion import DiscussionAgent
from agents.prompts import CODING_PROMPT, REVERSE_LINKED_LIST_QUESTION
from interview_question import build_discussion_question_context


class Speech:
    def __init__(self, events: list[str], label: str) -> None:
        self.events = events
        self.label = label

    async def wait_for_playout(self) -> None:
        self.events.append(f"wait:{self.label}")


class Session:
    def __init__(self) -> None:
        self.events: list[str] = []
        self.spoken: list[tuple[str, dict[str, object]]] = []
        self.generated: list[tuple[str, dict[str, object]]] = []

    def say(self, text: str, **kwargs: object) -> Speech:
        self.events.append(f"say:{text}")
        self.spoken.append((text, kwargs))
        return Speech(self.events, f"say:{text}")

    def generate_reply(self, *, instructions: str, **kwargs: object) -> Speech:
        self.events.append("generate_reply")
        self.generated.append((instructions, kwargs))
        return Speech(self.events, "generate_reply")


def attach(agent: object, session: Session) -> None:
    agent._activity = SimpleNamespace(session=session)  # type: ignore[attr-defined]


def test_coding_agent_has_exact_prompt_context_and_tools() -> None:
    agent = CodingAgent()

    assert CODING_PROMPT in agent.instructions
    assert (
        build_discussion_question_context(REVERSE_LINKED_LIST_QUESTION)
        in agent.instructions
    )
    assert {tool.info.name for tool in agent.tools} == {
        "continue_silently",
        "get_current_code",
        "finish_coding",
    }
    assert agent.allow_interruptions is False
    assert "on_enter" not in CodingAgent.__dict__


def test_coding_prompt_requires_fresh_code_for_current_code_judgments() -> None:
    assert "mandatory before responding" in CODING_PROMPT
    assert "inspect,\n  validate, review, debug, or judge" in CODING_PROMPT
    assert "likely to pass tests" in CODING_PROMPT
    assert "Why isn't my loop working?" in CODING_PROMPT
    assert "I think this is my\n  implementation" in CODING_PROMPT


@pytest.mark.asyncio
async def test_continue_silently_stops_without_speech() -> None:
    agent = CodingAgent()
    session = Session()
    attach(agent, session)

    with pytest.raises(StopResponse):
        await agent.continue_silently.__wrapped__(agent, None)

    assert session.events == []
    assert session.spoken == []
    assert session.generated == []


@pytest.mark.asyncio
async def test_get_current_code_requests_the_single_standard_participant(
    caplog: pytest.LogCaptureFixture,
) -> None:
    agent = CodingAgent()

    async def perform_rpc(**kwargs: object) -> str:
        assert kwargs == {
            "destination_identity": "candidate",
            "method": "editor.get_current_code",
            "payload": "",
            "response_timeout": 3.0,
        }
        return "def solve():\n    return 42"

    room = SimpleNamespace(
        local_participant=SimpleNamespace(perform_rpc=perform_rpc),
        remote_participants={
            "candidate": SimpleNamespace(
                identity="candidate",
                kind=rtc.ParticipantKind.PARTICIPANT_KIND_STANDARD,
            )
        },
    )
    context = SimpleNamespace(
        session=SimpleNamespace(room_io=SimpleNamespace(room=room))
    )

    with caplog.at_level(logging.INFO, logger="agents.coding"):
        code = await agent.get_current_code.__wrapped__(agent, context)

    assert code == "def solve():\n    return 42"
    rpc_records = [
        record
        for record in caplog.records
        if record.message.startswith("Current editor code RPC")
    ]
    assert [record.message for record in rpc_records] == [
        "Current editor code RPC started",
        "Current editor code RPC succeeded",
    ]
    assert rpc_records[0].identity == "candidate"
    assert rpc_records[1].identity == "candidate"
    assert rpc_records[1].code_bytes == len(code.encode("utf-8"))


@pytest.mark.asyncio
async def test_get_current_code_maps_rpc_errors_to_an_unavailable_code_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    agent = CodingAgent()

    async def perform_rpc(**_: object) -> str:
        raise rtc.RpcError(rtc.RpcError.ErrorCode.RESPONSE_TIMEOUT, "timed out")

    room = SimpleNamespace(
        local_participant=SimpleNamespace(perform_rpc=perform_rpc),
        remote_participants={
            "candidate": SimpleNamespace(
                identity="candidate",
                kind=rtc.ParticipantKind.PARTICIPANT_KIND_STANDARD,
            )
        },
    )
    context = SimpleNamespace(
        session=SimpleNamespace(room_io=SimpleNamespace(room=room))
    )

    with (
        caplog.at_level(logging.INFO, logger="agents.coding"),
        pytest.raises(ValueError, match="Candidate code is unavailable"),
    ):
        await agent.get_current_code.__wrapped__(agent, context)

    failed_record = next(
        record
        for record in caplog.records
        if record.message == "Current editor code RPC failed"
    )
    assert failed_record.identity == "candidate"
    assert failed_record.duration_ms >= 0
    assert failed_record.error_type == "RpcError"


@pytest.mark.asyncio
async def test_finish_coding_confirms_after_playout_and_hands_off_to_conclusion() -> (
    None
):
    agent = CodingAgent()
    session = Session()
    attach(agent, session)

    conclusion = await agent.finish_coding.__wrapped__(agent, None)

    assert isinstance(conclusion, ConclusionAgent)
    assert session.spoken == [
        ("Yep, this implementation looks good to go.", {"allow_interruptions": False})
    ]
    assert session.events == [
        "say:Yep, this implementation looks good to go.",
        "wait:say:Yep, this implementation looks good to go.",
    ]


@pytest.mark.asyncio
async def test_start_coding_speaks_and_hands_off_with_question_and_copied_context() -> (
    None
):
    question = make_question()
    chat_ctx = ChatContext(
        items=[
            ChatMessage(role="system", content=["discarded instructions"]),
            ChatMessage(role="user", content=["prior turn"]),
        ]
    )
    agent = DiscussionAgent(question=question, chat_ctx=chat_ctx)
    session = Session()
    attach(agent, session)

    coding = await agent.start_coding.__wrapped__(agent, None)

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
    assert isinstance(coding, CodingAgent)
    assert coding._question is question
    assert coding._question is agent._question
    assert coding.chat_ctx is not chat_ctx
    assert [(item.role, item.content) for item in coding.chat_ctx.items] == [
        ("user", ["prior turn"])
    ]
