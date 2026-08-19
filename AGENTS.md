# LiveKit Dev Lab

This repository is a minimal TypeScript LiveKit voice-agent lab.

## Project layout and commands

- `server/src/agent.ts` is the LiveKit Agents worker entrypoint.
- `server/src/` contains agent behavior, providers, voice sessions, and dev tooling.
- `client/src/` contains the frontend voice console.
- Use the existing npm scripts and root `Makefile`; this repository uses `package-lock.json`, not pnpm.
- `make lab` starts the local server, agent, token service, and client. Use `make stop` to stop them.

## LiveKit development

- Consult the current LiveKit Node.js documentation before using or changing LiveKit APIs. Prefer the LiveKit Docs MCP server configured in `mcp.json`; use the docs overview or page retrieval first, then documentation search when needed.
- Verify that an API or feature is supported by the Node.js Agents SDK rather than assuming parity with Python.
- Keep the lab minimal and preserve its existing entrypoints and local-development workflow.
- For changes to agent behavior, tools, instructions, workflows, or handoffs, write focused tests first and run the relevant tests before declaring success.
- Never commit credentials. Use `.env` for local secrets and keep `.env.example` free of real keys.

## LiveKit Docs MCP

- The canonical project manifest is `mcp.json`; it exposes LiveKit documentation at `https://docs.livekit.io/mcp` over Streamable HTTP.
- Codex loads the project-specific adapter in `.codex/config.toml` when this repository is trusted.
- OpenCode loads the native project adapter in `opencode.json`; use the `livekit-docs` server by name when prompting.
- Other MCP-compatible clients, including DeepSeek, Kimi, and GLM-based hosts, should import or reference `mcp.json` using their native project configuration or MCP config-file option.
- If the documentation reveals a concrete gap or broken example, add documentation feedback to the task and submit it after the implementation is complete.
