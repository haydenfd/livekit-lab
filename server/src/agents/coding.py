"""Primary coding, immutable submission, and the one follow-up selection boundary."""

import asyncio
import logging
from datetime import UTC, datetime
from uuid import uuid4

from livekit.agents import Agent, ChatContext, RunContext, ToolError, function_tool

from agents.coding_tools import CodingTools
from agents.conclusion import ConclusionAgent
from agents.followup import FollowUpAgent
from agents.prompts.base import build_instructions
from agents.prompts.coding import build_coding_prompt
from agents.prompts.questions import MAXIMUM_DEPTH_QUESTION
from code_submission import (
    CodeSubmission,
    CodeSubmissionStore,
    LocalCodeSubmissionStore,
)
from editor_code import get_current_editor_code
from followup import log_followup
from followup_selector import select_followup
from interview_context import InterviewContext
from interview_question import InterviewQuestion

logger = logging.getLogger(__name__)

FOLLOWUP_TRANSITION = "Okay, let's move on."


class CodingAgent(CodingTools, Agent):
    """Stay quiet while implementing; submit only after review and complexity."""

    def __init__(
        self,
        *,
        question: InterviewQuestion = MAXIMUM_DEPTH_QUESTION,
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
        self._next_agent: Agent | None = None

    @function_tool()
    async def submit_code(self, context: RunContext[InterviewContext]) -> Agent:
        """Submit only after a fresh code review with a spoken verdict and adequately established baseline time and space complexity."""
        state = context.userdata.followup
        if self._reviewed_code is None:
            log_followup(state, "primary_submission_without_review_blocked")
            raise ToolError(
                "Review the current full code and give the candidate a verdict before submitting."
            )
        if self._next_agent is not None:
            log_followup(state, "primary_transition_repeat_blocked")
            return self._next_agent
        if state.primary_transition_running or state.entered or state.consumed:
            log_followup(state, "primary_transition_blocked")
            raise ToolError(
                "Primary submission is already being processed or complete."
            )
        state.primary_transition_running = True
        try:
            return await self._save_and_route(context)
        finally:
            state.primary_transition_running = False

    async def _save_and_route(self, context: RunContext[InterviewContext]) -> Agent:
        interview = context.userdata
        state = interview.followup
        # A retry after a later operation fails reuses V1, never re-reads or
        # overwrites the accepted original solution.
        if state.primary_submission is None:
            code = await get_current_editor_code(context)
            submission = CodeSubmission(
                job_id=interview.job_id,
                room_name=interview.room_name,
                question_slug=self._question.slug,
                question_title=self._question.title,
                programming_language=interview.programming_language,
                code=code,
                submitted_at=datetime.now(UTC),
                submission_id=uuid4().hex,
                version=1,
            )
            try:
                path = await self._submission_store.save(submission)
            except Exception as error:
                logger.exception(
                    "Code submission storage failed",
                    extra={"question_slug": self._question.slug},
                )
                raise ValueError("Code submission could not be saved.") from error
            state.primary_submission = submission
            state.primary_submission_path = str(path)
            log_followup(
                state,
                "primary_submission_saved",
                version=1,
                path=str(path),
                code_bytes=len(code.encode("utf-8")),
            )

        if state.selector_started:
            plan = await select_followup(self._question, state, self.chat_ctx)
        else:
            # Selection runs while TTS speaks the transition. A fixed line needs
            # no extra LLM turn; handoff waits for BOTH selection and playout.
            selection = asyncio.create_task(
                select_followup(self._question, state, self.chat_ctx.copy()),
                name="select_followup",
            )
            try:
                log_followup(state, "transition_speech_started")
                await self.session.say(
                    FOLLOWUP_TRANSITION, allow_interruptions=False
                ).wait_for_playout()
                log_followup(state, "transition_speech_completed")
                plan = await selection
            finally:
                # Do not leave a model request running after a speech failure
                # or session cancellation. Completed selection stays cached.
                if not selection.done():
                    selection.cancel()
                await asyncio.gather(selection, return_exceptions=True)
        if plan is None or plan.mode == "none":
            state.consumed = True
            log_followup(
                state,
                "followup_skipped",
                reason="selector_failure" if plan is None else "none",
            )
            self._next_agent = ConclusionAgent()
        else:
            self._next_agent = FollowUpAgent(
                question=self._question,
                plan=plan,
                state=state,
                submission_store=self._submission_store,
            )
        return self._next_agent
