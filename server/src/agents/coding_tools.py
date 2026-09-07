"""The two shared coding interaction tools; lifecycle stays in each caller."""

from livekit.agents import RunContext, StopResponse, function_tool

from editor_code import get_current_editor_code
from interview_context import InterviewContext


class CodingTools:
    """Mixin shared by the primary agent and the temporary follow-up task."""

    _reviewed_code: str | None = None

    @function_tool()
    async def continue_silently(self, context: RunContext[InterviewContext]) -> None:
        """End silently while the candidate is implementing and does not expect interviewer participation."""
        raise StopResponse()

    @function_tool()
    async def get_current_code(self, context: RunContext[InterviewContext]) -> str:
        """Retrieve current editor code before inspecting, reviewing, debugging, or judging the implementation."""
        self._reviewed_code = None
        code = await get_current_editor_code(context)
        self._reviewed_code = code
        return code
