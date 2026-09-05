"""LiveKit agent server entrypoint."""

import logging
from typing import Any

from livekit.agents import AgentServer, ChatContext, JobContext, cli

from agent_session import create_agent_session
from agents.coding import CodingAgent
from agents.intro import IntroAgent
from agents.prompts import REVERSE_LINKED_LIST_QUESTION
from audio import create_room_options
from config.env import InterviewStartStage, get_interview_start_stage, load_environment
from interview_context import InterviewContext
from interview_question import (
    build_discussion_question_context,
    build_intro_question_context,
)
from services.transcription_service import TranscriptionService

logger = logging.getLogger("agent")

CODING_APPROACH = (
    "Use a dummy head and a tail pointer. Compare the current nodes from both "
    "sorted lists, link the smaller node to the tail, and advance that list. "
    "When one list is exhausted, attach the other list and return dummy.next."
)
CODING_APPROVAL = "That approach works. Go ahead and start implementing it."

load_environment()
INTERVIEW_START_STAGE = get_interview_start_stage()
server = AgentServer()


async def start_interview(
    *,
    agent_session: Any,
    room: Any,
    room_options: Any,
    start_stage: InterviewStartStage,
) -> None:
    """Start the configured interview stage without changing stage prompts."""
    question = REVERSE_LINKED_LIST_QUESTION
    if start_stage == "intro":
        await agent_session.start(
            agent=IntroAgent(question=question),
            room=room,
            room_options=room_options,
        )
        return

    chat_ctx = ChatContext()
    chat_ctx.add_message(role="user", content=CODING_APPROACH)
    await agent_session.start(
        agent=CodingAgent(question=question, chat_ctx=chat_ctx),
        room=room,
        room_options=room_options,
    )
    approval = agent_session.say(CODING_APPROVAL, allow_interruptions=False)
    await approval.wait_for_playout()


@server.rtc_session(agent_name="my-agent")
async def my_agent(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    interview_context = InterviewContext.from_dispatch_metadata(
        ctx.job.metadata,
        job_id=ctx.job.id,
        room_name=ctx.room.name,
    )
    agent_session = create_agent_session(interview_context)
    TranscriptionService().register(ctx, agent_session)

    question = REVERSE_LINKED_LIST_QUESTION
    logger.debug(
        "Intro question context:\n%s",
        build_intro_question_context(question),
    )
    logger.debug(
        "Discussion question context:\n%s",
        build_discussion_question_context(question),
    )

    await start_interview(
        agent_session=agent_session,
        room=ctx.room,
        room_options=create_room_options(),
        start_stage=INTERVIEW_START_STAGE,
    )

    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(server)
