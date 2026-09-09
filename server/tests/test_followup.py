"""Offline lifecycle checks with real local storage and controlled model/RPC input."""

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from livekit.agents import AgentSession, ChatContext, ToolError
from pydantic import ValidationError
from test_agents import make_question
from test_coding_agent import Session, attach

import agents.coding as coding_module
import agents.coding_tools as coding_tools
import agents.followup as agent_module
import agents.followup_coding as task_module
import followup as contracts
import followup_selector as selector
from agents.coding import CodingAgent
from agents.conclusion import ConclusionAgent
from agents.followup import FollowUpAgent
from agents.followup_coding import FollowUpCodingTask
from code_submission import CodeSubmission, LocalCodeSubmissionStore
from followup import CodingOutcome, FollowUpPlan
from interview_context import InterviewContext


def make_plan(mode="discuss_then_code"):
    return FollowUpPlan(
        mode=mode,
        kind="constraint_change",
        objective="Assess input preservation",
        opening_question=None if mode == "none" else "What if inputs cannot change?",
        assessment_rubric=() if mode == "none" else ("Preserves both inputs",),
        coding_requirement="Preserve the input lists."
        if mode == "discuss_then_code"
        else None,
    )


@pytest.fixture(autouse=True)
def isolate_io(monkeypatch, tmp_path):
    # Keep real audit files out of the user's dogfooding logs.
    monkeypatch.setattr(contracts, "__file__", str(tmp_path / "server/src/followup.py"))

    def unexpected_model(**kwargs):
        pytest.fail("Follow-up tests must never create a live model client")

    monkeypatch.setattr(selector, "build_interview_llm", unexpected_model)


@pytest.fixture
async def saved_primary(tmp_path):
    interview = InterviewContext(programming_language="python", job_id="job-1")
    store = LocalCodeSubmissionStore(tmp_path)
    submission = CodeSubmission(
        question_slug="injected-question",
        question_title="Injected Question",
        code="original accepted code",
        submitted_at=datetime.now(UTC),
        submission_id="primary-1",
        version=1,
        job_id="job-1",
        programming_language="python",
    )
    path = await store.save(submission)
    interview.followup.primary_submission = submission
    interview.followup.primary_submission_path = str(path)
    return interview, store, path


@pytest.mark.parametrize("mode", ["none", "discuss", "discuss_then_code"])
async def test_primary_saves_before_selection_and_repeated_submission_reuses_result(
    mode,
    monkeypatch,
    tmp_path,
):
    interview = InterviewContext()
    state = interview.followup
    store = LocalCodeSubmissionStore(tmp_path)
    rpc = AsyncMock(return_value="accepted code")
    monkeypatch.setattr(coding_module, "get_current_editor_code", rpc)

    async def request(question, selected_state, history):
        assert selected_state is state
        assert state.primary_submission.version == 1
        assert (
            json.loads(Path(state.primary_submission_path).read_text())["code"]
            == "accepted code"
        )
        return make_plan(mode)

    model = AsyncMock(side_effect=request)
    monkeypatch.setattr(selector, "_request_plan", model)
    agent = CodingAgent(question=make_question(), submission_store=store)
    attach(agent, Session())
    context = SimpleNamespace(userdata=interview)

    result = await agent.submit_code(context)
    assert isinstance(result, ConclusionAgent if mode == "none" else FollowUpAgent)
    assert await agent.submit_code(context) is result
    rpc.assert_awaited_once()
    model.assert_awaited_once()
    assert state.selector_completed and state.selector_failure is None
    assert len(list((tmp_path / "logs").glob("code_submission_*.json"))) == 1


@pytest.mark.parametrize("failure", [TimeoutError(), RuntimeError("provider failed")])
async def test_selector_failure_concludes_without_retry_or_losing_primary(
    failure,
    saved_primary,
    monkeypatch,
):
    interview, store, path = saved_primary
    before = path.read_bytes()
    model = AsyncMock(side_effect=failure)
    monkeypatch.setattr(selector, "_request_plan", model)
    agent = CodingAgent(question=make_question(), submission_store=store)
    attach(agent, Session())

    assert isinstance(
        await agent.submit_code(SimpleNamespace(userdata=interview)), ConclusionAgent
    )
    state = interview.followup
    assert state.selector_completed
    assert state.selector_failure == type(failure).__name__
    assert state.plan is None  # Distinct from a validated plan with mode=none.
    assert await selector.select_followup(make_question(), state, ChatContext()) is None
    model.assert_awaited_once()
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    "overrides",
    [
        {"mode": "discuss", "coding_requirement": "Write code"},
        {"coding_requirement": None},
        {"assessment_rubric": []},
        {"objective": " "},
        {"mode": "unknown"},
    ],
)
def test_plan_rejects_invalid_execution_contracts(overrides):
    with pytest.raises(ValidationError):
        FollowUpPlan.model_validate({**make_plan().model_dump(), **overrides})


