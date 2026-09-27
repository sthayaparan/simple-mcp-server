# MCP Skill Integration

How to use "skills" to control how the Member agent calls the Member MCP Server tools.

A skill is a set of written instructions for a task: when to use which tool, in what order, how to handle "not found", and how to format the answer. The MCP tools (`get_all_users`, `get_user_by_name`, `get_user_by_email`) do not change. The skill only guides how they are used.

This document describes seven approaches. Every code snippet is labeled with where it lives:

- **Client (Agent)**: `src/agent/...` or `skills/...`. Runs in the console agent process.
- **MCP Server**: `src/member_mcp/...`. Runs in the FastAPI/FastMCP server process.
- **Claude Code**: `.claude/skills/...`. Read by Claude Code, no agent code involved.

The snippets are design examples for planning. They are not implemented in the project yet.

## Current Flow (Baseline)

```
User prompt -> Agent (messages history) -> LLM (OpenRouter)
                                            | tool_calls
Agent <-------------------------------------+
  | mcp.call_tool(...)
  v
MCP Server (get_all_users / get_user_by_name / get_user_by_email)
  | result
Agent -> LLM (tool message) -> ... -> final answer -> Console
```

The LLM chooses tools only from their names, descriptions and schemas. A skill adds task-level guidance on top of that.

## Example Skill File

All the approaches below use this skill.

**Location: Client (Agent)**, file `skills/member-lookup/SKILL.md` in the project root. In approach 4 the same text is served by the MCP Server instead.

```markdown
---
name: member-lookup
description: Find a member's contact details from a full name, partial name or email.
allowed-tools: [get_user_by_name, get_user_by_email, get_all_users]
---
# Member Lookup

1. If the input contains "@", call get_user_by_email.
2. Otherwise call get_user_by_name with the full name.
3. If the result is null, call get_all_users and suggest up to 3 members
   whose names are closest to the input.
4. Answer in the format: Name - email - mobile
5. Never invent member data. Only use tool results.
```

- The frontmatter (`name`, `description`, `allowed-tools`) is metadata that the agent reads.
- The body is the instruction text that the LLM follows.

---

## 1. Skill File as the System Prompt

**Idea:** at startup, load the skill body into the system message. The LLM always sees the instructions.

**Where:** Client (Agent) only. The MCP Server is unchanged.

**Location: Client (Agent)**, `src/agent/main.py`

```python
SKILL_FILE = Path(__file__).parents[2] / "skills" / "member-lookup" / "SKILL.md"

async def main() -> None:
    ...
    skill = SKILL_FILE.read_text(encoding="utf-8")
    messages: list[dict] = [{"role": "system", "content": f"{SYSTEM_PROMPT}\n\n{skill}"}]
    ...
```

`ask()` does not change.

| Pros | Cons |
|------|------|
| Trivial to implement | Every skill costs tokens on every call |
| Always applied | Does not scale past a few skills |
| | The LLM may apply the wrong skill when several are loaded |

**Use when:** you have one or two small skills.

---

## 2. Load Skills on Demand (Local `load_skill` Tool)

**Idea:** this is how Claude Code and Agent Skills work.
- The system prompt lists only each skill's `name` and `description`.
- The agent exposes a local tool, `load_skill(name)`.
- When the LLM decides a skill is relevant, it calls `load_skill`, reads the instructions, and then calls the MCP tools as the skill says.

**Where:** Client (Agent) only. `load_skill` is a plain Python function in the agent. It is not an MCP tool. The LLM sees it as just another function tool, but the agent handles the call locally instead of forwarding it to the MCP Server.

### 2a. Read the Skill Catalog

**Location: Client (Agent)**, `src/agent/skills.py`

```python
"""Local skill catalog read from skills/<name>/SKILL.md."""

from pathlib import Path

import yaml

SKILLS_DIR = Path(__file__).parents[2] / "skills"


def read_skill(name: str) -> tuple[dict, str]:
    """Return (frontmatter, body) for a skill."""
    text = (SKILLS_DIR / name / "SKILL.md").read_text(encoding="utf-8")
    _, front, body = text.split("---", 2)
    return yaml.safe_load(front), body.strip()


def list_skills() -> list[dict]:
    """Return the frontmatter of every skill."""
    return [read_skill(p.name)[0] for p in SKILLS_DIR.iterdir() if (p / "SKILL.md").exists()]


def load_skill(name: str) -> str:
    """Return the full instructions of a skill (used as the load_skill tool)."""
    return read_skill(name)[1]
```

