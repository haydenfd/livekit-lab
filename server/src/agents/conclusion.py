"""Conclusion stage for the minimal interview flow."""

from livekit.agents import Agent, ChatContext

from agents.prompts import CONCLUSION_PROMPT, build_instructions


class ConclusionAgent(Agent):
    """Deliver the closing line and gracefully shut down the session."""

    def __init__(self, *, chat_ctx: ChatContext | None = None) -> None:
        super().__init__(
            instructions=build_instructions(CONCLUSION_PROMPT),
            chat_ctx=chat_ctx,
        )

    async def on_enter(self) -> None:
        await self.session.say(
            "We're done for now. Let's call it.",
            allow_interruptions=False,
        )
        self.session.shutdown()
