# Current interview flow

The implemented v1 follows one bounded assessment after primary coding:

```text
IntroAgent → DiscussionAgent → CodingAgent
  → fresh editor snapshot → save immutable V1
  → one silent selector + spoken transition running concurrently
      ├─ valid none / selector failure → ConclusionAgent
      └─ FollowUpAgent
          ├─ discuss → record outcome → ConclusionAgent
          └─ discuss_then_code
              → introduce exact requirement
              → await FollowUpCodingTask
              → capture V2 and complete(CodingOutcome)
              → same FollowUpAgent resumes
              → record resolution → ConclusionAgent
```

The restored FollowUpAgent concludes directly from its original tool function.
There is no additional substantive question or selector call after the task.
Conclusion says “We're done for now” and shuts down the session without deleting
the room. The normal startup remains IntroAgent; the development toggle still
supports starting CodingAgent.

## Contracts

`FollowUpPlan` is a frozen, validated Pydantic model in
`server/src/followup.py`. JSON uses an array for the rubric; Python stores it
as a tuple to prevent mutation.

| Field | Type / meaning |
| --- | --- |
| mode | `none`, `discuss`, or `discuss_then_code`; execution contract |
| kind | Optional string describing what is assessed; never routes agents |
| objective | Optional string; required and nonempty for an assessment |
| opening_question | Optional string; required for assessments, null for none |
| assessment_rubric | Array of nonempty evidence criteria; required for assessments |
| coding_requirement | Nonempty string for discuss_then_code; null otherwise |

A valid none plan can explain the decision in objective. Invalid output is a
technical failure, not a none plan. The selector is instructed to accept valid
alternative solutions and disclose any specifically required technique.

`CodingOutcome` is a frozen Pydantic model with status
(`demonstrated | partial | unable | time_expired`), optional submission_id,
optional final_code, observations, and optional evidence_error. Technical
evidence failures are kept separate from candidate performance. Discussion
outcomes are recorded in state and lifecycle logs without inventing a coding
submission.

## Silent selection

`server/src/followup_selector.py` runs after primary persistence and the existing
complexity checkpoint. It receives the problem/examples/constraints, topic tags,
language, saved code, and spoken user/assistant conversation. Stated complexity
and previously demonstrated concepts are available in that conversation; no
additional extraction or judging model call is added.

The selector shares the model factory used by the interviewer (currently
gpt-5.6 through the LiveKit OpenAI Responses plugin), but creates an isolated HTTP
instance. It uses strict JSON-schema output through `LLM.chat(extra_kwargs=...)`,
no tools, no SDK/HTTP retries, and a 20-second total timeout. Its private context
and response never enter speech or the spoken transcript. It closes its model
connection after the request.

Selection is attempted once. Invalid JSON, invalid mode/field combinations,
timeouts, or provider errors set selector_failure and lead to conclusion.
A valid mode=none remains distinguishable in both state and logs.

While selection runs, the interviewer says “Okay, let's move on.” through TTS,
without another LLM request. Handoff waits for both the selected plan and speech
playout, so the follow-up opening cannot overlap the transition. The line also
fits a transition to conclusion when selection returns none. A slow selector can
still leave a pause after the line; v1 does not repeat fillers. Lifecycle logs
include transition_speech_started and transition_speech_completed.

## Conversational responsibilities

FollowUpAgent receives the selected plan and original accepted code explicitly.
It starts with a fresh conversation and asks the selected opening question once.
It conducts concise probes within that objective. Discussion-only agents expose
only finish_followup. Code-required agents additionally expose start_coding.
Application checks also reject wrong-mode or repeated launches.

For code-required assessments, demonstrated cannot be recorded from discussion
alone. Explicit inability, refusal, partial completion, or expiry can resolve
the assessment. Before launching the task, the parent speaks the fixed coding
requirement. The task receives only this follow-up's preceding conversation,
copied with prior instructions removed, plus the problem, language, original
code, plan, and requirement in its own instructions.

FollowUpCodingTask is an `AgentTask[CodingOutcome]`. It reuses CodingTools and
the shared coding-interaction prompt: silence during narration, on-demand editor
RPC, concise debugging probes, and fresh review on completion. It reviews the
original problem as modified by the selected requirement. It neither selects
follow-ups nor exposes handoff/task-launch tools. A demonstrated completion
requires the current editor to match the last fetched review snapshot.

