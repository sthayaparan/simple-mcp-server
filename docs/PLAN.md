# Member MCP Server - Implementation Plan

MVP of a Streamable HTTP MCP server (FastAPI + FastMCP) exposing member lookup tools to AI clients such as Claude Code CLI.

## Scope

- In-memory data only: 10 hard-coded members (name, email, mobile)
- MCP tools: `get_user_by_name`, `get_user_by_email`, `get_all_users`
- No persistence, no authentication, no user management, no extra features

## Tech Stack

| Concern         | Choice                                        |
|-----------------|-----------------------------------------------|
| Language        | Python 3.14 (latest available locally)        |
| Package manager | uv (project-level `.venv`)                    |
| Web framework   | FastAPI                                       |
| MCP framework   | `fastmcp` standalone package (latest), Streamable HTTP transport |
| Data model      | Pydantic `BaseModel`                          |
| ASGI server     | Uvicorn                                       |
| Testing         | pytest, pytest-asyncio, httpx                 |
| Lint            | pylint (dev dependency)                       |
| CI              | GitHub Actions (`.github/workflows/ci.yml`)   |

## Project Layout

```
simple-mcp-server/
  .github/
    workflows/
      ci.yml         # GitHub Actions: test, lint, script smoke test
  .gitignore
  .python-version
  pyproject.toml
  uv.lock
  README.md
  docs/
    PLAN.md
  scripts/
    start.ps1, stop.ps1   # Windows
    start.sh, stop.sh     # Linux
  src/
    member_mcp/
      __init__.py
      data.py        # Member model + 10 hard-coded members
      server.py      # FastMCP instance and the 3 tools
      main.py        # FastAPI app, mounts MCP at /mcp, /health route
  tests/
    test_data.py
    test_tools.py
    test_app.py
```

## Design

- `data.py`: `Member(BaseModel)` with `name: str`, `email: str`, `mobile: str`; a module-level `MEMBERS: list[Member]` of 10 entries.
- `server.py`: `mcp = FastMCP("Member MCP Server")` with three `@mcp.tool` functions:
  - `get_all_users() -> list[Member]` - returns all 10 members
  - `get_user_by_name(name: str) -> Member | None` - case-insensitive exact match
  - `get_user_by_email(email: str) -> Member | None` - case-insensitive exact match
- `main.py`: build the MCP ASGI app via `mcp.http_app(path="/mcp")`, create `FastAPI(lifespan=mcp_app.lifespan)`, add `GET /health` returning `{"status": "ok"}`, and mount the MCP app at `/`. Endpoint: `http://127.0.0.1:8000/mcp`.
- Run: `uv run uvicorn member_mcp.main:app --port 8000`, or the service scripts.
- Service scripts: `start` runs `uv sync`, launches uvicorn from the project `.venv` in the background, and writes `server.pid` / `server.log`; `stop` kills the PID and removes `server.pid`.

## Phases and Success Criteria

### Phase 1 - Scaffolding

- [x] `uv init --package` style project created with `src/member_mcp` layout
- [x] `.python-version` pinned; `.venv` created at project root by `uv sync`
- [x] Runtime deps added: `fastapi`, `fastmcp`, `uvicorn`
- [x] Dev deps added (`uv add --dev`): `pytest`, `pytest-asyncio`, `httpx`, `pylint`
- [x] pytest configured in `pyproject.toml` (`asyncio_mode = "auto"`, `testpaths = ["tests"]`)
- [x] pylint configured in `pyproject.toml` (`[tool.pylint]` section, defaults unless a rule conflicts with idiomatic FastMCP/pytest code)
- [x] Boilerplate Python `.gitignore` written (`.venv/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `dist/`, `build/`, `*.egg-info/`, `.env`, IDE folders)
- [x] `uv sync` succeeds and `uv run python -c "import fastapi, fastmcp"` succeeds

### Phase 2 - Member Data

- [x] `Member` Pydantic model defined
- [x] Exactly 10 members with unique names and unique emails
- [x] `tests/test_data.py` passes: count is 10, all fields non-empty, names unique, emails unique and contain `@`

### Phase 3 - MCP Tools

- [x] FastMCP server with the 3 tools implemented, each with a clear docstring (used as the tool description)
- [x] `tests/test_tools.py` (using the in-memory `fastmcp.Client(mcp)`) passes:
  - [x] `list_tools` returns exactly the 3 expected tool names
  - [x] `get_all_users` returns 10 members with correct fields
  - [x] `get_user_by_name` finds an existing member (exact and different case)
  - [x] `get_user_by_name` returns no result for an unknown name
  - [x] `get_user_by_email` finds an existing member (exact and different case)
  - [x] `get_user_by_email` returns no result for an unknown email

### Phase 4 - FastAPI Integration (Streamable HTTP)

- [x] FastAPI app mounts the MCP app with the MCP lifespan wired in
- [x] `tests/test_app.py` passes:
  - [x] `GET /health` returns 200 and `{"status": "ok"}`
  - [x] An MCP client over Streamable HTTP (`fastmcp.Client` with the ASGI app / live server) can initialize, list the 3 tools, and call `get_all_users`

### Phase 5 - Quality and Verification

- [x] `uv run pytest` - all tests pass
- [x] `uv run pylint src tests` - no errors or warnings (score 10.00/10)
- [x] Any defects found are fixed and re-tested

### Phase 6 - Service Scripts

- [x] `scripts/start.ps1` and `scripts/stop.ps1` (Windows): start in background, stop by PID
- [x] `scripts/start.sh` and `scripts/stop.sh` (Linux): same behaviour, POSIX `sh`
- [x] Windows scripts verified: start -> `/health` ok -> stop -> server down, PID file removed
- [x] Linux scripts pass `sh -n` syntax check (not run on Linux in this environment)

### Phase 7 - Run and Hand-off

- [x] Minimal `README.md`: what it is, install (`uv sync`), run, test, connect from Claude Code
- [x] Server started with `scripts/start.ps1`
- [x] Manual check: `/health` responds; an MCP client over Streamable HTTP at `http://127.0.0.1:8000/mcp` lists the 3 tools and calls each one successfully (Claude Code connects with `claude mcp add --transport http members http://127.0.0.1:8000/mcp`)
- [x] Server left running and ready for the user

### Phase 8 - Continuous Integration

- [x] `.github/workflows/ci.yml` runs on push and pull request to `main`
- [x] Uses `actions/checkout@v7` and `astral-sh/setup-uv@v7` (uv cache enabled); Python from `.python-version`
- [x] `uv sync --locked` fails the build if `uv.lock` is out of date
- [x] Runs `uv run pytest` and `uv run pylint src tests`
- [x] Smoke-tests the Linux service scripts: `start.sh` -> `/health` ok -> `stop.sh`
- [x] Same commands verified locally (15 tests pass, pylint 10.00/10)
- [ ] First workflow run on GitHub is green (after push)

## Recommendations (Out of Scope)

- Consider ruff for future work: a single fast tool for both linting and formatting, which could replace Pylint and add the formatting step Pylint does not provide.

## Definition of Done

All phase checkboxes ticked, full test suite green, lint clean, CI green on GitHub, and the server running at `http://127.0.0.1:8000/mcp`.
