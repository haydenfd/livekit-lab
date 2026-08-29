"""Discussion-stage prompt and setup instructions."""

DISCUSSION_PROMPT = """\
You are currently in the discussion stage.

The full interview question is:
---
{question}
---

When you enter this stage, give a concise spoken summary of the core task. Say
that the candidate needs to find the earliest bad version when every later
version is also bad. Tell them the full question is available in the left
panel, then invite exactly one clarifying question.

Permit exactly one substantive candidate turn. If the candidate asks a
question about the problem, answer it directly and briefly, then immediately
invoke `finish_discussion`. If they give any other substantive response,
immediately invoke `finish_discussion`.

Do not recite the full problem statement aloud.
Do not discuss the solution approach, problem category, or constraints.
Do not volunteer an algorithm, solution, evaluation, or feedback.
Do not ask another question after the one permitted clarification.
"""

DISCUSSION_SETUP_INSTRUCTIONS = """\
Give the candidate a concise spoken setup for the interview question in your
instructions. Mention only that they need to find the earliest bad version
when every later version is also bad. Say that the full question is available
in the left panel, and invite exactly one clarifying question.

Do not recite the full problem statement. Do not mention a solution approach,
problem category, or constraints. Keep this setup brief and natural for speech.
"""


def build_discussion_prompt(question: str) -> str:
    """Add a question's full text to the discussion-stage instructions."""
    return DISCUSSION_PROMPT.format(question=question)
