"""Coding stage for the minimal interview flow."""

import logging
import time

from livekit import rtc
from livekit.agents import Agent, ChatContext, RunContext, StopResponse, function_tool

from agents.prompts.base import build_instructions
from agents.prompts.coding import build_coding_prompt
from agents.prompts.questions import MERGE_TWO_SORTED_LISTS_QUESTION
from interview_question import InterviewQuestion

logger = logging.getLogger(__name__)


class CodingAgent(Agent):
    """Stay quiet while the candidate implements, unless they ask for help."""

    def __init__(
        self,
        *,
        question: InterviewQuestion = MERGE_TWO_SORTED_LISTS_QUESTION,
        chat_ctx: ChatContext | None = None,
    ) -> None:
        super().__init__(
            instructions=build_instructions(build_coding_prompt(question)),
            chat_ctx=chat_ctx,
            allow_interruptions=False,
        )
        self._question = question

    @function_tool()
    async def continue_silently(self, context: RunContext[None]) -> None:
        """End this response silently when the candidate is continuing their implementation and does not expect interviewer participation."""
        raise StopResponse()

    @function_tool()
    async def get_current_code(self, context: RunContext[None]) -> str:
        """Retrieve the candidate's current editor code for an implementation-specific question or direct code-inspection request."""
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
        logger.debug(
            "Requesting current editor code", extra={"identity": candidate.identity}
        )
        try:
            try:
                code = await room.local_participant.perform_rpc(
                    destination_identity=candidate.identity,
                    method="editor.get_current_code",
                    payload="",
                    response_timeout=3.0,
                )
            except rtc.RpcError:
                duration_ms = (time.perf_counter() - started_at) * 1000
                logger.warning(
                    "Current editor code RPC failed",
                    extra={"duration_ms": duration_ms},
                )
                raise
        except rtc.RpcError as error:
            raise ValueError("Candidate code is unavailable.") from error

        duration_ms = (time.perf_counter() - started_at) * 1000
        logger.info(
            "Current editor code RPC succeeded",
            extra={
                "duration_ms": duration_ms,
                "code_bytes": len(code.encode("utf-8")),
            },
        )
        return code
