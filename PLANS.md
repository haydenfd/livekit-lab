

## (1) Agent Session Config.

A starting point for a voice agent that needs to respond quickly in environments with background noise or other speakers. See All options for what each parameter does.

from livekit.agents import AgentSession, TurnHandlingOptions, inference, room_io
from livekit.plugins import ai_coustics

session = AgentSession(
    turn_handling=TurnHandlingOptions(
        turn_detection=inference.TurnDetector(),
        endpointing={
            "mode": "fixed",
            "min_delay": 0.5,
            "max_delay": 3.0,
        },
        interruption={
            "mode": "adaptive",
            "min_duration": 0.5,
            "min_words": 0,
        },
        # preemptive_generation is enabled by default. Opt into preemptive TTS
        # for lower latency at the cost of wasted compute on cancellations.
        preemptive_generation={
            "preemptive_tts": False,
        },
    ),
    # ... stt, tts, llm, etc.
)

await session.start(
    # ...,
    room_options=room_io.RoomOptions(
        audio_input=room_io.AudioInputOptions(
            noise_cancellation=ai_coustics.audio_enhancement(
                model=ai_coustics.EnhancerModel.QUAIL_VF_L,
            ),
        ),
    ),
)

import { inference, voice } from '@livekit/agents';
import * as aiCoustics from '@livekit/plugins-ai-coustics';

const session = new voice.AgentSession({
  turnHandling: {
    turnDetection: new inference.TurnDetector(),
    endpointing: {
      minDelay: 500,
      maxDelay: 3000,
    },
    interruption: {
      mode: 'adaptive',
      minDuration: 500,
      minWords: 0,
    },
    // preemptiveGeneration is enabled by default. Opt into preemptive TTS
    // for lower latency at the cost of wasted compute on cancellations.
    preemptiveGeneration: {
      preemptiveTts: false,
    },
  },
  // ... stt, tts, llm, etc.
});

await session.start({
  // ...,
  inputOptions: {
    noiseCancellation: aiCoustics.audioEnhancement({ model: 'quailVfL' }),
  },
});

For quieter environments, drop the noise cancellation argument from session.start(). The rest of the config still applies.

For SIP participants, swap voice isolation for the telephony-tuned Krisp model: noise_cancellation.BVCTelephony() (Python) or TelephonyBackgroundVoiceCancellation() (Node.js). For multi-speaker rooms, use background noise suppression instead of voice isolation.
All options

The following table lists the options that affect turn-taking, grouped by pipeline stage.
Option	Stage	What it controls	Default
turn_detection mode	User activity detection	How the session decides the user is done speaking. Options: turn detector model, VAD, STT endpointing, realtime LLM, manual.	Auto-selected
endpointing.min_delay	User activity detection	Minimum time after detected silence before the turn closes. In VAD mode this is max(VAD silence, min_delay). In STT mode it adds to the provider's endpoint signal.	0.5 seconds
endpointing.max_delay	User activity detection	Maximum time the agent waits before forcing the turn closed.	3.0 seconds
endpointing.mode	User activity detection	"fixed" always uses the configured delays. "dynamic" adapts within the range based on session pause statistics.	"fixed"
interruption.enabled	Interruption handling	Master on/off toggle for interruptions. Set to False to make the agent uninterruptible.	True
interruption.mode	Interruption handling	"adaptive" (recommended) uses an audio model to distinguish real interruptions from backchannel acknowledgments. "vad" triggers on any detected speech.	"adaptive" if available, otherwise "vad"
interruption.min_duration	Interruption handling	Minimum speech duration to register as an interruption.	0.5 seconds
interruption.min_words	Interruption handling	Minimum word count to register as an interruption. Requires STT.	0
interruption.false_interruption_timeout	Interruption handling	Silence window after a detected interruption before it's classified as false. After this elapses with no transcript, the agent can resume (see resume_false_interruption).	2.0 seconds
interruption.resume_false_interruption	Interruption handling	Whether to resume the interrupted speech after the false-interruption timeout passes.	True
preemptive_generation.enabled	Preemptive generation	Whether to start LLM generation as soon as a final transcript arrives, before the turn is confirmed.	True
preemptive_generation.preemptive_tts	Preemptive generation	Also start TTS preemptively. Cuts more latency at the cost of wasted compute on cancellations.	False
preemptive_generation.max_speech_duration	Preemptive generation	Skip preemptive generation for utterances longer than this. Long turns are more likely to mutate.	10.0 seconds
preemptive_generation.max_retries	Preemptive generation	Cap on preemptive attempts per turn. Resets when the turn completes.	3
Voice isolation	Audio pre-processing	Suppresses competing voices in the input so STT, VAD, and the turn detector see clean audio. Models include ai-coustics QUAIL_VF_L, Krisp BVC, and Krisp BVCTelephony.	Off
Background noise suppression	Audio pre-processing	Suppresses non-speech noise. Use when the main challenge is environmental noise rather than competing speakers.	Off
min_consecutive_speech_delay	Agent speech scheduling	Minimum gap between consecutive agent utterances. Does not affect user-side turn detection.

