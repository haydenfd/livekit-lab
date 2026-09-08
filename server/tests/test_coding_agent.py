import logging
from pathlib import Path
from types import SimpleNamespace

import pytest
from livekit import rtc
from livekit.agents import ChatContext, ChatMessage, StopResponse
from test_agents import make_question

import agents.coding as coding_module
from agents.coding import CodingAgent
from agents.discussion import DiscussionAgent
from code_submission import CodeSubmission
from followup import FollowUpPlan
from interview_context import InterviewContext


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


class RecordingStore:
    def __init__(self, events: list[str], error: Exception | None = None) -> None:
        self.events = events
        self.error = error
        self.submissions: list[CodeSubmission] = []

    async def save(self, submission: CodeSubmission) -> Path:
        self.events.append("store:start")
        if self.error is not None:
            raise self.error
        self.submissions.append(submission)
        self.events.append("store:complete")
        return Path("submission.json")


def attach(agent: object, session: Session) -> None:
    agent._activity = SimpleNamespace(session=session)  # type: ignore[attr-defined]


def test_coding_agent_has_expected_tools_and_config() -> None:
    agent = CodingAgent()

    assert {tool.info.name for tool in agent.tools} == {
        "continue_silently",
        "get_current_code",
        "submit_code",
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
async def test_submit_code_persists_fresh_rpc_result_before_acknowledgment_and_handoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    rpc_results = iter(["stale review snapshot", "final editor contents"])

    async def perform_rpc(**_: object) -> str:
        events.append("rpc")
        return next(rpc_results)

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
        session=SimpleNamespace(room_io=SimpleNamespace(room=room)),
        userdata=InterviewContext(
            programming_language="python",
            job_id="job-123",
            room_name="interview-room",
        ),
    )
    store = RecordingStore(events)
    agent = CodingAgent(question=make_question(), submission_store=store)
    session = Session()
    session.events = events
    attach(agent, session)

    await agent.get_current_code.__wrapped__(agent, context)

    sentinel = object()

    def construct_conclusion() -> object:
        events.append("conclusion")
        return sentinel

    monkeypatch.setattr(coding_module, "ConclusionAgent", construct_conclusion)

    async def select_no_followup(*_: object) -> FollowUpPlan:
        events.append("selector")
        return FollowUpPlan(
            mode="none",
            kind=None,
            objective=None,
            opening_question=None,
            assessment_rubric=(),
            coding_requirement=None,
        )

    # Keep this existing transition check offline after adding the selector.
    monkeypatch.setattr(coding_module, "select_followup", select_no_followup)

    conclusion = await agent.submit_code.__wrapped__(agent, context)

    assert conclusion is sentinel
    assert events == [
        "rpc",
        "rpc",
        "store:start",
        "store:complete",
        f"say:{coding_module.FOLLOWUP_TRANSITION}",
        f"wait:say:{coding_module.FOLLOWUP_TRANSITION}",
        "selector",
        "conclusion",
    ]
    assert len(store.submissions) == 1
    assert store.submissions[0].code == "final editor contents"
    assert store.submissions[0].job_id == "job-123"
    assert store.submissions[0].room_name == "interview-room"
    assert store.submissions[0].question_slug == "injected-question"
    assert store.submissions[0].question_title == "Injected Question"
    assert store.submissions[0].programming_language == "python"
    assert store.submissions[0].submitted_at.tzinfo is not None
    assert session.spoken == [
        (coding_module.FOLLOWUP_TRANSITION, {"allow_interruptions": False})
    ]
    assert session.generated == []


@pytest.mark.asyncio
async def test_submit_code_retrieval_failure_does_not_store_acknowledge_or_handoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    async def perform_rpc(**_: object) -> str:
        events.append("rpc")
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
        session=SimpleNamespace(room_io=SimpleNamespace(room=room)),
        userdata=InterviewContext(),
    )
    store = RecordingStore(events)
    agent = CodingAgent(submission_store=store)
    session = Session()
    session.events = events
    attach(agent, session)
    monkeypatch.setattr(
        coding_module,
        "ConclusionAgent",
        lambda: pytest.fail("retrieval failure must not construct ConclusionAgent"),
    )

    with pytest.raises(ValueError, match="Candidate code is unavailable"):
        await agent.submit_code.__wrapped__(agent, context)

    assert events == ["rpc"]
    assert store.submissions == []
    assert session.generated == []


@pytest.mark.asyncio
async def test_submit_code_storage_failure_is_logged_and_sanitized_without_handoff(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    events: list[str] = []

    async def perform_rpc(**_: object) -> str:
        events.append("rpc")
        return "final code"

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
        session=SimpleNamespace(room_io=SimpleNamespace(room=room)),
        userdata=InterviewContext(),
    )
    store = RecordingStore(events, error=OSError("private filesystem details"))
    agent = CodingAgent(submission_store=store)
    session = Session()
    session.events = events
    attach(agent, session)
    monkeypatch.setattr(
        coding_module,
        "ConclusionAgent",
        lambda: pytest.fail("storage failure must not construct ConclusionAgent"),
    )

    with (
        caplog.at_level(logging.ERROR, logger="agents.coding"),
        pytest.raises(ValueError, match="Code submission could not be saved"),
    ):
        await agent.submit_code.__wrapped__(agent, context)

    assert events == ["rpc", "store:start"]
    assert session.generated == []
    assert "Code submission storage failed" in caplog.messages


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
