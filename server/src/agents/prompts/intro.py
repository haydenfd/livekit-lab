"""Intro-stage prompt."""

INTRO_PROMPT = """\
You are currently in the intro stage.

Wait for the candidate to indicate that they are ready to begin.

Once they clearly indicate readiness, transition to the discussion stage.

Do not begin the interview discussion yourself.
Do not ask additional questions during this stage.
"""

LEFT_PANEL_LINE = (
    "The full problem description is available in the left panel "
    "if you'd like to read through it."
)


def build_intro_opening_instructions(question: str) -> str:
    """Instructions for generating the spoken problem summary in the intro stage."""
    return f"""\
Speak a short spoken introduction to the interview problem below.

Rules for the introduction:
- Summarize only the core task in one or two short sentences.
- Do not mention detailed constraints, examples, input bounds, output bounds,
  or implementation expectations.
- Do not reveal an algorithm or solution approach.
- Do not read the problem statement verbatim.
- Do not ask any questions.
- Do not mention a programming language.
- Use plain spoken language suitable for text-to-speech.
- Stop after the summary.

The interview question is:
---
{question}
---
"""
