import copy
import json
import re

from agents.prompts import MERGE_TWO_SORTED_LISTS_QUESTION, MERGE_TWO_SORTED_LISTS_ROW
from interview_question import (
    InterviewQuestion,
    QuestionExample,
    QuestionImage,
    build_discussion_question_context,
    build_intro_question_context,
    html_to_text,
    parse_json_field,
    parse_question_row,
)

IMAGE_URL = "https://assets.leetcode.com/uploads/2020/10/03/merge_ex1.jpg"
HTML_TAG = re.compile(r"<[^>]+>")


def test_parse_json_field_decodes_strings_and_passes_through_structured_values() -> (
    None
):
    assert parse_json_field('["a", "b"]') == ["a", "b"]
    assert parse_json_field(["a", "b"]) == ["a", "b"]
    assert parse_json_field({"a": 1}) == {"a": 1}


def test_parse_question_row_parses_the_supplied_one_row_array() -> None:
    assert len(MERGE_TWO_SORTED_LISTS_ROW) == 1

    question = parse_question_row(MERGE_TWO_SORTED_LISTS_ROW[0])

    assert question == MERGE_TWO_SORTED_LISTS_QUESTION
    assert question.idx == 11
    assert question.slug == "merge-two-sorted-lists"
    assert question.title == "Merge Two Sorted Lists"
    assert question.difficulty == "easy"
    assert question.topic_tags == ("Linked List", "Recursion")


def test_parse_question_row_does_not_mutate_the_raw_fixture() -> None:
    original = copy.deepcopy(MERGE_TWO_SORTED_LISTS_ROW)

    question = parse_question_row(MERGE_TWO_SORTED_LISTS_ROW[0])
    question.starter_code["python"]["raw_code"] = "mutated"

    assert original == MERGE_TWO_SORTED_LISTS_ROW


def test_parse_question_row_structures_json_string_columns() -> None:
    raw = MERGE_TWO_SORTED_LISTS_ROW[0]
    assert isinstance(raw["examples"], str)
    assert isinstance(raw["constraints"], str)
    assert isinstance(raw["hints"], str)

    question = parse_question_row(raw)

    assert len(question.examples) == 3
    assert question.examples[0].label == "Example 1"
    assert question.examples[0].input == "list1 = [1,2,4], list2 = [1,3,4]"
    assert question.examples[0].output == "[1,1,2,3,4,4]"
    assert question.constraints == (
        "The number of nodes in both lists is in the range [0, 50].",
        "-100 <= Node.val <= 100",
        "Both list1 and list2 are sorted in non-decreasing order.",
    )
    assert question.hints == ()


def test_parse_question_row_accepts_already_decoded_json_columns() -> None:
    row = copy.deepcopy(MERGE_TWO_SORTED_LISTS_ROW[0])
    row["examples"] = json.loads(row["examples"])
    row["constraints"] = json.loads(row["constraints"])
    row["hints"] = json.loads(row["hints"])

    question = parse_question_row(row)

    assert len(question.examples) == 3
    assert len(question.constraints) == 3
    assert question.hints == ()


def test_parse_question_row_preserves_starter_code_and_image_metadata() -> None:
    question = parse_question_row(MERGE_TWO_SORTED_LISTS_ROW[0])

    assert "python" in question.starter_code
    assert "javascript" in question.starter_code
    assert question.starter_code["python"]["leetcode_lang_slug"] == "python3"
    assert "mergeTwoLists" in question.starter_code["python"]["solution_scaffold"]
    assert question.examples[0].images == (QuestionImage(src=IMAGE_URL, alt=""),)
    assert question.examples[1].images == ()
    assert question.examples[2].images == ()


