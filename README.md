# AlgoVox

AlgoVox is a voice interview app with a Python LiveKit agent and a Next.js browser UI.

```text
web/       Next.js voice interface
server/    Python agent using OpenAI GPT-5.6 and Deepgram STT/TTS
.env       Local development credentials; never commit this file
```

## Current interview flow

Read [the implementation snapshot](docs/interview-flow.md) for the current
node-by-node interview lifecycle, editor-code access, state handoffs, and known
incomplete areas.

## Deploy to LiveKit Cloud

This project uses LiveKit Cloud for rooms, agent dispatch, and production agent
hosting.

1. Create or select a project in [LiveKit Cloud](https://cloud.livekit.io), then
   install the [LiveKit CLI](https://docs.livekit.io/intro/basics/cli/).
2. Authenticate the CLI and set the deployment project:

```bash
lk cloud auth
lk project set-default "your-project-name"
```

3. Copy `.env.example` to `.env` in the repository root and add your Cloud and
   provider credentials:

```env
LIVEKIT_URL=wss://your-project-subdomain.livekit.cloud
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret
OPENAI_API_KEY=your_openai_key
DEEPGRAM_API_KEY=your_deepgram_key
```

4. Create the Cloud deployment from the agent directory. This registers the
   agent, stores its identifier in `server/livekit.toml`, uploads the Docker
   build, and securely imports provider secrets from the root `.env`.

```bash
(cd server && lk agent create --secrets-file ../.env)
```

5. Verify the deployed agent, then tail its logs:

```bash
(cd server && lk agent status)
(cd server && lk agent logs)
```

After the first deployment, publish a new version with:

```bash
(cd server && lk agent deploy)
```

LiveKit Cloud supplies `LIVEKIT_URL`, `LIVEKIT_API_KEY`, and
`LIVEKIT_API_SECRET` to deployed agents. Do not add those three values as agent
secrets; the CLI imports the provider keys from `.env` instead.

## Develop against LiveKit Cloud

Install the project dependencies once:

```bash
uv sync --directory server
pnpm --dir web install
```

Start the agent worker and web app in separate terminals:

```bash
# Terminal 1
cd server && lk agent dev

# Terminal 2
cd web && pnpm dev
```

Open [http://localhost:3000](http://localhost:3000) and click **Start interview**.
The browser and worker connect to the same LiveKit Cloud project using the root
`.env` file. Press `Ctrl-C` in each terminal to stop development.

The browser receives a short-lived participant token from `web/app/api/token/route.ts`; the LiveKit API secret never goes to the browser.

## Terminal-only testing

```bash
uv run --directory server python src/agent.py console --text
```

Console mode exercises the agent without joining a Cloud room. Use `lk agent dev`
when testing browser-based interviews.

## Interview session metadata

The web token route currently dispatches each configured agent with
`{"programmingLanguage":"python"}`. The metadata is session-scoped and reaches
every agent stage through this flow:

```text
future Supabase preferences
  -> token/session creation
  -> RoomAgentDispatch.metadata
  -> ctx.job.metadata
  -> AgentSession.userdata (InterviewContext)
  -> all graph stages and handoffs
```

`InterviewContext.programming_language` accepts any string. Missing or malformed
metadata is non-fatal and produces `None`; Supabase-backed creation can replace
only the token-route origin later.

## Notes

### Room creation

- Browser clicks start() interview, which triggers a POST /api/token. useSession(..., { agentName: "my-agent" }) supplies agent dispatch config
- Generates a 15-minute signed join token and a unique name
- Browser connects to the configured `LIVEKIT_URL` with that token.


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

`session.history` is a LiveKit `ChatContext`. Its canonical, ordered data is `session.history.items`, not a list of transcript strings. The items can include messages, tool calls and outputs, agent handoffs, and agent configuration changes. See [LiveKit Chat context documentation](https://docs.livekit.io/agents/logic/chat-context/).

Representative `session.history.to_dict(exclude_timestamp=False)` data looks like this (optional fields are shown only where useful):

```json
{
  "items": [
    {
      "id": "item_user_1",
      "type": "message",
      "role": "user",
      "content": ["What is the weather?"],
      "interrupted": false,
      "created_at": 1700000000.0
    },
    {
      "id": "item_call_1",
      "type": "function_call",
      "call_id": "call_weather_1",
      "name": "get_weather",
      "arguments": "{\"city\": \"San Francisco\"}",
      "created_at": 1700000001.0
    },
    {
      "id": "item_output_1",
      "type": "function_call_output",
      "call_id": "call_weather_1",
      "name": "get_weather",
      "output": "Sunny, 18 C",
      "is_error": false,
      "created_at": 1700000002.0
    },
    {
      "id": "item_handoff_1",
      "type": "agent_handoff",
      "old_agent_id": "intake",
      "new_agent_id": "weather",
      "created_at": 1700000003.0
    },
    {
      "id": "item_config_1",
      "type": "agent_config_update",
      "instructions": "Answer weather questions concisely.",
      "tools_added": ["get_weather"],
      "tools_removed": [],
      "created_at": 1700000004.0
    }
  ]
}
```

- A `message` has `id`, `type`, `role`, `content`, `interrupted`, `metrics`, `extra`, and Unix-second `created_at`; `transcript_confidence` is optional. `content` can contain text and non-text content such as images. A message item's `text_content` property derives readable text from its `content` (joining text parts); it is not a serialized item field.
- A `function_call` has `id`, `type`, `call_id`, `name`, `arguments`, `created_at`, `extra`, and optional `group_id`. Its matching `function_call_output` has `id`, `type`, `call_id`, `name`, `output`, `is_error`, and `created_at`.
- An `agent_handoff` has `id`, `type`, optional `old_agent_id`, `new_agent_id`, and `created_at`. An `agent_config_update` has `id`, `type`, optional `instructions`, `tools_added`, `tools_removed`, and `created_at`.

This app's saved JSON is deliberately narrower than `session.history`: after the LiveKit session fully closes, `TranscriptionService` keeps only non-empty `user` and `assistant` `message` items. Each saved transcript entry contains `id`, `role`, `text` (from `text_content`), ISO-8601 `timestamp`, `interrupted`, and optional `transcript_confidence`.

Each finished session produces one JSON file named `session_<next-number>_<MMDDYYYY>.json`. The sequence is shared by all files in the log directory and continues across process restarts.

- Local agent: `server/logs/`
- Docker container: `/app/logs/`

Docker container files disappear when the container is replaced unless `/app/logs/` is mounted to durable storage. For a local bind mount, use `-v "$(pwd)/server/logs:/app/logs"` when starting the container.
