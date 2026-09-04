import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from code_submission import CodeSubmission, LocalCodeSubmissionStore


def make_submission(**overrides: object) -> CodeSubmission:
    values: dict[str, object] = {
        "job_id": "job-123",
        "room_name": "interview-room",
        "question_slug": "reverse-linked-list",
        "question_title": "Reverse Linked List",
        "programming_language": "python",
        "code": "def reverse(head):\n    return head",
        "submitted_at": datetime(2026, 9, 4, 19, 30, 45, tzinfo=UTC),
    }
    values.update(overrides)
    return CodeSubmission(**values)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_local_store_creates_logs_directory_and_writes_formatted_json(
    tmp_path: Path,
) -> None:
    store = LocalCodeSubmissionStore(repository_root=tmp_path)

    path = await store.save(make_submission())

    assert path == tmp_path / "logs" / "code_submission_1_09042026.json"
    assert json.loads(path.read_text()) == {
        "job_id": "job-123",
        "room_name": "interview-room",
        "question_slug": "reverse-linked-list",
        "question_title": "Reverse Linked List",
        "programming_language": "python",
        "code": "def reverse(head):\n    return head",
        "submitted_at": "2026-09-04T19:30:45Z",
    }
    assert path.read_text().endswith("\n")
    assert '\n  "job_id"' in path.read_text()


@pytest.mark.asyncio
async def test_local_store_omits_unavailable_optional_metadata(tmp_path: Path) -> None:
    store = LocalCodeSubmissionStore(repository_root=tmp_path)

    path = await store.save(
        make_submission(job_id=None, room_name=None, programming_language=None)
    )

    payload = json.loads(path.read_text())
    assert "job_id" not in payload
    assert "room_name" not in payload
    assert "programming_language" not in payload


@pytest.mark.asyncio
async def test_local_store_uses_exclusive_sequential_filename_on_collision(
    tmp_path: Path,
) -> None:
    logs = tmp_path / "logs"
    logs.mkdir()
    existing = logs / "code_submission_1_09042026.json"
    existing.write_text("do not replace")
    store = LocalCodeSubmissionStore(repository_root=tmp_path)

    path = await store.save(make_submission())

    assert path.name == "code_submission_2_09042026.json"
    assert existing.read_text() == "do not replace"


@pytest.mark.asyncio
async def test_local_store_never_overwrites_multiple_submissions(
    tmp_path: Path,
) -> None:
    store = LocalCodeSubmissionStore(repository_root=tmp_path)

    first = await store.save(make_submission(code="first"))
    second = await store.save(make_submission(code="second"))
    third = await store.save(make_submission(code="third"))

    assert [first.name, second.name, third.name] == [
        "code_submission_1_09042026.json",
        "code_submission_2_09042026.json",
        "code_submission_3_09042026.json",
    ]
    assert json.loads(first.read_text())["code"] == "first"
    assert json.loads(second.read_text())["code"] == "second"
    assert json.loads(third.read_text())["code"] == "third"
