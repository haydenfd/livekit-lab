# LiveKit Voice Lab — one-command launcher
#
#   make lab        start everything (server, agent, token endpoint, client)
#   make stop       kill anything the lab left running
#
# Ctrl+C stops all four processes.

SHELL := /bin/bash

PORTS := 7880 1591 1590

.PHONY: lab stop logs

lab:
	@mkdir -p .context
	@trap 'kill 0' INT TERM EXIT; \
	( cd server && npm run dev > ../.context/livekit-server.log 2>&1 ) & \
	( cd server && npm run agent:dev > ../.context/agent.log 2>&1 ) & \
	( cd server && npm run token:dev > ../.context/token-server.log 2>&1 ) & \
	( cd client && npm run dev > ../.context/client.log 2>&1 ) & \
	echo ""; \
	echo "LiveKit Voice Lab starting..."; \
	echo "  UI:            http://localhost:1590"; \
	echo "  Token endpoint: http://127.0.0.1:1591/token"; \
	echo "  LiveKit server: ws://127.0.0.1:7880"; \
	echo ""; \
	echo "Logs: .context/*.log  (make logs to tail them)"; \
	echo "Ctrl+C to stop everything."; \
	wait

stop:
	@for port in $(PORTS); do \
		pid=$$(lsof -tiTCP:$$port -sTCP:LISTEN 2>/dev/null); \
		if [ -n "$$pid" ]; then \
			echo "stopping port $$port (pid $$pid)"; \
			kill $$pid 2>/dev/null || true; \
		fi; \
	done

logs:
	@tail -f .context/livekit-server.log .context/agent.log .context/token-server.log .context/client.log
