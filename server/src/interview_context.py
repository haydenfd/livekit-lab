"""Session-scoped interview metadata shared by every agent stage."""

import json
from dataclasses import dataclass


@dataclass(frozen=True)
class InterviewContext:
    """Configuration supplied when LiveKit dispatches an interview job."""

    programming_language: str | None = None

    @classmethod
    def from_dispatch_metadata(cls, metadata: str | None) -> "InterviewContext":
        """Parse optional JSON dispatch metadata without restricting languages."""
        if not metadata:
            return cls()

        try:
            parsed = json.loads(metadata)
        except (TypeError, json.JSONDecodeError):
            return cls()

        if not isinstance(parsed, dict):
            return cls()

        programming_language = parsed.get("programmingLanguage")
        if not isinstance(programming_language, str):
            return cls()

        return cls(programming_language=programming_language)
