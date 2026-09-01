"""Canonical interview question definitions."""

import json
from pathlib import Path

from interview_question import parse_question_row

MERGE_TWO_SORTED_LISTS_ROW = json.loads(
    Path(__file__).with_name("merge_two_sorted_lists_row.json").read_text()
)
MERGE_TWO_SORTED_LISTS_QUESTION = parse_question_row(MERGE_TWO_SORTED_LISTS_ROW[0])
