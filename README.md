# AlgoVox

AlgoVox is a voice interview app with a Python LiveKit agent and a Next.js browser UI.

```text
web/       Next.js voice interface
server/    Python agent using Groq GPT-OSS 120B and Deepgram STT/TTS
.env       Shared local credentials
```

## Local setup

Keep provider credentials in the repository root `.env.local`:

```env
LIVEKIT_URL=ws://127.0.0.1:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret
GROQ_API_KEY=your_groq_key
DEEPGRAM_API_KEY=your_deepgram_key
```

Start the local LiveKit server, Python agent, and web UI together:

```bash
make dev
```

The first run installs Python and web dependencies. Local LiveKit development defaults to `ws://127.0.0.1:7880` with `devkey` / `secret` if those values are not already in `.env.local`. Press `Ctrl-C` once to stop all three processes. Open [http://localhost:3000](http://localhost:3000) and click **Start interview**.

The browser receives a short-lived participant token from `web/app/api/token/route.ts`; the LiveKit API secret never goes to the browser.

## Terminal-only testing

```bash
uv run --directory server python src/agent.py console --text
```

Console mode does not require a LiveKit server. The browser UI does, because browsers need a WebRTC signaling and media server.

## LiveKit Cloud later

Replace the local LiveKit values with a Cloud project’s values, authenticate with `lk cloud auth`, and run the agent in `dev` mode. The same web UI can then connect to Cloud instead of the local server.


## Notes

### Room creation

- Browser clicks start() interview, which triggers a POST /api/token. useSession(..., { agentName: "my-agent" }) supplies agent dispatch config
- Generates a 15-minute signed join token and a unique name
- Browser connects to ws://127.0.0.1:7880 with that token. 


### Agent Session

- Main orchestrator for app
- Handles entire voice pipeline and emits events for observability and control

### Agent

- What AgentSession orchestrates
- Defines instructions, tools of app. Framework supports design of custom workflows to orchestrate handoffs, delegation

### How the browser transcript works

The transcript is delivered through the LiveKit room; the browser does not poll the Python agent or call a separate transcript API.

```text
candidate audio
    -> LiveKit room
    -> AgentSession STT
    -> text stream: lk.transcription
    -> browser LiveKit session
    -> useSessionMessages(session)
    -> AgentChatTranscript
```

When the candidate finishes a turn, the agent's STT produces a final text segment. LiveKit Agents publishes that transcription to the `lk.transcription` text stream. The agent's spoken response is published through the same mechanism, aligned with its audio playback. Both sides appear in the browser's session message list as the conversation progresses.

In this app, `web/components/agents-ui/blocks/agent-session-view-01/components/agent-session-block.tsx` calls `useSessionMessages(session)`. It passes the returned `messages` to `web/components/agents-ui/agent-chat-transcript.tsx`, which renders each message as a user or agent bubble. `AgentSessionProvider` supplies the LiveKit session context, so no custom transcript WebSocket, polling loop, or database lookup is needed.

This is LiveKit's current text-stream path for transcriptions. The older `TranscriptionReceived` event and `publish_transcription()` path are deprecated. See [Text and transcriptions](https://docs.livekit.io/agents/multimodality/text/) and [LiveKit chat components](https://docs.livekit.io/frontends/agents-ui/chat/) for the underlying behavior.

## Session history and transcript logging

`session.history` is broader than a spoken transcript: it can include system and developer instructions, tool calls and results, handoffs, configuration updates, and other internal records. `TranscriptionService` intentionally writes only non-empty spoken `user` and `assistant` messages after the LiveKit session has fully closed.

Each finished session produces one JSON file named `session_<next-number>_<MMDDYYYY>.json`. The sequence is shared by all files in the log directory and continues across process restarts.

- Local agent: `server/logs/`
- Docker container: `/app/logs/`

Docker container files disappear when the container is replaced unless `/app/logs/` is mounted to durable storage. For a local bind mount, use `-v "$(pwd)/server/logs:/app/logs"` when starting the container.
