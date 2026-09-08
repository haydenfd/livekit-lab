"""Canonical on-demand editor RPC shared by coding interactions."""

import logging
import time

from livekit import rtc
from livekit.agents import RunContext

from interview_context import InterviewContext

logger = logging.getLogger("agents.coding")


async def get_current_editor_code(context: RunContext[InterviewContext]) -> str:
    """Return the only candidate's current editor contents via the canonical RPC."""
    room = context.session.room_io.room
    candidates = [
        participant
        for participant in room.remote_participants.values()
        if participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_STANDARD
    ]
    if not candidates:
        raise ValueError("Candidate code is unavailable: no candidate participant.")
    if len(candidates) > 1:
        raise ValueError(
            "Candidate code is unavailable: multiple candidate participants."
        )

    candidate = candidates[0]
    started_at = time.perf_counter()
    logger.info(
        "Current editor code RPC started",
        extra={"identity": candidate.identity},
    )
    try:
        try:
            code = await room.local_participant.perform_rpc(
                destination_identity=candidate.identity,
                method="editor.get_current_code",
                payload="",
                response_timeout=3.0,
            )
        except rtc.RpcError as error:
            duration_ms = (time.perf_counter() - started_at) * 1000
            logger.warning(
                "Current editor code RPC failed",
                extra={
                    "identity": candidate.identity,
                    "duration_ms": duration_ms,
                    "error_type": type(error).__name__,
                },
            )
            raise
    except rtc.RpcError as error:
        raise ValueError("Candidate code is unavailable.") from error

    duration_ms = (time.perf_counter() - started_at) * 1000
    logger.info(
        "Current editor code RPC succeeded",
        extra={
            "identity": candidate.identity,
            "duration_ms": duration_ms,
            "code_bytes": len(code.encode("utf-8")),
        },
    )
    return code
