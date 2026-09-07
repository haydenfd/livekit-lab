"""Session-scoped interview metadata shared by every agent stage."""

import json
from dataclasses import dataclass, field

from followup import FollowUpState


@dataclass(frozen=True)
class InterviewContext:
    """Configuration supplied when LiveKit dispatches an interview job."""

    programming_language: str | None = None
    job_id: str | None = None
    room_name: str | None = None
    followup: FollowUpState = field(default_factory=FollowUpState, compare=False)

    @classmethod
    def from_dispatch_metadata(
        cls,
        metadata: str | None,
        *,
        job_id: str | None = None,
        room_name: str | None = None,
    ) -> "InterviewContext":
        """Parse optional JSON dispatch metadata without restricting languages."""
        if not metadata:
            return cls(job_id=job_id, room_name=room_name)

        try:
            parsed = json.loads(metadata)
        except (TypeError, json.JSONDecodeError):
            return cls(job_id=job_id, room_name=room_name)

        if not isinstance(parsed, dict):
            return cls(job_id=job_id, room_name=room_name)

        programming_language = parsed.get("programmingLanguage")
        if not isinstance(programming_language, str):
            return cls(job_id=job_id, room_name=room_name)

        return cls(
            programming_language=programming_language,
            job_id=job_id,
            room_name=room_name,
        )
