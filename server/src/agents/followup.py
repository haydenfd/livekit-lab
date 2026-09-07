"""Conduct one fixed follow-up and optionally await one coding excursion."""

import json
import time

from livekit.agents import Agent, ChatContext, RunContext, ToolError, function_tool

from agents.conclusion import ConclusionAgent
from agents.followup_coding import FollowUpCodingTask
from agents.prompts.base import build_instructions
from agents.prompts.followup import FOLLOWUP_PROMPT
from code_submission import CodeSubmissionStore
from followup import (
    CodingOutcome,
    FollowUpPlan,
    FollowUpState,
    OutcomeStatus,
    log_followup,
)
from interview_context import InterviewContext
from interview_question import InterviewQuestion, build_discussion_question_context


class FollowUpAgent(Agent):
    """Interviewer for a selected assessment; has no selector capability."""

    def __init__(
        self,
        *,
        question: InterviewQuestion,
        plan: FollowUpPlan,
        state: FollowUpState,
        submission_store: CodeSubmissionStore,
    ) -> None:
        if (
            plan.mode == "none"
            or state.plan is not plan
            or state.primary_submission is None
        ):
            raise ValueError(
                "FollowUpAgent requires the selected assessment and primary code."
            )
        self._question = question
        self._plan = plan
        self._state = state
        self._submission_store = submission_store
        self._conclusion: ConclusionAgent | None = None
        primary = state.primary_submission
        tools = [function_tool(self.finish_followup)]
        if plan.mode == "discuss_then_code":
            tools.append(function_tool(self.start_coding))
        # A fresh history contains only this follow-up's conversation. The
        # baseline and fixed assessment are explicit, rather than inherited.
        super().__init__(
            instructions=build_instructions(FOLLOWUP_PROMPT)
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
            chat_ctx=ChatContext(),
            tools=tools,
            allow_interruptions=False,
        )

    async def on_enter(self) -> None:
        if self._state.entered or self._state.consumed:
            return
        self._state.entered = True
        log_followup(
            self._state, "followup_entered", mode=self._plan.mode, kind=self._plan.kind
        )
        assert self._plan.opening_question is not None
        await self.session.say(
            self._plan.opening_question, allow_interruptions=False
        ).wait_for_playout()

    async def finish_followup(
        self,
        context: RunContext[InterviewContext],
        status: OutcomeStatus,
        observations: list[str],
    ) -> ConclusionAgent:
        """Finish the discussion assessment; for code-required plans only use this before coding if the candidate explicitly declines, cannot proceed, or is out of time."""
        if self._state.coding_started and self._state.coding_outcome is None:
            raise ToolError("The coding exercise is still active.")
        if self._plan.mode == "discuss_then_code" and status == "demonstrated":
            raise ToolError(
                "This assessment requires implementation. Start its coding exercise."
            )
        if not self._state.consumed:
            self._state.discussion_status = status
            log_followup(
                self._state,
                "discussion_completed",
                status=status,
                observations=observations,
            )
        return self._conclude()

    async def start_coding(
        self, context: RunContext[InterviewContext]
    ) -> ConclusionAgent:
        """Begin the selected coding requirement once the candidate is ready to implement; a verbal explanation alone does not satisfy this assessment."""
        state = self._state
        if (
            self._plan.mode != "discuss_then_code"
            or state.coding_started
            or state.consumed
        ):
            log_followup(state, "coding_start_blocked", mode=self._plan.mode)
            raise ToolError("Another coding exercise is not available.")
        # Set before speech or construction: parallel/repeated calls cannot
        # create two AgentTasks. Task construction must happen in this tool.
        state.coding_started = True
        started = time.perf_counter()
        log_followup(state, "coding_started", requirement=self._plan.coding_requirement)
        assert self._plan.coding_requirement is not None
        try:
            await self.session.say(
                self._plan.coding_requirement + " Go ahead and implement that change.",
                allow_interruptions=False,
            ).wait_for_playout()
            # SDK 1.6.10 pauses this instance, runs the task, and resumes this
            # same instance before the await returns, including on task errors.
            outcome = await FollowUpCodingTask(
                question=self._question,
                plan=self._plan,
                state=state,
                chat_ctx=self.chat_ctx.copy(exclude_instructions=True),
                submission_store=self._submission_store,
            )
        except Exception as error:
            outcome = state.coding_outcome or CodingOutcome(
                status="partial",
                evidence_error=f"task_failed:{type(error).__name__}",
                observations=("The coding interaction could not be completed.",),
            )
            log_followup(state, "coding_task_failed", error=type(error).__name__)
        state.coding_outcome = outcome
        log_followup(
            state,
            "coding_returned_to_followup",
            status=outcome.status,
            parent_resumed=self.session.current_agent is self,
            duration_ms=round((time.perf_counter() - started) * 1000),
        )
        # No further model turn is needed to decide routing. The restored parent
        # resolves the exercise and returns Conclusion through its original tool.
        return self._conclude()

    def _conclude(self) -> ConclusionAgent:
        if self._conclusion is None:
            self._state.consumed = True
            log_followup(self._state, "followup_resolved")
            self._conclusion = ConclusionAgent()
        return self._conclusion
