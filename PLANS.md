

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
- Logic around looping with follow ups, code submissions (should i just start with code finishes with follow ups, and then moves onto conclusion, or try looping back into coding for follow ups -- more complex)
- Should user context show explanation for the problems too? or just testcase with solution for (1 or 2 cases) and images (from leetcode)
- How should it work with evaluating approaches? One agent (luna 5.6 for llm that can do this?). Like the boundary around brute forcing. Sometimes if users first suggestion is brute force but brute force is very unreasonable approach, it might not say that this approach should be acceptable and instead force user to think of a cleaner approach. Or sometimes brute force is the first natural approach and one that can be used for the initial case, but then the user needs to implement it and then follow up for optimizations will be most important (so coding follow up loop). Sometimes, brute force is the only way so it should be acceptable from the get go. Users might not always give the most optimal approach, but you see why this is important now? thats kinda what im getting at in terms of what to explore.
- sometimes when the user is talking, they might be talking in full proper loops where the thought will be end of turn evaluated or like a prper answer. but the problem is, sometimes the bot shouldnt necessarily be repeating or asking for follow ups. maybe not even respond at all, but i dont know if this is a prompting specific thing, or maybe just say mhmm etc
- Speed of bot talking
- Problem structure (Images, examples, testcases) -> static assets, explanation(s), what about def for DS
