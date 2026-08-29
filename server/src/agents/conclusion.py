"""Conclusion stage for the minimal interview flow."""

from livekit.agents import Agent


class ConclusionAgent(Agent):
    """Deliver the closing line and gracefully shut down the session."""

    def __init__(self) -> None:
        super().__init__(instructions="")

    async def on_enter(self) -> None:
        await self.session.say(
            "We're done for now. Let's call it.",
            allow_interruptions=False,
        )
        self.session.shutdown()