def test_html_normalization_strips_tags_and_decodes_entities() -> None:
    question = parse_question_row(MERGE_TWO_SORTED_LISTS_ROW[0])

    assert "list1" in question.prompt
    assert "list2" in question.prompt
    assert HTML_TAG.search(question.prompt) is None
    assert "<p>" not in question.prompt
    assert "<code>" not in question.prompt
    assert "<strong>" not in question.prompt
    assert "<= " in question.constraints[1] or "<=" in question.constraints[1]
    assert "&lt;" not in question.constraints[1]
    assert "&nbsp;" not in question.prompt
    assert "\n\n" in question.prompt


def test_html_to_text_preserves_readable_paragraphs() -> None:
    text = html_to_text(
        "<p>You are given the heads of two sorted linked lists "
        "<code>list1</code> and <code>list2</code>.</p>\n\n"
        "<p>Merge the two lists into one <strong>sorted</strong> list.</p>"
    )

    assert text == (
        "You are given the heads of two sorted linked lists list1 and list2.\n"
        "\n"
        "Merge the two lists into one sorted list."
    )


def test_intro_context_contains_only_title_and_problem() -> None:
    context = build_intro_question_context(MERGE_TWO_SORTED_LISTS_QUESTION)

    assert "Title: Merge Two Sorted Lists" in context
    assert (
        "You are given the heads of two sorted linked lists list1 and list2." in context
    )
    assert "Example 1" not in context
    assert "Constraints" not in context
    assert "non-decreasing" not in context
    assert "Linked List" not in context
    assert "Recursion" not in context
    assert "hint" not in context.lower()
    assert "mergeTwoLists" not in context
    assert IMAGE_URL not in context
    assert "<p>" not in context
    assert "<code>" not in context
    assert "<strong>" not in context
    assert "raw_content_html" not in context
    assert context.startswith("<interview_question>")
    assert context.endswith("</interview_question>")


def test_discussion_context_contains_statement_examples_and_constraints() -> None:
    context = build_discussion_question_context(MERGE_TWO_SORTED_LISTS_QUESTION)

    assert "Title: Merge Two Sorted Lists" in context
    assert (
        "You are given the heads of two sorted linked lists list1 and list2." in context
    )
    assert "Example 1:" in context
    assert "Input: list1 = [1,2,4], list2 = [1,3,4]" in context
    assert "Output: [1,1,2,3,4,4]" in context
    assert "Example 2:" in context
    assert "Input: list1 = [], list2 = []" in context
    assert "Output: []" in context
    assert "Example 3:" in context
    assert "Input: list1 = [], list2 = [0]" in context
    assert "Output: [0]" in context
    assert "The number of nodes in both lists is in the range [0, 50]." in context
    assert "-100 <= Node.val <= 100" in context
    assert "Both list1 and list2 are sorted in non-decreasing order." in context
    assert "Linked List" not in context
    assert "Recursion" not in context
    assert "hint" not in context.lower()
    assert "mergeTwoLists" not in context
    assert "raw_html" not in context
    assert "raw_content_html" not in context
    assert IMAGE_URL not in context
    assert "<p>" not in context
    assert "<code>" not in context
    assert "<strong>" not in context


def test_discussion_context_excludes_hints_tags_and_starter_code_when_present() -> None:
    question = make_question()
    context = build_discussion_question_context(question)

    assert "try recursion" not in context
    assert "Arrays" not in context
    assert "def foo(): pass" not in context


def make_question(**overrides: object) -> InterviewQuestion:
    values: dict[str, object] = {
        "idx": 1,
        "slug": "test-question",
        "title": "Test Question",
        "difficulty": "easy",
        "topic_tags": ("Arrays",),
        "prompt": "Do something interesting.",
        "examples": (
            QuestionExample(
                label="Example 1",
                input="x = 1",
                output="2",
                explanation=None,
                images=(),
            ),
        ),
        "constraints": ("x > 0",),
        "hints": ("try recursion",),
        "starter_code": {"python": {"raw_code": "def foo(): pass"}},
    }
    values.update(overrides)
    return InterviewQuestion(**values)  # type: ignore[arg-type]
