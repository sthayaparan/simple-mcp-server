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

## Test and lint

```
uv run pytest
uv run pylint src tests
```
