import json
import logging
from types import SimpleNamespace

import pytest

from services.transcription_service import TranscriptionService


def message(
    *,
    message_id: str,
    role: str,
    text: str,
    created_at: float = 0,
    interrupted: bool = False,
    transcript_confidence: float | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=message_id,
        type="message",
        role=role,
        text_content=text,
        created_at=created_at,
        interrupted=interrupted,
        transcript_confidence=transcript_confidence,
    )


def report() -> SimpleNamespace:
    return SimpleNamespace(
        job_id="job-123", room="interview-room", timestamp=1_700_000_000
    )


def test_build_payload_keeps_only_spoken_messages() -> None:
    service = TranscriptionService()
    history = SimpleNamespace(
        items=[
            message(message_id="system", role="system", text="Do not save this"),
            message(
                message_id="user-1",
                role="user",
                text="  I would use binary search.  ",
                created_at=1,
                transcript_confidence=0.98,
            ),
            SimpleNamespace(type="function_call", name="search"),
            SimpleNamespace(type="agent_handoff", agent_name="conclusion"),
            message(
                message_id="assistant-1",
                role="assistant",
                text="That is correct.",
                created_at=2,
                interrupted=True,
            ),
            message(message_id="empty", role="user", text="   ", created_at=3),
        ]
    )

    payload = service.build_payload(report(), history)

    assert payload == {
        "job_id": "job-123",
        "room_name": "interview-room",
        "report_timestamp": "2023-11-14T22:13:20Z",
        "transcript": [
            {
                "id": "user-1",
                "role": "user",
                "text": "I would use binary search.",
                "timestamp": "1970-01-01T00:00:01Z",
                "interrupted": False,
                "transcript_confidence": 0.98,
            },
            {
                "id": "assistant-1",
                "role": "assistant",
                "text": "That is correct.",
                "timestamp": "1970-01-01T00:00:02Z",
                "interrupted": True,
            },
        ],
    }


def test_persist_writes_metadata_and_transcript(tmp_path) -> None:
    service = TranscriptionService(output_dir=tmp_path)
    history = SimpleNamespace(
        items=[message(message_id="user-1", role="user", text="Hello", created_at=1)]
    )

    output_path = service.persist(report(), history)

    assert output_path.name == "session_1_11142023.json"
    assert json.loads(output_path.read_text()) == {
        "job_id": "job-123",
        "room_name": "interview-room",
        "report_timestamp": "2023-11-14T22:13:20Z",
        "transcript": [
            {
                "id": "user-1",
                "role": "user",
                "text": "Hello",
                "timestamp": "1970-01-01T00:00:01Z",
                "interrupted": False,
            }
        ],
    }


def test_persist_uses_the_next_global_sequence_number(tmp_path) -> None:
    (tmp_path / "session_3_01012026.json").touch()
    (tmp_path / "session_12_01012026.json").touch()
    (tmp_path / "unrelated.json").touch()
    service = TranscriptionService(output_dir=tmp_path)

    output_path = service.persist(report(), SimpleNamespace(items=[]))

    assert output_path.name == "session_13_11142023.json"
    assert (tmp_path / "session_12_01012026.json").exists()


@pytest.mark.asyncio
async def test_register_builds_final_report_and_saves_once(tmp_path) -> None:
    service = TranscriptionService(output_dir=tmp_path)
    session = SimpleNamespace(history=SimpleNamespace(items=[]))
    callbacks = []

    class JobContext:
        def add_shutdown_callback(self, callback) -> None:
            callbacks.append(callback)

        def make_session_report(self, received_session):
            assert received_session is session
            return report()

    service.register(JobContext(), session)

    assert len(callbacks) == 1
    await callbacks[0]()
    assert [path.name for path in tmp_path.iterdir()] == ["session_1_11142023.json"]


@pytest.mark.asyncio
async def test_shutdown_logs_filesystem_error_without_raising(
    tmp_path, monkeypatch, caplog
) -> None:
    service = TranscriptionService(output_dir=tmp_path)
    session = SimpleNamespace(history=SimpleNamespace(items=[]))
    callbacks = []

    class JobContext:
        def add_shutdown_callback(self, callback) -> None:
            callbacks.append(callback)

        def make_session_report(self, received_session):
            return report()

    def raise_filesystem_error(*_args) -> None:
        raise OSError("disk is read-only")

    monkeypatch.setattr(service, "persist", raise_filesystem_error)
    service.register(JobContext(), session)

    with caplog.at_level(logging.ERROR):
        await callbacks[0]()

    assert "Failed to save transcript" in caplog.text
