"""Durable storage for code accepted during an interview."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class CodeSubmission:
    """The editor snapshot and available metadata at acceptance time."""

    question_slug: str
    question_title: str
    code: str
    submitted_at: datetime
    job_id: str | None = None
    room_name: str | None = None
    programming_language: str | None = None


class CodeSubmissionStore(Protocol):
    """Persist accepted code before the interview can conclude."""

    async def save(self, submission: CodeSubmission) -> Path:
        """Save a submission without replacing an existing one."""
        ...


class LocalCodeSubmissionStore:
    """Store submissions as exclusive JSON files under repository-root logs."""

    def __init__(self, repository_root: Path | None = None) -> None:
        self._repository_root = repository_root or Path(__file__).resolve().parents[2]

    async def save(self, submission: CodeSubmission) -> Path:
        logs_directory = self._repository_root / "logs"
        logs_directory.mkdir(parents=True, exist_ok=True)

        payload = {
            key: value for key, value in asdict(submission).items() if value is not None
        }
        submitted_at = submission.submitted_at.astimezone(UTC)
        payload["submitted_at"] = submitted_at.isoformat().replace("+00:00", "Z")
        contents = json.dumps(payload, indent=2) + "\n"
        date = submitted_at.strftime("%m%d%Y")

        sequence = 1
        while True:
            path = logs_directory / f"code_submission_{sequence}_{date}.json"
            try:
                with path.open("x", encoding="utf-8") as file:
                    file.write(contents)
            except FileExistsError:
                sequence += 1
                continue
            return path
