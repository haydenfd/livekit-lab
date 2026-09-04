# Current interview flow

Implementation snapshot, not a proposed design. This document follows the
runtime code and tests in `server/src/`, `server/tests/`, and the browser code
in `web/` as of this revision.

## Current flow

```text
browser token request
  -> LiveKit dispatch: my-agent
  -> IntroAgent
  -> DiscussionAgent
  -> CodingAgent
  -> ConclusionAgent
  -> session shutdown and transcript write
```

`server/src/agent.py` always starts `IntroAgent` with the hardcoded
`REVERSE_LINKED_LIST_QUESTION`. There is no implemented alternate stage entry
path.

## Session startup and shared state

1. The browser starts a session through `web/app/api/token/route.ts`. For every
   agent dispatch in the requested room configuration, the route overwrites
   metadata with `{"programmingLanguage":"python"}`.
2. `my_agent()` in `server/src/agent.py` parses that metadata into
   `InterviewContext(programming_language=...)` and creates one
   `AgentSession` with it as `userdata`.
3. The same `AgentSession`, its `userdata`, and its overall LiveKit history
   remain for the interview. `IntroAgent` and `DiscussionAgent` explicitly copy
   their chat context to the next stage with instructions removed; this keeps
   prior conversational messages while each new agent gets its own stage prompt.
4. `ConclusionAgent` is constructed without a copied `chat_ctx`. The session's
   overall history and `userdata` still remain until shutdown.

The shared voice configuration uses Deepgram STT/TTS and OpenAI Responses LLM
(`server/src/config/agent_session_config.py`). Endpointing is fixed at 1.2 to
2.5 seconds; agent replies are non-interruptible.

## IntroAgent

**Implementation:** `server/src/agents/intro.py`

### Entry

The session always begins here after LiveKit dispatch. `on_enter()` speaks:
“Hey, let's begin when you're ready.”

### Inputs / context

- The hardcoded Reverse Linked List `InterviewQuestion`.
- The session chat context and `InterviewContext` userdata. The class does not
  read `programming_language` itself.

### Current responsibilities

The stage prompt tells the LLM to wait for a clear readiness signal, without
asking another question or beginning discussion. It tries to move into problem
presentation only after that signal.

### Tools and state access

- `move_to_discussion`: the only tool. It is intended for clear candidate
  readiness.
- The question supplies the title and problem statement for the generated
  spoken summary. It does not supply examples or constraints to that summary.
- No editor-code, submission, or external persistence access.

### Completion / transition

When the LLM invokes `move_to_discussion`, the tool waits for two deterministic,
non-interruptible playbacks:

1. An LLM-generated one- or two-sentence problem summary, constrained not to
   reveal an algorithm, examples, constraints, or a language.
2. “The full problem description is available in the left panel if you'd like
   to read through it.”

It then returns `DiscussionAgent` with the same question and copied chat
history. Session userdata is unchanged.

## DiscussionAgent

**Implementation:** `server/src/agents/discussion.py`

### Entry

Reached only when `IntroAgent.move_to_discussion` returns it. It has no
deterministic `on_enter()` speech.

### Inputs / context

- The same question, now formatted with statement, examples, and constraints.
- Conversation history copied from IntroAgent, excluding prior instructions.
- Session userdata remains available, but this class does not read it.

### Current responsibilities

The prompt directs the LLM to answer factual specification questions briefly,
let the candidate develop an approach, and probe only material unresolved
reasoning. It is not supposed to reveal a solution, certify an approach, or
proactively discuss complexity.

### Tools and state access

- `start_coding`: the only tool. It is intended once the candidate has a
  coherent, implementable approach without a known blocking correctness flaw.
- It has no editor RPC, persistence, execution, or structured approach record.
  The proposed approach is available only in the copied conversation history.

### Completion / transition

The stage remains active while the candidate is clarifying or developing an
approach. When the LLM invokes `start_coding`, the tool says “Go ahead and
start implementing your approach.”, waits for playback, and returns
`CodingAgent` with the same question and copied chat history. Userdata is
unchanged.

## CodingAgent

**Implementation:** `server/src/agents/coding.py` and
`server/src/agents/prompts/coding.py`

### Entry

Reached only when `DiscussionAgent.start_coding` returns it. It has no
deterministic entry speech and disables interruptions at the agent level.

### Inputs / context

- The same question, including statement, examples, and constraints.
- The copied discussion history. This is how it knows the candidate's proposed
  approach; there is no separate approach object or evaluator result.
- The session, room, and `InterviewContext` userdata. The implementation does
  not read `programming_language`.

### Current responsibilities

The prompt tells the LLM to remain silent during ordinary implementation
narration, answer direct questions concisely, and avoid giving the solution. It
must obtain the current editor code before reviewing, validating, debugging, or
judging it. The implementation is not executed.

