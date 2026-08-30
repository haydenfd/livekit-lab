"""Shared LiveKit AgentSession configuration."""

from livekit.agents import AgentSession

from config.agent_session_config import build_agent_session_config
from interview_context import InterviewContext


def create_agent_session(context: InterviewContext) -> AgentSession[InterviewContext]:
    """Create the lab's shared voice pipeline configuration."""
    return AgentSession(**build_agent_session_config(), userdata=context)
