"""Stage-specific prompts for the AlgoVox interviewer."""

from agents.prompts.base import BASE_INTERVIEWER_PROMPT, build_instructions
from agents.prompts.coding import CODING_PROMPT, build_coding_prompt
from agents.prompts.discussion import DISCUSSION_PROMPT, build_discussion_prompt
from agents.prompts.intro import (
    INTRO_PROMPT,
    LEFT_PANEL_LINE,
    build_intro_opening_instructions,
)
from agents.prompts.questions import (
    MERGE_TWO_SORTED_LISTS_QUESTION,
    MERGE_TWO_SORTED_LISTS_ROW,
)

__all__ = [
    "BASE_INTERVIEWER_PROMPT",
    "CODING_PROMPT",
    "DISCUSSION_PROMPT",
    "INTRO_PROMPT",
    "LEFT_PANEL_LINE",
    "MERGE_TWO_SORTED_LISTS_QUESTION",
    "MERGE_TWO_SORTED_LISTS_ROW",
    "build_coding_prompt",
    "build_discussion_prompt",
    "build_instructions",
    "build_intro_opening_instructions",
]
