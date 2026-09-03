from interview_question import (
    InterviewQuestion,
    QuestionExample,
    build_discussion_question_context,
    html_to_text,
    parse_json_field,
)


def test_parse_json_field_decodes_strings_and_passes_through_structured_values() -> (
    None
):
    assert parse_json_field('["a", "b"]') == ["a", "b"]
    assert parse_json_field(["a", "b"]) == ["a", "b"]
    assert parse_json_field({"a": 1}) == {"a": 1}


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
