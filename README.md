# LiveKit Dev Lab

A minimal local self-hosted LiveKit server setup plus a minimal TypeScript
LiveKit Agents worker.

## Prerequisites

- [LiveKit server](https://docs.livekit.io/transport/self-hosting/local.md) installed (e.g. `brew install livekit`)
- Node.js 20+
- LiveKit CLI (`brew install livekit-cli`)

## Start the server

```bash
npm run dev
```

which runs:

```bash
livekit-server --dev
```

The server binds to `ws://127.0.0.1:7880` with the standard local dev
credentials:

| Setting            | Value                 |
| ------------------ | --------------------- |
| LIVEKIT_URL        | `ws://127.0.0.1:7880` |
| LIVEKIT_API_KEY    | `devkey`              |
| LIVEKIT_API_SECRET | `secret`              |

Verify it is listening:

```bash
lsof -iTCP:7880 -sTCP:LISTEN -P -n
# or
curl -s http://127.0.0.1:7880
```

> These are **dev-only** credentials. Never use them outside local development.

## Environment

Copy the example env file when you need these values in tooling:

```bash
cp .env.example .env
```

## Start the agent worker

```bash
npm run agent:dev
```

The worker starts in LiveKit Agents development mode and registers with the
local LiveKit server. It does not include STT, LLM, TTS, frontend, token
service, or database code.

## Manual room / agent-join workflow

### 1. Generate a participant token

```bash
npm run dev:token -- --room mylab --identity bob
```

This prints a JWT granting `bob` the minimum normal-participant permissions
(publish, subscribe, publish data) for the `mylab` room. It uses the same
`livekit-server-sdk` APIs a production token service would, but stands alone as
a dev-only CLI.

### 2. Connect a participant to the room

Feed that token into a LiveKit client of your choice, for example the common
LiveKit Web SDK in a playground page, or `lk room join` from the CLI:

```bash
lk room join --url ws://127.0.0.1:7880 --token <TOKEN>
```

Because no room exists yet, the room is created on first join.

### 3. Watch the agent join

With the server and worker running, the registered agent receives the room job
and connects to the same room. The worker prints:

```text
[agent] job "<job-id>" received for room "mylab"
[agent] connected to room "mylab" as "<agent-identity>"
```

## Structure

```text
src/
├── agent.ts               # app bootstrap / LiveKit worker startup only
├── config/
│   └── livekit.ts         # reads + validates LiveKit env config (dev defaults)
├── agent/
│   └── room-entry.ts      # agent job entry handler (connect + log, no AI)
└── dev/
    └── token.ts           # dev-only participant token generator + CLI
```

## Roadmap (not built yet)

- Frontend
- STT / LLM / TTS integration
- Interview logic
- Database code
