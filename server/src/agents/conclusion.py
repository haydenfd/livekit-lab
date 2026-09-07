"""Conclusion stage for the minimal interview flow."""

from livekit.agents import Agent

from followup import log_followup


class ConclusionAgent(Agent):
    """Deliver the closing line and stop the interviewer without deleting the room."""

    def __init__(self) -> None:
        super().__init__(instructions="")

    async def on_enter(self) -> None:
        state = getattr(getattr(self.session, "userdata", None), "followup", None)
        if state is not None:
            log_followup(state, "conclusion_entered")
        speech = self.session.say(
            "We're done for now",
            allow_interruptions=False,
        )
        await speech.wait_for_playout()
        self.session.shutdown()