That is the entire turn taking config for turn taking tuning. i want you to define a config object for the agent_session with these arguments passed in. for now, abstract away what you have defined in the agent into like a config object that depends on the above settings. i want you to include all of them in but for those parameters not currently configured in the active agent session setup, just comment it out. the reason im doing this is because if i want to later tune stuff, i have a quick reference of what parameters can be specified for this agent session to make sure i can quickly tune its parameters and change results. does that make sense? for the options we arent currently specifying, just also add a comment above for what this particular parameter is for exactly. you can either comment out the parameter and its setting(s) or just leave it active but set it to its default, whatever works. please double check the docs using the skills/mcp as well.

## (2) README update

session.history object in the readme doesnt have perfect documentation for what's exactly in the session.history object, id like more specifics bro. right now its just very vague qualitative points. but i want you to replace it with specific facts or actual examples of data/fields in the object so i understand. do your research on whats in it by researching, and then update your writeup on that part.


## (3) Session Metadata

We want to prototype how a user's configured programming language flows into the LiveKit interview agent.

In production, the programming language will come from the user's persisted preferences in Supabase when an interview session is created. That session-level configuration should then be passed into the LiveKit agent through the appropriate startup metadata/context mechanism and remain available throughout the conversation graph.

For now, do not integrate Supabase. Simply hardcode the language to `python` at the point where this session metadata would normally originate, then wire it through the same path we would expect to use in production.

The goal is to establish this conceptual flow:

```text
User preferences / session configuration
        ↓
LiveKit startup metadata
        ↓
shared interview context
        ↓
conversation graph / agents
```

The language should be treated as interview-level context, not inferred from the candidate's code and not treated as STT/LLM/TTS configuration.

We mainly want to prove that a value originating at session startup can make its way into the agent conversation and remain accessible later when we eventually need language-aware coding behavior or evaluation.

Keep the implementation minimal and consistent with the existing LiveKit architecture. Do not redesign the graph or build the future code-evaluation system as part of this.

Also add a short README section explaining the path the programming language takes through the system, including that `python` is currently hardcoded only to mimic the future production flow from Supabase preferences into LiveKit session metadata and then into the interview context.


# Problems I'm facing

- Potential follow up questions to ask for each question and how to go about it. Like agent handoff for generating or what?
  - Do not use a handoff just to generate a follow-up. A handoff should mean the interview has entered a genuinely different phase with different instructions or tools.
  - Store a small follow-up rubric with each interview question: the concepts that must be covered, acceptable approaches, common gaps, hints, and two or three possible probes. The interviewer should choose from that rubric based on what the candidate actually said rather than inventing every probe from scratch.
  - If choosing the next probe requires deeper reasoning, run a short-lived evaluator `AgentTask` that returns a typed result such as `decision`, `missing_concept`, and `suggested_probe`. The active stage agent remains the voice of the interview and turns that result into one concise question.
  - Generate any question-specific rubric before the live interview or when the question is loaded, not while the candidate is waiting. This keeps the spoken path fast and makes the behavior testable.
- Logic around looping with follow ups, code submissions (should i just start with code finishes with follow ups, and then moves onto conclusion, or try looping back into coding for follow ups -- more complex)
  - Keep one `CodingAgent` active while the candidate explains, edits, and submits code. A code submission is a checkpoint inside that phase, not automatically a handoff.
  - Send editor submissions from the browser to the agent as structured LiveKit data or RPC, then save the latest code and submission count in `AgentSession.userdata`. Do not depend on the voice transcript to reconstruct code.
  - On submission, run deterministic checks first, then a scoped code-evaluation task. Its typed result should choose one of three routes: `continue_coding` with one actionable issue, `move_to_followups`, or `finish`.
  - Use a bounded loop: allow a configured number of revision cycles, then move forward or end with the unresolved state recorded. Once the implementation is acceptable, hand off once to `FollowupAgent` for one or two question-specific optimization or complexity probes, then hand off to `ConclusionAgent`.
  - Do not use `TaskGroup` as the main coding loop. LiveKit currently marks it experimental, and its ordered collection/backtracking model fits forms and intake better than an adaptive code-review conversation.
