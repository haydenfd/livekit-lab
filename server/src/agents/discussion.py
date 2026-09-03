"""Discussion stage for the minimal interview flow."""

from livekit.agents import Agent, ChatContext, RunContext, function_tool

from agents.coding import CodingAgent
from agents.prompts import (
    MERGE_TWO_SORTED_LISTS_QUESTION,
    build_discussion_prompt,
    build_instructions,
)
from interview_question import InterviewQuestion


class DiscussionAgent(Agent):
    """Discuss the already-introduced question while remaining active."""

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
    async def start_coding(self, context: RunContext[None]) -> CodingAgent:
        """Start coding once the candidate has described a sound implementable approach."""
        speech = self.session.say(
            "Go ahead and start implementing your approach.",
            allow_interruptions=False,
        )
        await speech.wait_for_playout()
        return CodingAgent(
            question=self._question,
            chat_ctx=self.chat_ctx.copy(exclude_instructions=True),
        )
