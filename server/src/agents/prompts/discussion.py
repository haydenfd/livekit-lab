"""Discussion-stage prompt and setup instructions."""

DISCUSSION_PROMPT = """\
You are currently in the discussion stage.

The full interview question is:
---
{question}
---

The stage opener has already spoken a complete task summary, told the candidate
that the full question and examples are in the left panel, and explicitly
asked them to confirm the programming language from the session metadata. Do
not repeat that introduction. If the opener did not know the language, it
asked the candidate which language they will use.

After the candidate confirms or provides their language, acknowledge it briefly
and invite exactly one question about the full question. A language
confirmation or answer is not the one permitted content question.

Answer that one content question directly and briefly, then immediately invoke
`finish_discussion`. Do not invoke `finish_discussion` after only a language
confirmation or answer.

Do not recite the full problem statement aloud.
Do not volunteer an algorithm, solution, evaluation, or feedback.
Do not ask another question after the one permitted clarification.
"""

def build_discussion_prompt(question: str) -> str:
    """Add a question's full text to the discussion-stage instructions."""
    return DISCUSSION_PROMPT.format(question=question)


def build_discussion_opening(programming_language: str | None) -> str:
    """Build the deterministic, spoken introduction for the interview task."""
    language_confirmation = (
        f"You're using {programming_language}, correct?"
        if programming_language
        else "Which programming language will you use?"
    )

    return (
        "The task is to look at a binary tree from its right side and return "
        "the values of the visible nodes from top to bottom. The input can be "
        "an empty tree, with at most one hundred nodes whose values range from "
        "negative one hundred to one hundred. The full problem and all examples "
        f"are in the left panel. {language_confirmation}"
    )
