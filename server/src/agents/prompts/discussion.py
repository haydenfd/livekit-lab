"""Discussion-stage prompt and setup instructions."""

from interview_question import InterviewQuestion, build_discussion_question_context

DISCUSSION_PROMPT = """\
You are currently in the discussion stage.

The intro stage has already summarized the core task and told the candidate
that the full problem description is available in the left panel.

The candidate may now ask clarification questions about the problem.

Invite exactly one question about the full question. Answer that one content
question directly and briefly, then immediately invoke `finish_discussion`.

Do not recite the full problem statement aloud.
Do not volunteer an algorithm, solution, evaluation, or feedback.
Do not ask another question after the one permitted clarification.

The full interview question is:
{question}
"""


def build_discussion_prompt(question: InterviewQuestion) -> str:
    """Add a question's candidate-visible context to the discussion-stage instructions."""
    return DISCUSSION_PROMPT.format(
        question=build_discussion_question_context(question)
    )
