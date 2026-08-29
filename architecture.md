# Proposed LiveKit Interview Architecture

> **Design reference only.** This architecture is planned functionality and is not implemented yet. The exact stage graph may change as the interview flow is refined.

## Core model

- One interview = one LiveKit `AgentSession`.
- The `AgentSession` owns the overall realtime voice session, including the room/audio lifecycle, STT/TTS, interruptions, and overall session history.
- One interview stage = one active LiveKit `Agent` subclass.
- Only one stage agent is active at a time, but the same `AgentSession` can hand control between multiple agents over the course of the interview.

```text
                    AgentSession
                         |
                         v
                    IntroAgent
                         |
                      handoff
                         v
                 DiscussionAgent
                         |
                      handoff
                         v
                    CodingAgent
                         |
                      handoff
                         v
                  FollowupAgent
                         |
                      handoff
                         v
                 ConclusionAgent
```

These names and the exact graph are placeholders and may change.

## Why separate stage agents

The primary goal is prompt isolation. Each interview phase should have a narrow, focused system prompt instead of one large prompt containing every stage's instructions.

- `IntroAgent`: intro/problem-presentation behavior.
- `DiscussionAgent`: approach/reasoning behavior.
- `CodingAgent`: implementation-stage behavior.
- `FollowupAgent`: follow-up/complexity behavior.
- `ConclusionAgent`: interview-closing behavior.

Each agent should expose only the tools/transitions relevant to its stage. Available tools can naturally represent outgoing graph edges; deterministic prerequisite validation can be added later.

```text
IntroAgent
  instructions = INTRO_PROMPT
  tools = [move_to_discussion]

DiscussionAgent
  instructions = DISCUSSION_PROMPT
  tools = [move_to_coding]

CodingAgent
  instructions = CODING_PROMPT
  tools = [move_to_followup]

FollowupAgent
  instructions = FOLLOWUP_PROMPT
  tools = [move_to_conclusion]
```

## Agent handoffs

Stage transitions should use LiveKit agent handoffs. A transition tool can return the next `Agent`, which becomes active within the same `AgentSession`.

```python
@function_tool()
async def move_to_coding(...):
    return CodingAgent(...)
```

The important distinction is:

```text
one interview = one AgentSession
one interview stage = one active Agent
```

We do not need one mutable `Agent` instance for the entire interview.

## Conversation history across agents

Switching agents does not lose the candidate's previous conversation. When handing off, copy the previous agent's `ChatContext` into the next agent while excluding the previous stage's instructions.

```python
return CodingAgent(
    chat_ctx=self.chat_ctx.copy(
        exclude_instructions=True
    )
)
```

The next stage receives:

```text
NEW stage-specific system prompt
+ previous user/assistant conversation
- previous stage's system instructions
```

For example, `CodingAgent` receives its coding-specific system prompt plus the prior `DiscussionAgent` conversation, without the discussion-specific system instructions. The goal is conversational continuity with strict stage-prompt isolation.

## `session.history` vs `agent.chat_ctx`

Keep these concepts separate:

- `session.history` is the complete canonical conversation/session history.
- `agent.chat_ctx` is the context supplied to the currently active agent's LLM calls.

This preserves the complete interview transcript while allowing each stage to choose how much historical context its LLM receives.

## Context management

Do not build an elaborate context-management system yet. Initially, preserve prior conversation across handoffs while excluding old stage instructions.

If context size or stale information becomes a problem, this architecture can later support full history, truncated history, summaries, curated stage-specific context, or combinations of structured state and recent turns. This is an optimization that should not require changing the stage-agent architecture.

## Shared interview state

Persistent application state should not depend entirely on conversation history. Use typed `AgentSession.userdata` for information that survives agent handoffs.

Potential examples:

```text
problem
current stage metadata
latest_code
code version
hints already given
timestamps
session metadata
other durable interviewer state
```

Do not define or lock in the final state schema yet. This document only establishes where shared state belongs conceptually.

## Interview stages vs conversational topics

The graph represents major interview phases, not every topic discussed by the candidate. If the candidate is in `CodingAgent` and asks about an earlier edge case, the interviewer can respond naturally without transitioning back to `DiscussionAgent`.

A graph transition should occur because the interview phase changed, not because the subject temporarily changed.

## Pipecat to LiveKit conceptual mapping

| Pipecat concept | Planned LiveKit equivalent |
| --- | --- |
| Flow node | LiveKit `Agent` subclass |
| Node instructions | `Agent.instructions` |
| Node transition function | Function tool returning the next `Agent` |
| Available transitions | Available stage-specific tools |
| `FlowManager` / shared flow state | `AgentSession.userdata` |
| Conversation context | `ChatContext` |
| Node switch | Agent handoff |

## Current non-goals

Do not implement any of this as part of this architecture document.

- Do not modify the LiveKit agent implementation.
- Do not create the stage `Agent` classes yet.
- Do not add LangGraph.
- Do not use `TaskGroup` as the main interview graph.
- Do not build post-interview scoring or evaluation into the live interview graph.
- Do not refactor existing lab code around this architecture yet.

Post-interview candidate evaluation remains separate from the live interviewer. The purpose of this document is only to establish a durable architecture reference for the upcoming LiveKit migration.