### 2b. Advertise the Local Tool and the Catalog to the LLM

**Location: Client (Agent)**, `src/agent/main.py`

```python
LOAD_SKILL_TOOL = {
    "type": "function",
    "function": {
        "name": "load_skill",
        "description": "Load the full instructions of a skill by name before doing that task.",
        "parameters": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
}


def skills_prompt() -> str:
    lines = [f"- {s['name']}: {s['description']}" for s in list_skills()]
    return "Available skills (call load_skill to read one before acting):\n" + "\n".join(lines)


async def main() -> None:
    ...
    messages = [{"role": "system", "content": f"{SYSTEM_PROMPT}\n\n{skills_prompt()}"}]
    async with Client(MCP_URL) as mcp:
        tools = to_openai_tools(await mcp.list_tools()) + [LOAD_SKILL_TOOL]
        ...
```

### 2c. Handle the Local Tool in `ask()`

**Location: Client (Agent)**, `src/agent/main.py`, inside the tool-call loop of `ask()`

```python
for call in message.tool_calls:
    arguments = json.loads(call.function.arguments or "{}")
    if call.function.name == "load_skill":                  # handled locally in the agent
        content = load_skill(**arguments)
    else:                                                   # forwarded to the MCP Server
        result = await mcp.call_tool(call.function.name, arguments, raise_on_error=False)
        content = "\n".join(c.text for c in result.content) or "null"
    messages.append({"role": "tool", "tool_call_id": call.id, "content": content})
```

### Example Turn

```
User:  Get me Freya's contact
LLM:   tool_call load_skill {"name": "member-lookup"}          -> Agent reads SKILL.md locally
LLM:   tool_call get_user_by_name {"name": "Freya"}            -> MCP Server returns null
LLM:   tool_call get_all_users {}                              -> MCP Server returns 10 members
LLM:   "No exact match. Did you mean: Freya Davis - freya.davis@example.com - +1-555-0105"
```

The skill text is stored in the `messages` history, so the LLM keeps following it on later turns without loading it again. It is also written to `context_history.txt`, which shows which skill was used.

| Pros | Cons |
|------|------|
| Scales to many skills (only name + description in context) | One extra LLM round trip to load a skill |
| The LLM picks the skill that fits the request | The LLM may skip loading a skill (mitigate with a clear system prompt) |
| Same model as Claude Code / Agent Skills | |

**Use when:** you expect several skills. **This is the recommended starting point.**

---

## 3. Skill as a Fixed Workflow Run by Code

**Idea:** the skill is a fixed sequence of tool calls.
- The LLM only chooses which workflow to run and fills in its inputs.
- The agent runs the steps itself, without further LLM decisions.

The result is predictable, cheap and easy to unit test.

**Where:** Client (Agent) only. The MCP Server is unchanged.

### 3a. Workflow Definition

**Location: Client (Agent)**, `src/agent/workflows.py`

```python
"""Deterministic skill workflows that call MCP tools in a fixed order."""

import json

from fastmcp import Client


async def member_lookup(mcp: Client, query: str) -> str:
    """Look up a member by email or name, with a fallback to the full list."""
    tool, args = ("get_user_by_email", {"email": query}) if "@" in query \
        else ("get_user_by_name", {"name": query})
    result = await mcp.call_tool(tool, args)
    member = result.structured_content["result"]
    if member:
        return f"{member['name']} - {member['email']} - {member['mobile']}"
    everyone = (await mcp.call_tool("get_all_users")).structured_content["result"]
    matches = [m["name"] for m in everyone if query.lower() in m["name"].lower()]
    return f"Not found. Close matches: {', '.join(matches) or 'none'}"


WORKFLOWS = {"member_lookup": member_lookup}
```

### 3b. Expose Workflows as Tools and Run Them Locally

**Location: Client (Agent)**, `src/agent/main.py`

