"""Coding stage for the minimal interview flow."""

import logging
import time
from datetime import UTC, datetime

from livekit import rtc
from livekit.agents import Agent, ChatContext, RunContext, StopResponse, function_tool

from agents.conclusion import ConclusionAgent
from agents.prompts.base import build_instructions
from agents.prompts.coding import build_coding_prompt
from agents.prompts.questions import REVERSE_LINKED_LIST_QUESTION
from code_submission import (
    CodeSubmission,
    CodeSubmissionStore,
    LocalCodeSubmissionStore,
)
from interview_context import InterviewContext
from interview_question import InterviewQuestion

logger = logging.getLogger(__name__)

ACKNOWLEDGMENT_INSTRUCTIONS = (
    "Briefly and naturally acknowledge that the implementation is accepted. "
    "Do not mention tools, storage, logs, persistence, or internal systems."
)


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


class CodingAgent(Agent):
    """Stay quiet while the candidate implements, unless they ask for help."""

    def __init__(
        self,
        *,
        question: InterviewQuestion = REVERSE_LINKED_LIST_QUESTION,
        chat_ctx: ChatContext | None = None,
        submission_store: CodeSubmissionStore | None = None,
    ) -> None:
        super().__init__(
            instructions=build_instructions(build_coding_prompt(question)),
            chat_ctx=chat_ctx,
            allow_interruptions=False,
        )
        self._question = question
        self._submission_store = submission_store or LocalCodeSubmissionStore()

    @function_tool()
    async def continue_silently(self, context: RunContext[InterviewContext]) -> None:
        """End this response silently when the candidate is continuing their implementation and does not expect interviewer participation."""
        raise StopResponse()

    @function_tool()
    async def get_current_code(self, context: RunContext[InterviewContext]) -> str:
        """Retrieve the candidate's current editor code for an implementation-specific question or direct code-inspection request."""
        return await get_current_editor_code(context)

    @function_tool()
    async def submit_code(
        self, context: RunContext[InterviewContext]
    ) -> ConclusionAgent:
        """Submit only after the implementation is acceptable and baseline time and space complexity are adequately established."""
        code = await get_current_editor_code(context)
        interview = context.userdata
        submission = CodeSubmission(
            job_id=interview.job_id,
            room_name=interview.room_name,
            question_slug=self._question.slug,
            question_title=self._question.title,
            programming_language=interview.programming_language,
            code=code,
            submitted_at=datetime.now(UTC),
        )
        try:
            await self._submission_store.save(submission)
        except Exception as error:
            logger.exception(
                "Code submission storage failed",
                extra={"question_slug": self._question.slug},
            )
            raise ValueError("Code submission could not be saved.") from error

        speech = self.session.generate_reply(
            instructions=ACKNOWLEDGMENT_INSTRUCTIONS,
            tool_choice="none",
            allow_interruptions=False,
        )
        await speech.wait_for_playout()
        return ConclusionAgent()
