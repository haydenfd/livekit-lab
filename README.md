# AlgoVox

AlgoVox is a voice interview app with a Python LiveKit agent and a Next.js browser UI.

```text
web/       Next.js voice interface
server/    Python agent using Groq GPT-OSS 120B and Deepgram STT/TTS
.env       Shared local credentials
```

## Local setup

Keep credentials in the repository root `.env` or `.env.local`:

```env
LIVEKIT_URL=ws://127.0.0.1:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret
GROQ_API_KEY=your_groq_key
DEEPGRAM_API_KEY=your_deepgram_key
```

Start a local LiveKit server in one terminal:

```bash
livekit-server --dev
```

Start the agent in a second terminal:

```bash
uv run --directory server python src/agent.py dev
```

Install and start the web UI in a third terminal:

```bash
cd web
pnpm install
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000) and click **Start interview**.

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
