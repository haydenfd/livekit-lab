"""Conclusion stage for the minimal interview flow."""

from livekit.agents import Agent


class ConclusionAgent(Agent):
    """Deliver the closing line and stop the interviewer without deleting the room."""

    def __init__(self) -> None:
        super().__init__(instructions="")

    async def on_enter(self) -> None:
        speech = self.session.say(
            "We're done for now",
            allow_interruptions=False,
        )
        await speech.wait_for_playout()
        self.session.shutdown()
