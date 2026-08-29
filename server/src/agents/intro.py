"""Intro stage for the minimal interview flow."""

from livekit.agents import Agent, ChatContext, RunContext, function_tool

from agents.discussion import DiscussionAgent
from agents.prompts import INTRO_PROMPT, build_instructions


class IntroAgent(Agent):
    """Wait for readiness, then hand off to the discussion stage."""

    def __init__(self, *, chat_ctx: ChatContext | None = None) -> None:
        super().__init__(
            instructions=build_instructions(INTRO_PROMPT),
            chat_ctx=chat_ctx,
        )

    async def on_enter(self) -> None:
        await self.session.say("Hey, let's begin when you're ready.")

    @function_tool()
    async def move_to_discussion(self, context: RunContext[None]) -> DiscussionAgent:
        """Move to discussion after the candidate clearly indicates readiness."""
        return DiscussionAgent(
            chat_ctx=self.chat_ctx.copy(exclude_instructions=True),
        )
