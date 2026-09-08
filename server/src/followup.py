"""Validated follow-up contracts and session-owned lifecycle state."""

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, model_validator

from code_submission import CodeSubmission

OutcomeStatus = Literal["demonstrated", "partial", "unable", "time_expired"]
logger = logging.getLogger(__name__)


class FollowUpPlan(BaseModel):
    """One fixed assessment; kind is descriptive and never controls routing."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    mode: Literal["none", "discuss", "discuss_then_code"]
    kind: str | None
    objective: str | None
    opening_question: str | None
    assessment_rubric: tuple[str, ...]
    coding_requirement: str | None

    @model_validator(mode="after")
    def validate_contract(self) -> "FollowUpPlan":
        if self.mode == "none":
            if self.coding_requirement is not None or self.opening_question is not None:
                raise ValueError("A none plan must not request an exercise.")
            return self
        if not self.objective or not self.objective.strip():
            raise ValueError("An assessment needs an objective.")
        if not self.opening_question or not self.opening_question.strip():
            raise ValueError("An assessment needs an opening question.")
        if not self.assessment_rubric or any(
            not item.strip() for item in self.assessment_rubric
        ):
            raise ValueError("An assessment needs a nonempty rubric.")
        if self.mode == "discuss_then_code":
            if not self.coding_requirement or not self.coding_requirement.strip():
                raise ValueError("A coding assessment needs an explicit requirement.")
        elif self.coding_requirement is not None:
            raise ValueError("Discussion-only plans cannot require coding.")
        return self


class CodingOutcome(BaseModel):
    """Evidence returned by the coding task, never a routing instruction."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: OutcomeStatus
    submission_id: str | None = None
    final_code: str | None = None
    observations: tuple[str, ...] = ()
    evidence_error: str | None = None


@dataclass
class FollowUpState:
    """Mutable per-session state; guards are set before the first await."""

    followup_id: str = field(default_factory=lambda: uuid4().hex)
    primary_submission: CodeSubmission | None = None
    primary_submission_path: str | None = None
    primary_transition_running: bool = False
    selector_started: bool = False
    selector_completed: bool = False
    selector_failure: str | None = None
    plan: FollowUpPlan | None = None
    entered: bool = False
    coding_started: bool = False
    coding_outcome: CodingOutcome | None = None
    discussion_status: OutcomeStatus | None = None
    consumed: bool = False


def log_followup(state: FollowUpState, event: str, **details: object) -> None:
    """Readable console events plus a correlated local JSONL dogfooding record."""
    primary = state.primary_submission
    record = {
        "timestamp": datetime.now(UTC).isoformat(),
        "event": event,
        "followup_id": state.followup_id,
        "job_id": primary.job_id if primary else None,
        "room_name": primary.room_name if primary else None,
        "question_slug": primary.question_slug if primary else None,
        "primary_submission_id": primary.submission_id if primary else None,
        **details,
    }
    encoded = json.dumps(record, ensure_ascii=False)
    logger.info("Follow-up %s", encoded)
    try:
        directory = Path(__file__).resolve().parents[2] / "logs"
        directory.mkdir(parents=True, exist_ok=True)
        with (directory / f"followup_{state.followup_id}.jsonl").open("a") as output:
            output.write(encoded + "\n")
    except OSError:
        logger.warning("Could not persist follow-up diagnostic event: %s", event)