- How should it work with evaluating approaches? One agent (luna 5.6 for llm that can do this?). Like the boundary around brute forcing. Sometimes if users first suggestion is brute force but brute force is very unreasonable approach, it might not say that this approach should be acceptable and instead force user to think of a cleaner approach. Or sometimes brute force is the first natural approach and one that can be used for the initial case, but then the user needs to implement it and then follow up for optimizations will be most important (so coding follow up loop). Sometimes, brute force is the only way so it should be acceptable from the get go. Users might not always give the most optimal approach, but you see why this is important now? thats kinda what im getting at in terms of what to explore.
  - Use a non-speaking approach evaluator behind the active interviewer, not another conversational agent. Give it the exact problem, constraints, candidate approach, and a question-specific rubric, and require a typed result instead of free-form advice.
  - Classify the approach as `reject_now`, `acceptable_then_optimize`, `acceptable_final`, or `insufficient_information`. Base that decision on whether the approach is correct and feasible under the stated constraints, not on whether it is globally optimal.
  - Encode the brute-force boundary per question. For example, a correct brute-force solution that fits the constraints can proceed and become an optimization follow-up; one that necessarily exceeds the constraints should trigger a single interviewer probe before coding; a problem whose intended solution is exhaustive search should accept it as final.
  - Keep the evaluator from coaching: it should return evidence, complexity, rubric coverage, and the next interview action to the interviewer, never speak directly to the candidate or reveal the solution.
  - Model choice is secondary to the rubric and structured output. Start with one capable, low-latency model for evaluation, then compare it against labeled approach examples. Use a larger model only if the smaller one repeatedly misclassifies borderline approaches; do not add a second live persona solely for model selection.
- sometimes when the user is talking, they might be talking in full proper loops where the thought will be end of turn evaluated or like a prper answer. but the problem is, sometimes the bot shouldnt necessarily be repeating or asking for follow ups. maybe not even respond at all, but i dont know if this is a prompting specific thing, or maybe just say mhmm etc
  - Separate turn detection from response policy. LiveKit should decide when the candidate has stopped speaking; the stage instructions and evaluator should decide whether that completed turn deserves speech.
  - Default to silence while the candidate is thinking aloud. Respond only when they ask a direct question, explicitly finish an explanation, submit code, become inactive for a configured interval, or the evaluator identifies one necessary probe.
  - Do not repeat or summarize every answer. Add a prompt rule that acknowledgments must add information, and prefer a short pause over filler. An occasional “mhm” can sound natural, but generating it on every turn adds latency and can make the candidate think they were interrupted.
  - Use LiveKit's adaptive interruption handling and tune endpointing from real recordings so short thinking pauses do not close the turn too early. Track false interruptions and candidate-to-agent latency before changing thresholds.
- Speed of bot talking
  - Treat response latency and spoken pace as separate controls. First measure end-of-turn to first audio, LLM time, TTS time, and total playback duration; otherwise a slow response can be mistaken for a slow voice.
  - For latency, keep each stage prompt and tool list narrow, preload question/rubric data, and test LiveKit preemptive generation, which is currently disabled in `agent_session_config.py`. Enable it only after tests confirm that partial candidate turns do not cause incorrect replies.
  - For perceived pace, make spoken responses shorter before changing the voice. One sentence and one question usually feels faster and more interview-like than increasing audio playback speed.
  - The current Deepgram Aura-2 plugin documentation does not expose a speaking-rate parameter. If actual words-per-minute control is required, benchmark a supported TTS provider with an explicit rate setting or choose a naturally faster voice rather than relying on an undocumented Deepgram option.
  - Add a small voice benchmark using the same five interview lines and compare time-to-first-audio, words per minute, intelligibility, and interruption behavior before switching providers or voices.

- Intro sees only title + statement, so its summary generation stays focused.
- Discussion sees everything the candidate can reasonably reference verbally: statement, examples, constraints.
- Hints, tags, starter code, images stay available in application data without leaking into normal interviewer context.
- The raw DB-shaped fixture remains separate from the normalized runtime object.
- The same normalized object flows through the session.

- The rendered discussion block is also good prompt material. It’s compact, readable, and avoids duplicate HTML/raw fields.
