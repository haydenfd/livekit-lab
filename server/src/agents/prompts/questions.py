"""Canonical interview question definitions."""

import json
from pathlib import Path

from interview_question import parse_question_row

REVERSE_LINKED_LIST_ROW = json.loads(
    Path(__file__).with_name("reverse_linked_list_row.json").read_text()
)
REVERSE_LINKED_LIST_QUESTION = parse_question_row(REVERSE_LINKED_LIST_ROW[0])
