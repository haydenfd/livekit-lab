"""Stage-specific prompts for the AlgoVox interviewer."""

from agents.prompts.base import BASE_INTERVIEWER_PROMPT, build_instructions
from agents.prompts.discussion import (
    DISCUSSION_PROMPT,
    DISCUSSION_SETUP_INSTRUCTIONS,
    build_discussion_prompt,
)
from agents.prompts.intro import INTRO_PROMPT
from agents.prompts.questions import FIRST_BAD_VERSION_QUESTION

__all__ = [
    "BASE_INTERVIEWER_PROMPT",
    "DISCUSSION_PROMPT",
    "DISCUSSION_SETUP_INSTRUCTIONS",
    "FIRST_BAD_VERSION_QUESTION",
    "INTRO_PROMPT",
    "build_discussion_prompt",
    "build_instructions",
]