### Tools and state access

- `continue_silently`: raises `StopResponse`, ending the current response with
  no speech. The prompt directs its use for narration that does not request
  interviewer participation.
- `get_current_code`: selects exactly one standard remote participant and calls
  its `editor.get_current_code` RPC with a three-second timeout. It returns the
  current code string to the LLM.
- `finish_coding`: available only after a successful, fresh full-code review
  that the LLM considers correct enough for expected test cases.

The browser's `CodeEditor` keeps only the latest textarea value in a React ref
and registers that RPC in
`web/components/editor/editor-code-context.ts`. Only a participant identified
as an agent can call it. Responses over LiveKit's 15 KiB RPC limit are rejected.
The browser displays a static `python` label and starts with an empty editor;
the question's `starter_code` is not loaded into it.

### Completion / transition

Clear completion language prompts the LLM to call `get_current_code` again,
review the returned complete code against the problem and chat history, and:

- If it finds a meaningful issue, remain in `CodingAgent` and ask one concise
  interviewer-style question. It does not invoke `finish_coding`.
- If it judges the implementation correct enough, invoke `finish_coding`.
  That tool deterministically says “Yep, this implementation looks good to go.”,
  waits for playback, and returns `ConclusionAgent`.

### Current submission and persistence behavior

There is no submission action, submission counter, code execution, test run, or
server-side code store. `get_current_code` is a pull of the editor's current
in-memory value; the agent logs RPC identity, duration, and byte count, not the
code itself. It does not save that returned code in session userdata or a file.

If no single standard candidate participant exists, or the RPC fails or times
out, `get_current_code` raises a `ValueError` indicating code is unavailable.
It performs no retry, no automatic transition, and no persistence. The exact
spoken follow-up after that tool error is not deterministic in Python code; it
depends on the LLM applying its prompt.

## ConclusionAgent

**Implementation:** `server/src/agents/conclusion.py`

### Entry

Reached only when `CodingAgent.finish_coding` returns it. No copied chat context
is passed into its constructor.

### Inputs / context

The class has an empty instruction string and no tools. The still-active session
retains its history and userdata, although this class does not inspect either.

### Current responsibilities

It does not ask a question or ask the LLM to generate a closing response.

### Completion / transition

`on_enter()` deterministically says “We're done for now”, waits for playback,
then calls `session.shutdown()`. There is no next interview node.

`create_room_options()` sets `delete_room_on_close=False`. The shutdown callback
registered by `TranscriptionService` writes one JSON transcript after the
session closes to `server/logs/session_<number>_<MMDDYYYY>.json`. It includes
only non-empty user and assistant spoken messages plus job, room, and timestamp
metadata; it does not include editor code, tool calls, or handoff records.

## Development-only startup paths

No `INTERVIEW_START_STAGE` environment variable, stage-selection flag, or other
development shortcut exists in the current codebase. `my_agent()` always starts
with `IntroAgent`; `CodingAgent` is reachable only through the two preceding
LLM tool transitions.

The opt-in `server/tests/test_coding_agent_eval.py` sends sample turns to a real
LLM only when `RUN_LIVEKIT_EVALS=1` and `OPENAI_API_KEY` is configured. It tests
the prompt's intended silence behavior; it does not change runtime stage entry.

## Known limitations / incomplete areas

- One question is hardcoded: Reverse Linked List. The browser dispatch metadata
  is also hardcoded to `python`; `InterviewContext` accepts other strings, but
  no implemented agent uses the language value.
- Code correctness is an LLM review of a fetched snapshot. There is no compiler,
  test runner, deterministic validator, or persisted submission record.
- The token route explicitly rejects normal production use unless
  `IS_VERCEL_PREVIEW=true`, because it has no authentication layer.
- A code-RPC failure has no deterministic recovery dialogue in application code.

## Future/design references — not implemented

`architecture.md` describes a `FollowupAgent` between Coding and Conclusion,
with a `move_to_followup` transition. No `FollowUpAgent` or `FollowupAgent`
class, prompt, tool, or runtime transition exists. Current code transitions
directly from `CodingAgent` to `ConclusionAgent`.

`PLANS.md` describes potential structured code submissions, session-userdata
storage, deterministic checks, an evaluator task, revision loops, and a later
follow-up phase. Those are design references only; none exist in the current
implementation.

## Notable documentation discrepancies

- `architecture.md` shows `CodingAgent -> FollowupAgent -> ConclusionAgent`;
  the implementation is `CodingAgent -> ConclusionAgent`.
- `server/README.md` advertises “adaptive interruptions,” while the active
  session configuration uses fixed endpointing and explicitly disables
  interruptions.
