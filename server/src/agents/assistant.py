"""The current single-agent AlgoVox interviewer."""

from livekit.agents import Agent

from agents.prompts import ASSISTANT_PROMPT


class Assistant(Agent):
    """Current conversational agent used by the lab."""

    def __init__(self) -> None:
        super().__init__(
            instructions=ASSISTANT_PROMPT,
        )
