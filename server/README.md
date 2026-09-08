<a href="https://livekit.io/">
  <img src="./.github/assets/livekit-mark.png" alt="LiveKit logo" width="100" height="100">
</a>

# AlgoVox Python Agent

A minimal AlgoVox voice interviewer built with [LiveKit Agents for Python](https://github.com/livekit/agents).

The starter project includes:

- OpenAI `gpt-5.6` as the interviewer brain
- Deepgram Nova 3 for speech-to-text
- Deepgram Aura 2 for text-to-speech
- A focused interviewer prompt with one-question-at-a-time follow-ups
- Eval suite based on the LiveKit Agents [testing & evaluation framework](https://docs.livekit.io/agents/start/testing/)
- VAD-based turn handling with adaptive interruptions
- [Background voice cancellation](https://docs.livekit.io/transport/media/noise-cancellation/)
- Deep session insights from LiveKit [Agent Observability](https://docs.livekit.io/deploy/observability/)
- A Dockerfile ready for [production deployment to LiveKit Cloud](https://docs.livekit.io/deploy/agents/)

This app is deployed to LiveKit Cloud and connects to the repository's Next.js
web frontend.

## Bounded follow-up v1

Primary coding now saves immutable V1, selects one follow-up silently, and enters
FollowUpAgent. A code-required assessment temporarily runs FollowUpCodingTask,
saves separate V2 evidence, and returns to the same parent before conclusion.
Discussion-only and valid-none paths do not start a coding task.

See [the current flow and dogfooding guide](../docs/interview-flow.md) for schemas,
guards, failure handling, and log events. Lifecycle records are written to
repository-root `logs/followup_<id>.jsonl`; code snapshots remain separate JSON
files alongside them. The console shows the same correlated lifecycle events.

## Using coding agents

This project is designed to work with coding agents like [Cursor](https://www.cursor.com/) and [Codex](https://openai.com/codex/).

For your convenience, LiveKit offers both a CLI and an [MCP server](https://docs.livekit.io/reference/developer-tools/docs-mcp/) that can be used to browse and search its documentation. The [LiveKit CLI](https://docs.livekit.io/intro/basics/cli/) (`lk docs`) works with any coding agent that can run shell commands. Install it for your platform:

**macOS:**

```console
brew install livekit-cli
```

**Linux:**

```console
curl -sSL https://get.livekit.io/cli | bash
```

**Windows:**

```console
winget install LiveKit.LiveKitCLI
```

The `lk docs` subcommand requires version 2.15.0 or higher. Check your version with `lk --version` and update if needed. Once installed, your coding agent can search and browse LiveKit documentation directly from the terminal:

```console
lk docs search "voice agents"
lk docs get-page /agents/start/voice-ai-quickstart
```

See the [Using coding agents](https://docs.livekit.io/intro/coding-agents/) guide for more details, including MCP server setup.

The project includes a complete [AGENTS.md](AGENTS.md) file for these assistants. You can modify this file to suit your needs. To learn more about this file, see [https://agents.md](https://agents.md).

## Run locally against LiveKit Cloud

The repository root `.env` must contain the Cloud project credentials and
provider keys. Install dependencies, then run the worker:

```console
uv sync
lk agent dev
```

Use a separate terminal for the Next.js frontend:

```console
cd ../web && pnpm dev
```

## Deploy to LiveKit Cloud

Authenticate once, select the Cloud project, and create the deployment from
this directory:

```console
lk cloud auth
lk project set-default "your-project-name"
lk agent create --secrets-file ../.env
```

The command creates `livekit.toml`, uploads this directory using the included
`Dockerfile`, and stores provider credentials as Cloud-managed secrets. LiveKit
Cloud injects the LiveKit connection credentials automatically.

Deploy later changes with:

```console
lk agent deploy
lk agent status
lk agent logs
```

In production, use the `start` command:

```console
uv run python src/agent.py start
```

### Start directly in the coding stage

For faster local iteration, set this in the repository-root `.env`:

```env
INTERVIEW_START_STAGE=coding
```

This server-side, process-wide setting skips the intro and discussion stages. It
starts the reverse-linked-list coding stage with a known iterative approach and
speaks a deterministic approval before implementation begins. Restart the server
after changing it. No frontend control is added.

Restore the full interview flow with:

```env
INTERVIEW_START_STAGE=intro
```

`intro` is the default when the variable is omitted. Any other value stops server
startup with an error that lists the accepted values.

## Frontend & Telephony

Get started quickly with our pre-built frontend starter apps, or add telephony support:

| Platform | Link | Description |
|----------|----------|-------------|
| **Web** | [`livekit-examples/agent-starter-react`](https://github.com/livekit-examples/agent-starter-react) | Web voice AI assistant with React & Next.js |
| **iOS/macOS** | [`livekit-examples/agent-starter-swift`](https://github.com/livekit-examples/agent-starter-swift) | Native iOS, macOS, and visionOS voice AI assistant |
| **Flutter** | [`livekit-examples/agent-starter-flutter`](https://github.com/livekit-examples/agent-starter-flutter) | Cross-platform voice AI assistant app |
| **React Native** | [`livekit-examples/voice-assistant-react-native`](https://github.com/livekit-examples/voice-assistant-react-native) | Native mobile app with React Native & Expo |
| **Android** | [`livekit-examples/agent-starter-android`](https://github.com/livekit-examples/agent-starter-android) | Native Android app with Kotlin & Jetpack Compose |
| **Web Embed** | [`livekit-examples/agent-starter-embed`](https://github.com/livekit-examples/agent-starter-embed) | Voice AI widget for any website |
| **Telephony** | [Documentation](https://docs.livekit.io/telephony/) | Add inbound or outbound calling to your agent |

For advanced customization, see the [complete frontend guide](https://docs.livekit.io/frontends/).

## Tests and evals

This project includes a complete suite of evals, based on the LiveKit Agents [testing & evaluation framework](https://docs.livekit.io/agents/start/testing/). To run them, use `pytest`.

```console
uv run pytest
```

## Using this template repo for your own project

Once you've started your own project based on this repo, you should:

1. **Check in your `uv.lock`**: This file is currently untracked for the template, but you should commit it to your repository for reproducible builds and proper configuration management. (The same applies to `livekit.toml`, if you run your agents in LiveKit Cloud)

2. **Remove the git tracking test**: Delete the "Check files not tracked in git" step from `.github/workflows/tests.yml` since you'll now want this file to be tracked. These are just there for development purposes in the template repo itself.

3. **Add your own repository secrets**: You must [add secrets](https://docs.github.com/en/actions/how-tos/writing-workflows/choosing-what-your-workflow-does/using-secrets-in-github-actions) for `LIVEKIT_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET` so that the tests can run in CI.

## Production reference

See the [LiveKit Cloud agent deployment guide](https://docs.livekit.io/deploy/agents/)
for deployment status, logs, rolling releases, and Cloud secret management.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
