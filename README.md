# simple-mcp-server

Streamable HTTP Member MCP Server (FastAPI + FastMCP) with 10 in-memory members.

Tools: `get_all_users`, `get_user_by_name`, `get_user_by_email`

## Setup

```
uv sync
```

## Run

```
scripts\start.ps1    # Windows (stop: scripts\stop.ps1)
./scripts/start.sh   # Linux   (stop: ./scripts/stop.sh)
```

Or in the foreground: `uv run uvicorn member_mcp.main:app --port 8000`

- MCP endpoint: `http://127.0.0.1:8000/mcp`
- Health check: `http://127.0.0.1:8000/health`

## Connect from Claude Code

```
claude mcp add --transport http members http://127.0.0.1:8000/mcp
```

## Agent console

Console agent that answers member questions using an OpenRouter LLM (`openai/gpt-oss-120b`) and the MCP tools.

1. Copy `.env.example` to `.env` and set `OPENROUTER_API_KEY`
2. Start the server (above)
3. Run the agent:

```
scripts\start-agent.ps1    # Windows, opens a new console (stop: scripts\stop-agent.ps1)
./scripts/start-agent.sh   # Linux, runs in this terminal (stop: ./scripts/stop-agent.sh)
```

Or directly: `uv run python -m agent`. Type `exit` to quit. The conversation history is appended to `context_history.txt`.

## Test and lint

```
uv run pytest
uv run pylint src tests
```