async def test_discussion_cannot_launch_coding_and_opening_is_not_repeated(
    saved_primary,
):
    interview, store, _ = saved_primary
    state = interview.followup
    state.plan = make_plan("discuss")
    agent = FollowUpAgent(
        question=make_question(), plan=state.plan, state=state, submission_store=store
    )
    session = Session()
    attach(agent, session)
    assert {tool.info.name for tool in agent.tools} == {"finish_followup"}
    await agent.on_enter()
    await agent.on_enter()
    assert len(session.spoken) == 1
    with pytest.raises(ToolError):
        await agent.start_coding(SimpleNamespace(userdata=interview))
    assert not state.coding_started
    result = await agent.finish_followup(
        None, "demonstrated", ["Explained preservation"]
    )
    assert isinstance(result, ConclusionAgent)
    assert state.consumed and state.discussion_status == "demonstrated"


async def test_verbal_success_cannot_waive_required_code(saved_primary):
    interview, store, _ = saved_primary
    state = interview.followup
    state.plan = make_plan()
    agent = FollowUpAgent(
        question=make_question(), plan=state.plan, state=state, submission_store=store
    )
    with pytest.raises(ToolError, match="requires implementation"):
        await agent.finish_followup(
            None, "demonstrated", ["Excellent verbal reasoning"]
        )
    assert not state.consumed
    assert isinstance(
        await agent.finish_followup(None, "unable", ["Declined coding"]),
        ConclusionAgent,
    )


def make_task(interview, store):
    state = interview.followup
    state.plan = make_plan()
    state.coding_started = True
    return FollowUpCodingTask(
        question=make_question(),
        plan=state.plan,
        state=state,
        chat_ctx=ChatContext(),
        submission_store=store,
    )


@pytest.mark.parametrize("first_to_finish", ["speech", "selection", "cancel"])
async def test_transition_speech_overlaps_selection_and_waits_for_both(
    first_to_finish,
    saved_primary,
    monkeypatch,
):
    interview, store, _ = saved_primary
    speech_started, selection_started = asyncio.Event(), asyncio.Event()
    release_speech, release_selection = asyncio.Event(), asyncio.Event()
    speech_finished, selection_finished = asyncio.Event(), asyncio.Event()

    class PendingSpeech:
        async def wait_for_playout(self):
            speech_started.set()
            await release_speech.wait()
            speech_finished.set()

    async def request(*args):
        selection_started.set()
        try:
            await release_selection.wait()
            return make_plan("discuss")
        finally:
            selection_finished.set()

    monkeypatch.setattr(selector, "_request_plan", request)
    session = Session()
    monkeypatch.setattr(session, "say", lambda *args, **kwargs: PendingSpeech())
    agent = CodingAgent(question=make_question(), submission_store=store)
    attach(agent, session)
    pending = asyncio.create_task(
        agent.submit_code(SimpleNamespace(userdata=interview))
    )
    try:
        await asyncio.wait_for(
            asyncio.gather(
                speech_started.wait(),
                selection_started.wait(),
            ),
            timeout=2,
        )
        if first_to_finish == "cancel":
            pending.cancel()
            with pytest.raises(asyncio.CancelledError):
                await pending
            assert selection_finished.is_set()
            assert interview.followup.selector_failure == "cancelled"
            return
        if first_to_finish == "speech":
            release_speech.set()
            await asyncio.wait_for(speech_finished.wait(), timeout=2)
        else:
            release_selection.set()
            await asyncio.wait_for(selection_finished.wait(), timeout=2)
        assert not pending.done()  # Neither result alone permits the handoff.
        release_speech.set()
        release_selection.set()
        assert isinstance(await asyncio.wait_for(pending, timeout=2), FollowUpAgent)
        assert session.generated == []  # The filler adds no LLM request.
    finally:
        if not pending.done():
            pending.cancel()
        await asyncio.gather(pending, return_exceptions=True)


