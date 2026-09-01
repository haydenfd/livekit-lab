"""Stage-specific prompts for the AlgoVox interviewer."""

from agents.prompts.base import BASE_INTERVIEWER_PROMPT, build_instructions
from agents.prompts.discussion import DISCUSSION_PROMPT, build_discussion_prompt
from agents.prompts.intro import (
    INTRO_PROMPT,
    LEFT_PANEL_LINE,
    build_intro_opening_instructions,
)
from agents.prompts.questions import RIGHT_SIDE_VIEW_QUESTION

__all__ = [
    "BASE_INTERVIEWER_PROMPT",
    "DISCUSSION_PROMPT",
    "INTRO_PROMPT",
    "LEFT_PANEL_LINE",
    "RIGHT_SIDE_VIEW_QUESTION",
    "build_discussion_prompt",
    "build_instructions",
    "build_intro_opening_instructions",
]
