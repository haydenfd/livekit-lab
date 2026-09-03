"""Coding stage for the minimal interview flow."""

from livekit.agents import Agent, ChatContext, RunContext, StopResponse, function_tool

from agents.prompts.base import build_instructions
from agents.prompts.coding import build_coding_prompt
from agents.prompts.questions import MERGE_TWO_SORTED_LISTS_QUESTION
from interview_question import InterviewQuestion


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
