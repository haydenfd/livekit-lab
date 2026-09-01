"""LiveKit agent server entrypoint."""

import logging

from livekit.agents import AgentServer, JobContext, cli

from agent_session import create_agent_session
from agents.intro import IntroAgent
from agents.prompts import MERGE_TWO_SORTED_LISTS_QUESTION
from audio import create_room_options
from config.env import load_environment
from interview_context import InterviewContext
from interview_question import (
    build_discussion_question_context,
    build_intro_question_context,
)
from services.transcription_service import TranscriptionService

logger = logging.getLogger("agent")

load_environment()
server = AgentServer()


@server.rtc_session(agent_name="my-agent")
async def my_agent(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    interview_context = InterviewContext.from_dispatch_metadata(ctx.job.metadata)
    agent_session = create_agent_session(interview_context)
    TranscriptionService().register(ctx, agent_session)

    question = MERGE_TWO_SORTED_LISTS_QUESTION
    logger.debug(
        "Intro question context:\n%s",
        build_intro_question_context(question),
    )
    logger.debug(
        "Discussion question context:\n%s",
        build_discussion_question_context(question),
    )

    await agent_session.start(
        agent=IntroAgent(question=question),
        room=ctx.room,
        room_options=create_room_options(),
    )

    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(server)
