"""Canonical interview question definitions."""

import json
from pathlib import Path

from interview_question import parse_question_row

MAXIMUM_DEPTH_ROW = json.loads(
    Path(__file__).with_name("maximum_depth_row.json").read_text()
)
MAXIMUM_DEPTH_QUESTION = parse_question_row(MAXIMUM_DEPTH_ROW[0])