@pytest.mark.parametrize(
    "status", ["demonstrated", "partial", "unable", "time_expired"]
)
async def test_task_preserves_v1_and_saves_separate_v2_once(
    status,
    saved_primary,
    monkeypatch,
):
    interview, store, primary_path = saved_primary
    original = primary_path.read_bytes()
    task = make_task(interview, store)
    rpc = AsyncMock(return_value="extension code")
    monkeypatch.setattr(coding_tools, "get_current_editor_code", rpc)
    monkeypatch.setattr(task_module, "get_current_editor_code", rpc)
    context = SimpleNamespace(userdata=interview)
    await task.get_current_code(context)
    await task.finish_exercise(context, status, ["Observed candidate attempt"])
    outcome = interview.followup.coding_outcome
    assert isinstance(outcome, CodingOutcome) and task.done()
    assert outcome.status == status and outcome.final_code == "extension code"
    assert outcome.evidence_error is None
    assert primary_path.read_bytes() == original
    versions = [
        json.loads(p.read_text())
        for p in primary_path.parent.glob("code_submission_*.json")
    ]
    assert sorted(v["version"] for v in versions) == [1, 2]
    extension = next(v for v in versions if v["version"] == 2)
    assert extension["primary_submission_id"] == "primary-1"
    assert extension["followup_id"] == interview.followup.followup_id
    assert extension["submission_id"] == outcome.submission_id != "primary-1"
    with pytest.raises(ToolError):
        await task.finish_exercise(context, status, [])
    assert len(list(primary_path.parent.glob("code_submission_*.json"))) == 2


async def test_changed_editor_requires_another_review_before_success(
    saved_primary, monkeypatch
):
    interview, store, primary_path = saved_primary
    task = make_task(interview, store)
    monkeypatch.setattr(
        coding_tools, "get_current_editor_code", AsyncMock(return_value="reviewed")
    )
    monkeypatch.setattr(
        task_module, "get_current_editor_code", AsyncMock(return_value="changed")
    )
    await task.get_current_code(None)
    with pytest.raises(ToolError, match="review"):
        await task.finish_exercise(None, "demonstrated", [])
    assert not task.done() and interview.followup.coding_outcome is None
    assert len(list(primary_path.parent.glob("code_submission_*.json"))) == 1


@pytest.mark.parametrize("failure", ["editor", "storage"])
async def test_evidence_failure_is_explicit_and_still_returns_an_outcome(
    failure,
    saved_primary,
    monkeypatch,
):
    interview, store, primary_path = saved_primary
    original = primary_path.read_bytes()
    task = make_task(interview, store)
    monkeypatch.setattr(
        task_module,
        "get_current_editor_code",
        AsyncMock(
            return_value="partial code",
            side_effect=ValueError("unavailable") if failure == "editor" else None,
        ),
    )
    if failure == "storage":
        monkeypatch.setattr(store, "save", AsyncMock(side_effect=OSError("disk full")))
    await task.finish_exercise(None, "partial", ["Could not finish"])
    outcome = interview.followup.coding_outcome
    assert outcome.evidence_error and outcome.submission_id is None
    assert outcome.final_code == (None if failure == "editor" else "partial code")
    assert task.done() and primary_path.read_bytes() == original


async def test_real_livekit_task_resumes_same_parent_and_concludes_once(
    saved_primary,
    monkeypatch,
):
    """Use the actual SDK pause/resume lifecycle, with no LLM, room, or audio."""
    interview, store, _ = saved_primary
    state = interview.followup
    state.plan = make_plan()
    finished = asyncio.Event()
    captured = {}
    monkeypatch.setattr(
        task_module, "get_current_editor_code", AsyncMock(return_value="partial code")
    )

    class CompletingTask(FollowUpCodingTask):
        async def on_enter(self):
            captured["task"] = self
            captured["history"] = self.chat_ctx.copy()
            await self.finish_exercise(None, "partial", ["Candidate stopped"])

    class StartingParent(FollowUpAgent):
        async def on_enter(self):
            try:
                captured["conclusion"] = await self.start_coding(None)
                captured["resumed"] = self.session.current_agent
            finally:
                finished.set()

    monkeypatch.setattr(agent_module, "FollowUpCodingTask", CompletingTask)
    parent = StartingParent(
        question=make_question(), plan=state.plan, state=state, submission_store=store
    )
    async with AgentSession(userdata=interview) as session:
        session.output.set_audio_enabled(False)
        await session.start(parent)
        await asyncio.wait_for(finished.wait(), timeout=5)
        assert captured["resumed"] is parent
        assert isinstance(captured["conclusion"], ConclusionAgent)
        assert state.coding_outcome.evidence_error is None
        assert state.coding_outcome.status == "partial" and state.consumed
        assert captured["task"].done()
        assert any(
            state.plan.coding_requirement in item.text_content
            for item in captured["history"].items
            if item.type == "message"
        )
        assert not state.selector_started
        with pytest.raises(ToolError):
            await parent.start_coding(None)
        assert state.plan is parent._plan


