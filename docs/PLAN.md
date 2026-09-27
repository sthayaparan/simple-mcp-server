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

## Agent Console

Simple Python console agent that takes a user prompt, sends it together with the member MCP tool definitions to an LLM via OpenRouter, runs whichever tools the LLM chooses against `http://127.0.0.1:8000/mcp`, and prints the final answer.

### Agent Tech Stack

| Concern    | Choice                                                                 |
|------------|------------------------------------------------------------------------|
| LLM access | OpenRouter via the `openai` SDK (`AsyncOpenAI`, `base_url="https://openrouter.ai/api/v1"`) |
| Model      | `openai/gpt-oss-120b`                                                  |
| MCP client | `fastmcp.Client` over Streamable HTTP (already a dependency)           |
| Config     | `python-dotenv`, reads `OPENROUTER_API_KEY` from `.env`                |

### Agent Layout

```
src/
  agent/
    __init__.py
    __main__.py    # entry point: asyncio.run(main())
    main.py        # config, tool conversion, LLM/tool loop, console loop
scripts/
  start-agent.ps1, stop-agent.ps1   # Windows
  start-agent.sh, stop-agent.sh     # Linux
tests/
  test_agent.py
.env.example       # OPENROUTER_API_KEY=
```

The `agent` folder sits next to `member_mcp` under `src/` so it uses the same src layout and packaging.

### Agent Design

- Config: `load_dotenv()`. `OPENROUTER_API_KEY` is required. `MODEL = "openai/gpt-oss-120b"` and `MCP_URL = "http://127.0.0.1:8000/mcp"` are module constants.
- `to_openai_tools(tools)`: converts each MCP tool (`name`, `description`, `inputSchema`) to an OpenAI function tool `{"type": "function", "function": {"name", "description", "parameters"}}`.
- `ask(llm, mcp, tools, messages) -> str`: calls `chat.completions.create(model, messages, tools)`. If the reply has `tool_calls`, it runs each one with `mcp.call_tool(name, json.loads(arguments))`, appends the result as a `role="tool"` message, and calls the LLM again. When the reply has no tool calls, it returns the reply text.
- Conversation history is kept on the agent side, because the chat completions API is stateless. `main()` holds one in-memory `messages` list for the session. The list collects the user prompts, the assistant tool-call messages, the `tool` result messages and the final assistant answers, and it is sent in full on every LLM call. This lets follow-up questions work. The in-memory history is lost when the console exits, but it is also written to a file for later review (see below).
- History file: `HISTORY_FILE = <project root>/context_history.txt`, opened in append mode so earlier sessions are kept.
  - At session start, `main()` writes a header line: `=== Session <ISO timestamp> ===`.
  - After each turn, `append_history(path, messages)` appends the messages added in that turn: the user prompt, the assistant tool calls, the tool results and the final answer.
  - Each message is written as one JSON line, with SDK message objects converted via `model_dump(exclude_none=True)`.
  - The file is in `.gitignore`.
- `main()`: opens `fastmcp.Client(MCP_URL)` and lists the tools once. It then loops: `input("> ")`, appends the prompt to `messages`, calls `ask`, and prints the answer. Typing `exit`/`quit` or pressing Ctrl+C/Ctrl+D ends the session.
- Run: `uv run python -m agent` (the MCP server must be running).
- Scripts: the console is interactive, so it has to run in a terminal.
  - `start-agent.ps1` runs `uv sync`, then opens the agent in a new console window with `Start-Process` and writes `agent.pid`.
  - `start-agent.sh` runs `uv sync`, writes its own PID to `agent.pid`, and then `exec`s the agent in the current terminal.
  - `stop-agent.ps1` / `stop-agent.sh` kill the PID in `agent.pid` and remove the file.

### Phase 9 - Agent Scaffolding

- [x] Runtime deps added: `openai`, `python-dotenv`
- [x] `src/agent` package created and included in the build (`uv run python -m agent` resolves)
- [x] `.env.example` added with `OPENROUTER_API_KEY=`; `.env` confirmed in `.gitignore`
- [x] `agent.pid` and `context_history.txt` added to `.gitignore`

### Phase 10 - Agent Implementation

- [x] `to_openai_tools` converts the 3 MCP tools to OpenAI function-tool format
- [x] `ask` runs the tool-call loop and returns the final text
- [x] Session history (prompts, tool calls, tool results, answers) kept in `messages` and sent on every LLM call
- [x] Each turn's messages appended to `context_history.txt` in the project root as JSON lines, under a per-session header
- [x] Console loop reads prompts, prints answers, and exits cleanly on `exit`/`quit`/EOF

### Phase 11 - Agent Unit Tests

`tests/test_agent.py` (no network: MCP uses the in-memory `fastmcp.Client(mcp)`, and the LLM is a fake that returns scripted responses):

- [x] `to_openai_tools` produces 3 function tools with the correct names, descriptions and parameter schemas
- [x] `ask` with a direct answer (no tool calls) returns that text and makes no MCP calls
- [x] `ask` with a `get_user_by_email` tool call runs the tool, sends the member JSON back as a `tool` message, and returns the final text
- [x] `ask` handles several tool calls in one reply and in consecutive replies
- [x] After `ask`, `messages` holds the assistant tool-call message, the matching `tool` result (same `tool_call_id`) and the final answer, in order
- [x] A second prompt in the same session sends the full earlier history to the LLM
- [x] `append_history` (writing to `tmp_path`) writes one valid JSON line per message, and appends on a second call instead of overwriting
- [x] `uv run pytest` - all tests (server + agent) pass
- [x] `uv run pylint src tests` - 10.00/10

### Phase 12 - Agent Scripts and Manual Verification

- [x] `scripts/start-agent.ps1` / `stop-agent.ps1` verified on Windows: start opens the console, stop closes it, and the PID file is removed
- [x] `scripts/start-agent.sh` / `stop-agent.sh` pass `sh -n`
- [x] Manual end-to-end check with a real `OPENROUTER_API_KEY` and the server running:
  - [x] "List all members" calls `get_all_users` and prints 10 members
  - [x] "What is the email of <name>?" calls `get_user_by_name` (in the run, the LLM answered the email from the earlier `get_all_users` result in history, then called `get_user_by_name` for the mobile follow-up)
  - [x] "Who owns <email>?" calls `get_user_by_email`
  - [x] A follow-up question (for example "What is their mobile?") is answered from the session history
  - [x] An unknown name gets a sensible "not found" answer
  - [x] `context_history.txt` in the project root contains the session header and every prompt, tool call, tool result and answer from the session
- [x] README updated with a short Agent section: set up `.env`, start the server, run the agent

## Recommendations (Out of Scope)

- Consider ruff for future work: a single fast tool for both linting and formatting, which could replace Pylint and add the formatting step Pylint does not provide.

## Definition of Done

All phase checkboxes ticked, full test suite green, lint clean, CI green on GitHub, the server running at `http://127.0.0.1:8000/mcp`, and the agent console answering member questions through the MCP tools.