The task calls complete(outcome). LiveKit 1.6.10 resumes the original parent
instance and merges task conversation into that parent's history. The parent
records the outcome and returns ConclusionAgent, without another LLM routing
decision. See [tasks](https://docs.livekit.io/agents/logic/tasks/) and
[handoffs/context](https://docs.livekit.io/agents/logic/agents-handoffs/).

## Persistence and guards

Existing local exclusive-file creation remains the persistence mechanism.
Submission IDs are UUIDs; version=1 identifies the accepted primary snapshot.
Version=2 uses a distinct submission ID and includes primary_submission_id,
followup_id, available job/room metadata, and the coding outcome. V2 is always
a new file. Optional metadata preserves compatibility with older records.

The existing frozen InterviewContext contains a per-session FollowUpState.
It tracks the primary object/path, selector started/completed/failure, fixed plan,
entered flag, coding-started flag, coding outcome, discussion status, and consumed
flag. Primary-transition and task-completion guards cover operations in flight.
Guards are set before awaits. Parallel function calls are disabled in the
shared model configuration as an additional SDK compatibility precaution.

An accepted primary reference is reused after subsequent errors, never replaced.
The parent caches its conclusion/next agent. Selection cannot run twice,
discussion cannot start coding, the coding task cannot launch another task, and
task return cannot trigger selection. A consumed assessment cannot start again.

On incomplete coding, finish_exercise still fetches and saves current editor
contents as V2. On retrieval failure, final_code is null and evidence_error
explains why; a requested demonstrated outcome becomes partial. Storage failure
retains fetched code in the in-memory outcome with no submission ID, logs the
failure, and permits conclusion. It never reports that a failed save succeeded.

## Dogfooding

1. From `server/`, start the normal flow with
   `INTERVIEW_START_STAGE=intro uv run python src/agent.py dev`.
2. Connect the web frontend, complete the primary implementation, and discuss
   time/space complexity.
3. Inspect repository-root `logs/followup_<id>.jsonl` for the plan, routing,
   outcomes, duration, and submission paths.

The same JSON events appear in the worker console with a “Follow-up” prefix.
To inspect recent events from the repository root:

```sh
rg '"event":' logs/followup_*.jsonl
```

Expected coding-path events:

```text
primary_submission_saved
selector_started
selector_completed                  # full selected plan
followup_entered
coding_started                      # exact requirement
followup_submission_saved           # V2 path, ID, outcome, code byte count
coding_completed
coding_returned_to_followup          # parent_resumed=true
followup_resolved
conclusion_entered
```

Discussion produces discussion_completed instead of coding events. Valid none
produces followup_skipped with reason=none. Technical failures produce
selector_failed and reason=selector_failure. Rejected repeated operations also
emit events. Diagnostics include identifiers and evidence observations, but
raw code remains in submission files and spoken transcripts remain under
`server/logs/`. Diagnostic-write failures do not restart the workflow.

## Deliberate v1 limits and validation

There is no code execution engine, automatic follow-up timer, curated catalog,
secondary judge, or cloud database migration. Correctness/complexity assessment
remains LLM-driven. time_expired is available for explicitly established expiry;
pauses do not cause it. Abrupt disconnects do not guarantee a final editor pull.
Local persistence is not a guarantee across deployment replacement.

The existing development seed describes merging sorted lists while the active
question fixture is Reverse Linked List. This predates follow-ups; use the normal
intro path for coherent dogfooding until the fixture/seed is aligned. Primary
review still fetches again at submission time, so edits during the complexity
checkpoint can differ from its earlier reviewed snapshot; V2 adds an explicit
snapshot-match guard.

Offline regression coverage is in `server/tests/test_followup.py`: primary-save
ordering, one selection, none versus technical failure, strict streaming output,
mode enforcement, separate V2 persistence, partial/unavailable evidence, stale
review snapshots, and overlapping coding launches. One test uses a real LiveKit
AgentSession/AgentTask to verify the same parent resumes and receives the outcome,
without a model, room connection, or audio. Model requests and editor RPCs are
controlled; logs and submissions use temporary directories.

Run `uv run pytest` from `server/`. The suite currently passes 76 cases, with Ruff
lint and formatting checks passing. Live model judgment and voice behavior still
require dogfooding; these deterministic checks do not evaluate prompt quality.