@pytest.mark.parametrize("valid", [True, False])
async def test_selector_uses_silent_strict_request_and_rejects_invalid_output(
    valid,
    saved_primary,
    monkeypatch,
):
    interview, _, path = saved_primary
    state = interview.followup
    request = {}
    closed = []
    expected = make_plan("discuss")
    raw = expected.model_dump_json() if valid else '{"mode":"discuss_then_code"}'

    async def chunks():
        # Exercise streaming assembly, not just validation of a ready-made plan.
        for text in (raw[:10], raw[10:]):
            yield SimpleNamespace(delta=SimpleNamespace(content=text))

    @asynccontextmanager
    async def stream(**kwargs):
        request.update(kwargs)
        try:
            yield chunks()
        finally:
            closed.append("stream")

    @asynccontextmanager
    async def model(**kwargs):
        assert kwargs == {"use_websocket": False}
        try:
            yield SimpleNamespace(chat=stream)
        finally:
            closed.append("model")

    monkeypatch.setattr(selector, "build_interview_llm", model)
    history = ChatContext()
    history.add_message(role="system", content="Old stage instructions")
    history.add_message(role="user", content="Time O(n), auxiliary space O(1).")
    result = await selector.select_followup(make_question(), state, history)
    assert closed == ["stream", "model"]
    assert request["tools"] == [] and request["tool_choice"] == "none"
    assert request["conn_options"].max_retry == 0
    assert request["extra_kwargs"]["reasoning"] == {"effort": "low"}
    assert request["extra_kwargs"]["max_output_tokens"] == 1500
    assert request["extra_kwargs"]["text"]["format"]["strict"] is True
    payload = json.loads(request["chat_ctx"].items[-1].text_content)
    assert payload["accepted_primary_code"] == "original accepted code"
    assert payload["conversation"] == [
        {"role": "user", "text": "Time O(n), auxiliary space O(1)."}
    ]
    assert len(history.items) == 2  # Selection never writes to spoken history.
    assert state.selector_completed
    if valid:
        assert result == expected and state.selector_failure is None
    else:
        assert result is None and state.selector_failure == "ValidationError"
        events = [
            json.loads(line)
            for line in (path.parent / f"followup_{state.followup_id}.jsonl")
            .read_text()
            .splitlines()
        ]
        failure = next(event for event in events if event["event"] == "selector_failed")
        assert failure["validation_errors"]
        assert all("input" not in error for error in failure["validation_errors"])


async def test_overlapping_coding_launch_and_early_finish_are_blocked(
    saved_primary, monkeypatch
):
    interview, store, _ = saved_primary
    state = interview.followup
    state.plan = make_plan()
    parent = FollowUpAgent(
        question=make_question(), plan=state.plan, state=state, submission_store=store
    )
    entered = asyncio.Event()
    release = asyncio.Event()
    outcome = CodingOutcome(status="unable")

    async def exercise(**kwargs):
        entered.set()
        await release.wait()
        return outcome

    task = AsyncMock(side_effect=exercise)
    monkeypatch.setattr(agent_module, "FollowUpCodingTask", task)
    session = Session()
    session.current_agent = parent
    attach(parent, session)
    first = asyncio.create_task(parent.start_coding(None))
    try:
        await asyncio.wait_for(entered.wait(), timeout=2)
        with pytest.raises(ToolError):
            await parent.start_coding(None)
        with pytest.raises(ToolError, match="still active"):
            await parent.finish_followup(None, "unable", [])
    finally:
        release.set()
        result = await first
    assert isinstance(result, ConclusionAgent)
    task.assert_awaited_once()
    assert state.coding_outcome is outcome and state.consumed
