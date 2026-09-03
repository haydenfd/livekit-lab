from types import SimpleNamespace

import pytest
from livekit import rtc
from livekit.agents import ChatContext, ChatMessage, StopResponse
from test_agents import make_question

from agents.coding import CodingAgent
from agents.conclusion import ConclusionAgent
from agents.discussion import DiscussionAgent
from agents.prompts import CODING_PROMPT, MERGE_TWO_SORTED_LISTS_QUESTION
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
    normalized_instructions = " ".join(agent.instructions.split())

    assert CODING_PROMPT in agent.instructions
    assert (
        build_discussion_question_context(MERGE_TWO_SORTED_LISTS_QUESTION)
        in agent.instructions
    )
    assert "pause between thoughts" not in agent.instructions
    assert "without expecting the interviewer to participate" in normalized_instructions
    assert "still an interviewer, not a coding assistant" in normalized_instructions
    assert (
        "factual problem clarifications directly and briefly" in normalized_instructions
    )
    assert (
        "do not reveal the solution or directly fix their code"
        in normalized_instructions
    )
    assert "one concise question or hint" in normalized_instructions
    assert (
        "Do not over-help merely because the candidate sounds confused"
        in normalized_instructions
    )
    assert (
        "Do not invent observations about code or implementation details"
        in normalized_instructions
    )
    assert "candidate's code" in agent.instructions
    assert (
        "use `get_current_code` before making any claim about editor contents"
        in normalized_instructions
    )
    assert (
        "Do not use it automatically for narration, pauses, or every candidate turn"
        in normalized_instructions
    )
    assert {tool.info.name for tool in agent.tools} == {
        "continue_silently",
        "get_current_code",
        "finish_coding",
    }
    assert agent.allow_interruptions is False
    assert "on_enter" not in CodingAgent.__dict__


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
async def test_get_current_code_requests_the_single_standard_participant() -> None:
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

    assert (
        await agent.get_current_code.__wrapped__(agent, context)
        == "def solve():\n    return 42"
    )


@pytest.mark.asyncio
async def test_get_current_code_maps_rpc_errors_to_an_unavailable_code_error() -> None:
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

    with pytest.raises(ValueError, match="Candidate code is unavailable"):
        await agent.get_current_code.__wrapped__(agent, context)


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
