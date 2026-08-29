"""LiveKit agent server entrypoint."""

import logging

from livekit.agents import AgentServer, JobContext, cli

from agent_session import create_agent_session
from agents.assistant import Assistant
from audio import create_room_options
from config.env import load_environment

logger = logging.getLogger("agent")

load_environment()
server = AgentServer()


@server.rtc_session(agent_name="my-agent")
async def my_agent(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    agent_session = create_agent_session()

    await agent_session.start(
        agent=Assistant(),
        room=ctx.room,
        room_options=create_room_options(),
    )

    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(server)
