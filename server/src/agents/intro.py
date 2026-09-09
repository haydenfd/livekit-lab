"""Intro stage for the minimal interview flow."""

from livekit.agents import Agent, ChatContext, RunContext, function_tool

from agents.discussion import DiscussionAgent
from agents.prompts import (
    INTRO_PROMPT,
    MAXIMUM_DEPTH_QUESTION,
    build_instructions,
    build_intro_opening_instructions,
)
from agents.prompts.intro import LEFT_PANEL_LINE
from interview_question import InterviewQuestion


class IntroAgent(Agent):
    """Wait for readiness, introduce the problem, then hand off to discussion."""

    def __init__(
        self,
        *,
        question: InterviewQuestion = MAXIMUM_DEPTH_QUESTION,
        chat_ctx: ChatContext | None = None,
    ) -> None:
        super().__init__(
            instructions=build_instructions(INTRO_PROMPT),
            chat_ctx=chat_ctx,
        )
        self._question = question

    async def on_enter(self) -> None:
        await self.session.say("Hey, let's begin when you're ready.")

    @function_tool()
    async def move_to_discussion(self, context: RunContext[None]) -> DiscussionAgent:
        """Move to discussion after the candidate clearly indicates readiness."""
        speech = self.session.generate_reply(
            instructions=build_intro_opening_instructions(self._question),
            tool_choice="none",
            allow_interruptions=False,
        )
        await speech.wait_for_playout()

        panel = self.session.say(LEFT_PANEL_LINE, allow_interruptions=False)
        await panel.wait_for_playout()

        return DiscussionAgent(
            question=self._question,
            chat_ctx=self.chat_ctx.copy(exclude_instructions=True),
        )
