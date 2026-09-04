SHELL := /bin/zsh

ENV_FILE := .env.local

.PHONY: setup dev

setup:
	@command -v uv >/dev/null || { echo "Missing uv. Install it before running make dev."; exit 1; }
	@command -v npm >/dev/null || { echo "Missing npm. Install Node.js before running make dev."; exit 1; }
	@command -v lk >/dev/null || { echo "Missing the LiveKit CLI (lk). Install it before running make dev."; exit 1; }
	@command -v livekit-server >/dev/null || { echo "Missing livekit-server. Install it before running make dev."; exit 1; }
	@test -f "$(ENV_FILE)" || { echo "Missing $(ENV_FILE). Copy .env.example to $(ENV_FILE) and fill in the provider keys."; exit 1; }
	@test -x web/node_modules/.bin/next || { echo "Missing web dependencies. Install them once, then rerun make dev."; exit 1; }
	uv sync --directory server

dev: setup
	@set -a; source "$(ENV_FILE)"; \
		: "$${LIVEKIT_URL:=ws://127.0.0.1:7880}"; \
		: "$${LIVEKIT_API_KEY:=devkey}"; \
		: "$${LIVEKIT_API_SECRET:=secret}"; \
		export LIVEKIT_URL LIVEKIT_API_KEY LIVEKIT_API_SECRET; \
		pids=(); \
		cleanup() { trap - INT TERM EXIT; kill $$pids 2>/dev/null || true; wait $$pids 2>/dev/null || true; }; \
		trap cleanup INT TERM EXIT; \
		livekit-server --dev --logging.level warn --logging.pion_level error & pids+=($$!); \
		(sleep 1; cd server; exec lk agent dev --dev --log-level INFO) & pids+=($$!); \
		(sleep 2; cd web; exec npm run dev) & pids+=($$!); \
		wait
