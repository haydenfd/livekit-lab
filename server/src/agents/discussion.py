"""Discussion stage for the minimal interview flow."""

from livekit.agents import Agent, ChatContext, RunContext, function_tool

from agents.conclusion import ConclusionAgent
from agents.prompts import (
    MERGE_TWO_SORTED_LISTS_QUESTION,
    build_discussion_prompt,
    build_instructions,
)
from interview_question import InterviewQuestion


class DiscussionAgent(Agent):
    """Discuss the already-introduced question, then hand off to conclusion."""

    def __init__(
        self,
        *,
        question: InterviewQuestion = MERGE_TWO_SORTED_LISTS_QUESTION,
        chat_ctx: ChatContext | None = None,
    ) -> None:
        super().__init__(
            instructions=build_instructions(build_discussion_prompt(question)),
            chat_ctx=chat_ctx,
        )
        self._question = question

    @function_tool()
    async def finish_discussion(self, context: RunContext[None]) -> ConclusionAgent:
        """Finish after the one permitted substantive candidate turn."""
        return ConclusionAgent()
