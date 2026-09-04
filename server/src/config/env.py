"""Environment loading for the LiveKit agent."""

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

InterviewStartStage = Literal["intro", "coding"]
INTERVIEW_START_STAGES: tuple[InterviewStartStage, ...] = ("intro", "coding")


def load_environment() -> None:
    """Load the canonical repository environment file."""
    repo_root = Path(__file__).resolve().parents[3]
    load_dotenv(repo_root / ".env")


def get_interview_start_stage(
    environment: Mapping[str, str] = os.environ,
) -> InterviewStartStage:
    """Read and validate the process-wide interview entry stage."""
    value = environment.get("INTERVIEW_START_STAGE", "intro")
    if value not in INTERVIEW_START_STAGES:
        accepted = ", ".join(INTERVIEW_START_STAGES)
        raise ValueError(
            f"Invalid INTERVIEW_START_STAGE={value!r}; accepted values are: {accepted}"
        )
    return value
