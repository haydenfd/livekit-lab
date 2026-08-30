"""Persist filtered spoken transcripts after LiveKit sessions close."""

import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_SESSION_FILE_PATTERN = re.compile(r"session_(\d+)_\d{8}\.json$")


class TranscriptionService:
    """Write one privacy-focused transcript JSON file for each finished session."""

    def __init__(self, output_dir: Path | None = None) -> None:
        self._output_dir = output_dir or Path(__file__).resolve().parents[2] / "logs"

    def register(self, job_context: Any, agent_session: Any) -> None:
        """Register a fail-open callback that runs after the session fully closes."""

        async def save_transcript() -> None:
            try:
                report = job_context.make_session_report(agent_session)
                self.persist(report, agent_session.history)
            except OSError:
                logger.exception("Failed to save transcript after session shutdown")
            except Exception:
                logger.exception("Failed to prepare transcript after session shutdown")

        job_context.add_shutdown_callback(save_transcript)

    def persist(self, report: Any, history: Any) -> Path:
        """Create the next sequential transcript file without overwriting another."""
        payload = self.build_payload(report, history)
        self._output_dir.mkdir(parents=True, exist_ok=True)

        sequence_number = self._next_sequence_number()
        report_timestamp = self._as_utc_timestamp(report.timestamp)
        date_fragment = report_timestamp.strftime("%m%d%Y")

        while True:
            output_path = self._output_dir / (
                f"session_{sequence_number}_{date_fragment}.json"
            )
            try:
                with output_path.open("x", encoding="utf-8") as output_file:
                    json.dump(payload, output_file, indent=2)
                    output_file.write("\n")
                return output_path
            except FileExistsError:
                sequence_number += 1

    def build_payload(self, report: Any, history: Any) -> dict[str, Any]:
        """Return only non-empty spoken user and assistant messages."""
        return {
            "job_id": report.job_id,
            "room_name": report.room,
            "report_timestamp": self._format_timestamp(report.timestamp),
            "transcript": [
                transcript_message
                for item in history.items
                if (transcript_message := self._transcript_message(item)) is not None
            ],
        }

    def _next_sequence_number(self) -> int:
        sequence_numbers = []
        for path in self._output_dir.glob("session_*_*.json"):
            match = _SESSION_FILE_PATTERN.fullmatch(path.name)
            if match:
                sequence_numbers.append(int(match.group(1)))
        return max(sequence_numbers, default=0) + 1

    @staticmethod
    def _transcript_message(item: Any) -> dict[str, Any] | None:
        if getattr(item, "type", None) != "message":
            return None

        role = getattr(item, "role", None)
        role = getattr(role, "value", role)
        if role not in {"user", "assistant"}:
            return None

        text = getattr(item, "text_content", None)
        if not isinstance(text, str) or not (text := text.strip()):
            return None

        message = {
            "id": item.id,
            "role": role,
            "text": text,
            "timestamp": TranscriptionService._format_timestamp(item.created_at),
            "interrupted": bool(getattr(item, "interrupted", False)),
        }
        transcript_confidence = getattr(item, "transcript_confidence", None)
        if transcript_confidence is not None:
            message["transcript_confidence"] = transcript_confidence
        return message

    @staticmethod
    def _as_utc_timestamp(timestamp: float) -> datetime:
        return datetime.fromtimestamp(timestamp, tz=UTC)

    @staticmethod
    def _format_timestamp(timestamp: float) -> str:
        return (
            TranscriptionService._as_utc_timestamp(timestamp)
            .isoformat()
            .replace("+00:00", "Z")
        )
