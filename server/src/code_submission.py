"""Durable storage for code accepted during an interview."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, Protocol


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
    submission_id: str | None = None
    version: int | None = None
    primary_submission_id: str | None = None
    followup_id: str | None = None
    outcome: Literal["demonstrated", "partial", "unable", "time_expired"] | None = None

    def __post_init__(self) -> None:
        if self.version is None:
            return  # Legacy records remain readable/constructible.
        if self.version not in {1, 2} or not self.submission_id:
            raise ValueError("Versioned submissions require an ID and version 1 or 2.")
        if self.version == 1 and (self.primary_submission_id or self.followup_id):
            raise ValueError("Primary submissions cannot reference a follow-up.")
        if self.version == 2 and (
            not self.primary_submission_id
            or not self.followup_id
            or self.submission_id == self.primary_submission_id
        ):
            raise ValueError(
                "V2 requires a distinct ID and primary/follow-up references."
            )


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
