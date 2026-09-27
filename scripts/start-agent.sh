#!/usr/bin/env sh
# Start the Member agent console in this terminal (Linux).
cd "$(dirname "$0")/.." || exit 1

if [ -f agent.pid ] && kill -0 "$(cat agent.pid)" 2>/dev/null; then
    echo "Agent already running (PID $(cat agent.pid))."
    exit 1
fi

uv sync --quiet
echo $$ > agent.pid
exec .venv/bin/python -m agent
