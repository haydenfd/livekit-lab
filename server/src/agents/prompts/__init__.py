"""Stage-specific prompts for the AlgoVox interviewer."""

from agents.prompts.base import BASE_INTERVIEWER_PROMPT, build_instructions
from agents.prompts.conclusion import CONCLUSION_PROMPT
from agents.prompts.discussion import DISCUSSION_PROMPT
from agents.prompts.intro import INTRO_PROMPT

__all__ = [
    "BASE_INTERVIEWER_PROMPT",
    "CONCLUSION_PROMPT",
    "DISCUSSION_PROMPT",
    "INTRO_PROMPT",
    "build_instructions",
]
