import json
from types import SimpleNamespace

import pytest

import agent_session
from agents.intro import IntroAgent
from interview_context import InterviewContext


@pytest.mark.parametrize("language", ["python", "java", "javascript"])
def test_interview_context_accepts_any_string_programming_language(
    language: str,
) -> None:
    context = InterviewContext.from_dispatch_metadata(
        json.dumps({"programmingLanguage": language})
    )

    assert context.programming_language == language


@pytest.mark.parametrize(
    "metadata",
    [None, "", "not json", "[]", '{"programmingLanguage": 42}'],
)
def test_interview_context_ignores_missing_or_unusable_metadata(
    metadata: str | None,
) -> None:
    context = InterviewContext.from_dispatch_metadata(metadata)

    assert context.programming_language is None


def test_interview_context_retains_livekit_job_and_room_metadata() -> None:
    context = InterviewContext.from_dispatch_metadata(
        json.dumps({"programmingLanguage": "python"}),
        job_id="job-123",
        room_name="interview-room",
    )

    assert context == InterviewContext(
        programming_language="python",
        job_id="job-123",
        room_name="interview-room",
    )


def test_create_agent_session_receives_typed_interview_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    context = InterviewContext(programming_language="python")

    def fake_agent_session(**kwargs: object) -> object:
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(agent_session, "AgentSession", fake_agent_session)
    monkeypatch.setattr(agent_session, "build_agent_session_config", lambda: {})

    agent_session.create_agent_session(context)

    assert captured["userdata"] is context


class StubSpeechHandle:
    async def wait_for_playout(self) -> None:
        pass


class StubSession:
    def __init__(self, userdata: InterviewContext) -> None:
        self.userdata = userdata

    def generate_reply(self, **kwargs: object) -> StubSpeechHandle:
        return StubSpeechHandle()

    def say(self, text: str, **kwargs: object) -> StubSpeechHandle:
        return StubSpeechHandle()


@pytest.mark.asyncio
async def test_handoff_uses_the_same_session_userdata() -> None:
    context = InterviewContext(programming_language="python")
    intro = IntroAgent()
    intro._activity = SimpleNamespace(session=StubSession(context))  # type: ignore[attr-defined]

    discussion = await intro.move_to_discussion.__wrapped__(intro, None)
    discussion._activity = SimpleNamespace(session=StubSession(context))  # type: ignore[attr-defined]

    assert discussion.session.userdata is context
