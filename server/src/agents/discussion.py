"""Discussion stage for the minimal interview flow."""

from livekit.agents import Agent, ChatContext, RunContext, function_tool

from agents.conclusion import ConclusionAgent
from agents.prompts import DISCUSSION_PROMPT, build_instructions


class DiscussionAgent(Agent):
    """Ask one conversational question, then hand off to conclusion."""

    def __init__(self, *, chat_ctx: ChatContext | None = None) -> None:
        super().__init__(
            instructions=build_instructions(DISCUSSION_PROMPT),
            chat_ctx=chat_ctx,
        )

    async def on_enter(self) -> None:
        await self.session.say("How are you doing today?")

    @function_tool()
    async def finish_discussion(self, context: RunContext) -> ConclusionAgent:
        """Finish after the candidate gives their first substantive response."""
        return ConclusionAgent(
            chat_ctx=self.chat_ctx.copy(exclude_instructions=True),
        )
