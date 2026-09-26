#!/usr/bin/env sh
# Start the Member MCP Server in the background (Linux).
cd "$(dirname "$0")/.." || exit 1

if [ -f server.pid ]; then
    echo "Server already running (PID $(cat server.pid))."
    exit 1
fi

uv sync --quiet
nohup .venv/bin/python -m uvicorn member_mcp.main:app --host 127.0.0.1 --port 8000 > server.log 2>&1 &
echo $! > server.pid
echo "Server started (PID $!) at http://127.0.0.1:8000/mcp"