```python
WORKFLOW_TOOL = {
    "type": "function",
    "function": {
        "name": "member_lookup",
        "description": "Find one member's contact details by name or email.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
}

# inside ask()
if call.function.name in WORKFLOWS:                         # handled locally in the agent
    content = await WORKFLOWS[call.function.name](mcp, **arguments)
else:                                                       # forwarded to the MCP Server
    ...
```

A variant is to send the LLM only the workflow tools and not the raw MCP tools. The LLM then cannot bypass the workflow.

| Pros | Cons |
|------|------|
| Predictable, same tool order every time | Less flexible, new cases need code changes |
| Fewer LLM calls and tokens | Logic lives in code, not in editable text |
| Easy to unit test without an LLM | |

**Use when:** the tool sequence must always be the same, for example in compliance or audit flows.

---

## 4. Skills Provided by the MCP Server (Prompts or Resources)

**Idea:** the server that owns the tools also provides the instructions for using them. Every MCP client (the agent, Claude Code, others) gets the same guidance, and the tools and their instructions are versioned together. MCP has two primitives for this: **prompts** and **resources**.

**Where:**
- The MCP Server defines and serves the skill.
- The Client (Agent) fetches the skill and puts it into the conversation. The server cannot push a skill into the LLM on its own; the client always decides when to use it.

### 4a. Skill as an MCP Prompt

**Location: MCP Server**, `src/member_mcp/server.py`

```python
@mcp.prompt
def member_lookup(query: str) -> str:
    """Find a member's contact details from a full name, partial name or email."""
    return f"""Look up the member for: {query}
1. If it contains "@", call get_user_by_email.
2. Otherwise call get_user_by_name with the full name.
3. If the result is null, call get_all_users and suggest up to 3 closest names.
4. Answer as: Name - email - mobile. Never invent data."""
```

**Location: Client (Agent)**, `src/agent/main.py`: list the server prompts and use one

```python
# At startup: the server's prompts become the skill catalog
prompts = await mcp.list_prompts()
catalog = "\n".join(f"- {p.name}: {p.description}" for p in prompts)

# When a skill is needed, for example from a local load_skill tool (approach 2) or a /command (approach 6)
result = await mcp.get_prompt("member_lookup", {"query": "Freya"})
skill_text = result.messages[0].content.text
messages.append({"role": "user", "content": skill_text})
```

### 4b. Skill as an MCP Resource

**Location: MCP Server**, `src/member_mcp/server.py`

```python
@mcp.resource("skill://member-lookup", mime_type="text/markdown")
def member_lookup_skill() -> str:
    """Instructions for looking up member contact details."""
    return """# Member Lookup
1. If the input contains "@", call get_user_by_email.
2. Otherwise call get_user_by_name.
3. If null, call get_all_users and suggest close names.
4. Answer as: Name - email - mobile."""
```

**Location: Client (Agent)**, `src/agent/main.py`

```python
# Discover skills
skills = [r for r in await mcp.list_resources() if str(r.uri).startswith("skill://")]

# load_skill (approach 2) reads from the MCP Server instead of the local skills/ folder
async def load_skill(mcp: Client, name: str) -> str:
    contents = await mcp.read_resource(f"skill://{name}")
    return contents[0].text
```

### Prompt vs Resource

| | MCP Prompt | MCP Resource |
|---|---|---|
| Takes arguments | Yes (for example `query`) | No (static text, or a URI template) |
| Typical trigger | User-chosen (for example a slash command) | Read by the app or agent when needed |
| Claude Code support | Shown as `/mcp__members__member_lookup` | Referenced with `@members:skill://member-lookup` |

| Pros | Cons |
|------|------|
| One source of truth for tools and their usage | Client still needs code to fetch and apply skills |
| Every MCP client benefits | Skill changes need a server redeploy |
| Skill versions always match the tools | |

**Use when:** several different clients use the server and should behave the same way.

---

## 5. Limit Which Tools a Skill Can Use

**Idea:** when a skill is active, send the LLM only the tools listed in the skill's `allowed-tools`. This cuts wrong tool choices and keeps the LLM on task.

**Where:** Client (Agent) only. It is combined with approach 2 or 4.

**Location: Client (Agent)**, `src/agent/main.py`

