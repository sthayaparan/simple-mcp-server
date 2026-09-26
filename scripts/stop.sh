#!/usr/bin/env sh
# Stop the Member MCP Server (Linux).
cd "$(dirname "$0")/.." || exit 1

if [ ! -f server.pid ]; then
    echo "Server not running."
    exit 1
fi

kill "$(cat server.pid)" 2>/dev/null
echo "Server stopped (PID $(cat server.pid))."
rm server.pid
