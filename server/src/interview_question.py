"""Runtime interview-question model, DB-row parser, and prompt context builders."""

from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any


@dataclass(frozen=True)
class QuestionImage:
    src: str
    alt: str


@dataclass(frozen=True)
class QuestionExample:
    label: str
    input: str
    output: str
    explanation: str | None
    images: tuple[QuestionImage, ...]


@dataclass(frozen=True)
class InterviewQuestion:
    idx: int
    slug: str
    title: str
    difficulty: str
    topic_tags: tuple[str, ...]
    prompt: str
    examples: tuple[QuestionExample, ...]
    constraints: tuple[str, ...]
    hints: tuple[str, ...]
    starter_code: dict[str, Any]


def parse_json_field(value: Any) -> Any:
    """Decode a JSON-encoded column, leaving already-structured values alone."""
    if isinstance(value, str):
        return json.loads(value)
    return value


class _HTMLToTextParser(HTMLParser):
    _BLOCK_TAGS = frozenset(
        {
            "p",
            "div",
            "li",
            "ul",
            "ol",
            "br",
            "pre",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "tr",
            "blockquote",
        }
    )

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self._BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._BLOCK_TAGS and tag != "br":
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        self._chunks.append(data)


def html_to_text(value: str) -> str:
    """Convert HTML fragments into readable plain text."""
    if not value:
        return ""

    parser = _HTMLToTextParser()
    parser.feed(value)
    parser.close()

    text = "".join(parser._chunks).replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]

    collapsed: list[str] = []
    for line in lines:
        if line:
            collapsed.append(line)
        elif collapsed and collapsed[-1] != "":
            collapsed.append("")

    return "\n".join(collapsed).strip()


def parse_question_row(row: dict[str, Any]) -> InterviewQuestion:
    """Normalize a Supabase-shaped question row without mutating it."""
    examples_raw = parse_json_field(row["examples"])
    constraints_raw = parse_json_field(row["constraints"])
    hints_raw = parse_json_field(row["hints"])

    return InterviewQuestion(
        idx=row["idx"],
        slug=row["slug"],
        title=row["title"],
        difficulty=row["difficulty"],
        topic_tags=tuple(row["topic_tags"]),
        prompt=html_to_text(row["question_prompt_html"]),
        examples=tuple(_parse_example(example) for example in examples_raw),
        constraints=tuple(html_to_text(constraint) for constraint in constraints_raw),
        hints=tuple(
            html_to_text(hint) if isinstance(hint, str) else str(hint)
            for hint in hints_raw
        ),
        starter_code=copy.deepcopy(row["starter_code"]),
    )


def build_intro_question_context(question: InterviewQuestion) -> str:
    """Title and problem statement only, for the spoken intro summary."""
    return (
        "<interview_question>\n"
        f"Title: {question.title}\n"
        "\n"
        "Problem:\n"
        f"{question.prompt}\n"
        "</interview_question>"
    )


def build_discussion_question_context(question: InterviewQuestion) -> str:
    """Candidate-visible statement, examples, and constraints for discussion."""
    parts = [
        "<interview_question>",
        f"Title: {question.title}",
        "",
        "Problem:",
        question.prompt,
        "",
        "Examples:",
        "",
    ]

    for example in question.examples:
        parts.append(f"{example.label}:")
        parts.append(f"Input: {example.input}")
        parts.append(f"Output: {example.output}")
        if example.explanation:
            parts.append(f"Explanation: {example.explanation}")
        parts.append("")

    parts.append("Constraints:")
    for constraint in question.constraints:
        parts.append(f"- {constraint}")
    parts.append("</interview_question>")

    return "\n".join(parts)


def _parse_example(raw: dict[str, Any]) -> QuestionExample:
    images_raw = raw.get("images") or []
    explanation_html = raw.get("explanation_html")
    explanation = html_to_text(explanation_html) if explanation_html else None

    return QuestionExample(
        label=raw.get("label", ""),
        input=raw.get("input", ""),
        output=raw.get("output", ""),
        explanation=explanation,
        images=tuple(
            QuestionImage(src=image.get("src", ""), alt=image.get("alt", ""))
            for image in images_raw
        ),
    )