```python
def tools_for_skill(all_tools: list[dict], skill_meta: dict) -> list[dict]:
    """Return only the tools the active skill allows (plus load_skill)."""
    allowed = set(skill_meta.get("allowed-tools", [])) | {"load_skill"}
    return [t for t in all_tools if t["function"]["name"] in allowed]

# inside ask(): after load_skill runs, narrow the tool list for the remaining calls
if call.function.name == "load_skill":
    meta, content = read_skill(arguments["name"])
    tools = tools_for_skill(all_tools, meta)
```

Tool filtering happens only in the agent. The MCP Server still exposes all its tools. For real enforcement, for example against misuse, the server would need its own authorization, which is out of scope for the MVP.

| Pros | Cons |
|------|------|
| Fewer wrong tool calls | The active tool set must be tracked in the agent |
| Smaller tool list, fewer tokens | Not a security boundary |

---

## 6. User-Invoked Skills (Slash Commands)

**Idea:** the user chooses the skill directly, for example `/member-lookup Freya`. The LLM does not have to decide which skill applies.

**Where:** Client (Agent). The skill text comes from the local `skills/` folder (approaches 1 and 2) or from the MCP Server (approach 4).

**Location: Client (Agent)**, `src/agent/main.py`, in the console loop of `main()`

```python
prompt = input("> ").strip()
if prompt.startswith("/"):
    name, _, args = prompt[1:].partition(" ")
    skill_text = load_skill(name)                     # or: await mcp.get_prompt(name, {"query": args})
    messages.append({"role": "system", "content": skill_text})
    prompt = args
messages.append({"role": "user", "content": prompt})
print(await ask(llm, mcp, tools, messages))
```

| Pros | Cons |
|------|------|
| Explicit and predictable | The user must know the skill names |
| No extra LLM round trip to choose a skill | |

---

## 7. Claude Code Skill for the Same MCP Server

**Idea:** the Member MCP Server can already be connected to Claude Code (`claude mcp add --transport http members http://127.0.0.1:8000/mcp`). Add a project skill, and Claude Code follows it when calling the `members` MCP tools. No agent code is needed.

**Where:** Claude Code (client side, project folder). The MCP Server is unchanged.

**Location: Claude Code**, `.claude/skills/member-lookup/SKILL.md`

```markdown
---
name: member-lookup
description: Find a member's contact details using the members MCP server. Use when the user asks for a member's email, mobile or contact.
---
# Member Lookup

Use the `members` MCP server tools:

1. If the input contains "@", call mcp__members__get_user_by_email.
2. Otherwise call mcp__members__get_user_by_name with the full name.
3. If the result is null, call mcp__members__get_all_users and suggest up to 3 closest names.
4. Answer as: Name - email - mobile. Never invent member data.
```

- Claude Code loads the skill automatically when the request matches its `description`.
- You can also call it directly with `/member-lookup`.
- MCP tool names in Claude Code have the form `mcp__<server>__<tool>`.

---

## Summary

| # | Approach | Skill defined on | Skill applied on | MCP Server change |
|---|----------|------------------|------------------|-------------------|
| 1 | Skill file as system prompt | Client (Agent) | Client (Agent) | No |
| 2 | Load skills on demand (`load_skill`) | Client (Agent) | Client (Agent) | No |
| 3 | Fixed workflow run by code | Client (Agent) | Client (Agent) | No |
| 4 | MCP prompts / resources | MCP Server | Client (Agent) | Yes |
| 5 | Limit tools per skill | Client (Agent) | Client (Agent) | No |
| 6 | User-invoked slash command | Client or MCP Server | Client (Agent) | Optional |
| 7 | Claude Code skill | Claude Code project | Claude Code | No |

## Recommendation

1. Start with **approach 2** (local `skills/` folder and a `load_skill` tool in the agent). It is a small change to `ask()` and matches how skills work in Claude Code.
2. Add **approach 5** if the LLM keeps choosing the wrong tools.
3. Move the skills to the server with **approach 4** once other clients (for example Claude Code) should share the same guidance. The agent's `load_skill` then reads from `mcp.read_resource` or `mcp.get_prompt` instead of the local folder.
4. Use **approach 3** only for flows that must always run in the same order.
