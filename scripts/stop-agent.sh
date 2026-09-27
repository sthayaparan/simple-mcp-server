#!/usr/bin/env sh
# Stop the Member agent console (Linux).
cd "$(dirname "$0")/.." || exit 1

if [ ! -f agent.pid ]; then
    echo "Agent not running."
    exit 1
fi

kill "$(cat agent.pid)" 2>/dev/null
echo "Agent stopped (PID $(cat agent.pid))."
rm agent.pid
