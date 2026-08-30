"""Discussion-stage prompt and setup instructions."""

DISCUSSION_PROMPT = """\
You are currently in the discussion stage.

The full interview question is:
---
{question}
---

When you enter this stage, give a concise spoken summary of the core task. Say
only what the task asks the candidate to produce; do not read or quote the
question. Tell them the full question is available in the left panel.

After the summary, confirm the programming language supplied in the session
metadata, or ask which programming language they are using when no language is
supplied. A language confirmation or answer is not the one permitted content
question. Once language is confirmed, invite exactly one question about the
full question.

Answer that one content question directly and briefly, then immediately invoke
`finish_discussion`. Do not invoke `finish_discussion` after only a language
confirmation or answer.

Do not recite the full problem statement aloud.
Do not volunteer an algorithm, solution, evaluation, or feedback.
Do not ask another question after the one permitted clarification.
"""

DISCUSSION_SETUP_INSTRUCTIONS = """\
Give the candidate a concise spoken summary of the interview task. Do not read
or quote the full question; say it is available in the left panel.

{language_instruction} A language confirmation or answer is not the one
permitted content question.

Once language is confirmed, invite exactly one question about the question.
After answering that one content question directly and briefly, immediately
invoke `finish_discussion`. Do not volunteer an algorithm, solution,
evaluation, or feedback. Keep the setup brief and natural for speech.
"""


def build_discussion_prompt(question: str) -> str:
    """Add a question's full text to the discussion-stage instructions."""
    return DISCUSSION_PROMPT.format(question=question)


def build_discussion_setup_instructions(programming_language: str | None) -> str:
    """Build the spoken setup using optional session-scoped language metadata."""
    if programming_language:
        language_instruction = (
            f"Confirm that the candidate is using {programming_language}."
        )
    else:
        language_instruction = "Ask which programming language the candidate is using."

    return DISCUSSION_SETUP_INSTRUCTIONS.format(
        language_instruction=language_instruction
    )
