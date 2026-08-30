"""Discussion stage for the minimal interview flow."""

from livekit.agents import Agent, ChatContext, RunContext, function_tool

from agents.conclusion import ConclusionAgent
from agents.prompts import (
    RIGHT_SIDE_VIEW_QUESTION,
    build_discussion_prompt,
    build_discussion_setup_instructions,
    build_instructions,
)


class DiscussionAgent(Agent):
    """Present one interview question, then hand off to conclusion."""

    def __init__(
        self,
        *,
        question: str = RIGHT_SIDE_VIEW_QUESTION,
        chat_ctx: ChatContext | None = None,
    ) -> None:
        super().__init__(
            instructions=build_instructions(build_discussion_prompt(question)),
            chat_ctx=chat_ctx,
        )

    async def on_enter(self) -> None:
        await self.session.generate_reply(
            instructions=build_discussion_setup_instructions(
                self.session.userdata.programming_language
            )
        )

    @function_tool()
    async def finish_discussion(self, context: RunContext[None]) -> ConclusionAgent:
        """Finish after the one permitted substantive candidate turn."""
        return ConclusionAgent()
