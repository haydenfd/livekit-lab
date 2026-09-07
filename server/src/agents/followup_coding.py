"""Temporary coding control that returns evidence to its FollowUpAgent caller."""

import json
from datetime import UTC, datetime
from uuid import uuid4

from livekit.agents import AgentTask, ChatContext, RunContext, ToolError, function_tool

from agents.coding_tools import CodingTools
from agents.prompts.base import build_instructions
from agents.prompts.followup import FOLLOWUP_CODING_PROMPT
from code_submission import CodeSubmission, CodeSubmissionStore
from editor_code import get_current_editor_code
from followup import (
    CodingOutcome,
    FollowUpPlan,
    FollowUpState,
    OutcomeStatus,
    log_followup,
)
from interview_context import InterviewContext
from interview_question import InterviewQuestion, build_discussion_question_context


class FollowUpCodingTask(CodingTools, AgentTask[CodingOutcome]):
    """A single implementation extension, never an interview-stage router."""

    def __init__(
        self,
        *,
        question: InterviewQuestion,
        plan: FollowUpPlan,
        state: FollowUpState,
        chat_ctx: ChatContext,
        submission_store: CodeSubmissionStore,
    ) -> None:
        if (
            plan.mode != "discuss_then_code"
            or state.plan is not plan
            or not state.coding_started
            or state.consumed
            or state.coding_outcome is not None
            or state.primary_submission is None
        ):
            raise ValueError("No active follow-up coding requirement.")
        primary = state.primary_submission
        super().__init__(
            instructions=build_instructions(FOLLOWUP_CODING_PROMPT)
            + "\n\n"
            + build_discussion_question_context(question)
            + "\n\n"
            + json.dumps(
                {
                    "selected_followup": plan.model_dump(mode="json"),
                    "original_accepted_code": primary.code,
                    "programming_language": primary.programming_language,
                }
            ),
            chat_ctx=chat_ctx,
            allow_interruptions=False,
        )
        self._question = question
        self._state = state
        self._submission_store = submission_store
        self._finish_running = False

    @function_tool()
    async def finish_exercise(
        self,
        context: RunContext[InterviewContext],
        status: OutcomeStatus,
        observations: list[str],
    ) -> None:
        """Finish this exercise after reviewing acceptable code, or when the candidate explicitly stops/is unable/out of time; preserve available code and return evidence."""
        if (
            self._finish_running
            or self.done()
            or self._state.coding_outcome is not None
        ):
            log_followup(self._state, "coding_completion_repeat_blocked")
            raise ToolError("This coding exercise is already finishing or finished.")
        self._finish_running = True
        try:
            outcome = await self._capture_outcome(context, status, observations)
            self._state.coding_outcome = outcome
            log_followup(
                self._state,
                "coding_completed",
                status=outcome.status,
                submission_id=outcome.submission_id,
                observations=outcome.observations,
                evidence_error=outcome.evidence_error,
            )
            # AgentTask.complete resolves the awaiting parent; it does not hand
            # off to another Agent. https://docs.livekit.io/agents/logic/tasks/
            self.complete(outcome)
        finally:
            self._finish_running = False

    async def _capture_outcome(
        self,
        context: RunContext[InterviewContext],
        status: OutcomeStatus,
        observations: list[str],
    ) -> CodingOutcome:
        code = None
        evidence_error = None
        submission_id = None
        try:
            code = await get_current_editor_code(context)
        except Exception as error:
            evidence_error = f"editor_unavailable:{type(error).__name__}"
            if status == "demonstrated":
                status = "partial"
            log_followup(self._state, "followup_code_unavailable", error=evidence_error)
        if status == "demonstrated" and (
            code is None or not code.strip() or code != self._reviewed_code
        ):
            raise ToolError(
                "Fetch and review the current full code before marking it demonstrated. "
                "The editor must still match that reviewed snapshot."
            )
        primary = self._state.primary_submission
        assert primary is not None
        if code is not None:
            submission = CodeSubmission(
                question_slug=self._question.slug,
                question_title=self._question.title,
                programming_language=primary.programming_language,
                job_id=primary.job_id,
                room_name=primary.room_name,
                code=code,
                submitted_at=datetime.now(UTC),
                submission_id=uuid4().hex,
                version=2,
                primary_submission_id=primary.submission_id,
                followup_id=self._state.followup_id,
                outcome=status,
            )
            try:
                path = await self._submission_store.save(submission)
                submission_id = submission.submission_id
                log_followup(
                    self._state,
                    "followup_submission_saved",
                    version=2,
                    submission_id=submission_id,
                    path=str(path),
                    status=status,
                    code_bytes=len(code.encode("utf-8")),
                )
            except Exception as error:
                evidence_error = f"storage_failed:{type(error).__name__}"
                log_followup(
                    self._state, "followup_submission_failed", error=evidence_error
                )
        return CodingOutcome(
            status=status,
            submission_id=submission_id,
            final_code=code,
            observations=tuple(observations),
            evidence_error=evidence_error,
        )
