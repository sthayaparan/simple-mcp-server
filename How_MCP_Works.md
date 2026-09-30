# How MCP Works: Local vs Remote Servers

When you add an MCP server to Claude, whether it runs locally or remotely depends on the **transport** you choose.

| Transport | Where it runs | How Claude connects | Example |
|---|---|---|---|
| `stdio` | Always local. Claude Code starts it as a child process on your machine. | stdin/stdout pipes | `claude mcp add myserver -- uv run server.py` |
| `http` (Streamable HTTP) | Local or remote. It is just a URL. | HTTP requests to the endpoint | `claude mcp add --transport http member-mcp http://127.0.0.1:8000/mcp` |
| `sse` (legacy) | Local or remote | HTTP + Server-Sent Events | Older servers; prefer `http` for new ones |

## This project

- The member-mcp server uses Streamable HTTP and is bound to `127.0.0.1:8000`, so it runs locally. You start it with the start script in `scripts/`, and Claude Code only connects to the URL. Claude Code does not start or manage it.
- If the same app were deployed to a cloud host, you would register it with a URL like `https://your-host/mcp` and it would run remotely. Nothing changes on the Claude side.

## Other points

- **stdio servers:** Claude Code manages the lifecycle. It starts the server when a session begins and stops it when the session ends.
- **HTTP servers:** you manage the lifecycle. The server must already be running when Claude connects.
- **Connectors added on claude.ai** are remote servers. They are reached through Anthropic's infrastructure, so they cannot reach `localhost` on your machine. A local server like this one only works with local clients such as the Claude Code CLI, the Claude desktop app, or the `agent/` console.
- **Scope** (`--scope local|project|user`) only controls where the configuration is saved: just you, the shared `.mcp.json`, or all your projects. It does not affect where the server runs.

## Why claude.ai connectors cannot reach localhost

The key question is **which computer opens the network connection to the MCP server**. `localhost` / `127.0.0.1` always means "this same machine", so the answer depends on where the connecting client runs.

### Case 1: Claude Code CLI or the `agent/` console (local client)

```
Your PC
+------------------------------------------------+
|  Claude Code CLI  --HTTP-->  127.0.0.1:8000/mcp |
|  (or agent/)                 (member-mcp)       |
+------------------------------------------------+
         |
         | model API calls only (prompts, tool results)
         v
   Anthropic / OpenRouter cloud
```

- The client process runs on your PC, and it makes the HTTP call to `127.0.0.1:8000`. That address points to your own machine, so the call succeeds.
- The LLM never talks to the MCP server directly. The model decides which tool to call, the local client executes the call, and then it sends the result back to the model. The `agent/` console follows this pattern with OpenRouter.

### Case 2: A connector added on claude.ai (remote client)

```
Anthropic cloud                                  Your PC
+-------------------------------+               +---------------------+
| claude.ai connector service   |               | member-mcp          |
|  --HTTP--> 127.0.0.1:8000     |      X        | 127.0.0.1:8000      |
|  (resolves to Anthropic's own |  cannot reach | (not on the         |
|   server, not your PC)        |               |  internet)          |
+-------------------------------+               +---------------------+
```

- When you add a custom connector at claude.ai (Settings > Connectors), you only give it a URL. Anthropic's servers make the HTTP requests to that URL, not your browser or PC.
- If the URL is `http://127.0.0.1:8000/mcp`, it resolves to Anthropic's own machine, and the server is not running there, so the connection fails.
- A LAN IP (e.g. `192.168.x.x`) does not work either. It is private, and the router or firewall blocks inbound traffic from the internet.
- A claude.ai connector therefore needs a **public HTTPS URL** that anyone on the internet can reach.

### Connectors synced into Claude Code

Connectors configured on your claude.ai account are synced into Claude Code sessions. Their tools appear with a `claude_ai` prefix, e.g. `mcp__claude_ai_Claude_Docs__*`. The calls are routed through Anthropic's infrastructure to the connector's server, which must be a public remote service. They also cannot be pointed at anything on your localhost.

### The Claude desktop app

- Servers configured in the desktop app's local config (`claude_desktop_config.json`) run locally as stdio processes, so they can reach localhost.
- Connectors added through the desktop app's Connectors UI behave like claude.ai connectors: remote, reached from the cloud.
- To point the desktop app at a local HTTP server like member-mcp, use a stdio bridge in the local config, e.g. `npx mcp-remote http://127.0.0.1:8000/mcp`.

### Making member-mcp usable from claude.ai

1. **Deploy it** to a cloud host with HTTPS, e.g. `https://member-mcp.example.com/mcp`, or
2. **Tunnel it** from your PC with `cloudflared tunnel` or `ngrok http 8000`, which gives a temporary public HTTPS URL.

Either way, the server becomes reachable by anyone who has the URL. The MVP has no authentication, so all member names, emails and mobile numbers would be exposed. Add auth first (FastMCP supports bearer tokens / OAuth).

| Client | Who connects to the MCP server | Can use `127.0.0.1:8000`? |
|---|---|---|
| Claude Code CLI (`claude mcp add ...`) | Your PC | Yes |
| `agent/` console | Your PC | Yes |
| Desktop app, local config (stdio / `mcp-remote` bridge) | Your PC | Yes |
| claude.ai / desktop Connectors UI | Anthropic's cloud | No, needs a public HTTPS URL |

## What is claude.ai

[claude.ai](https://claude.ai) is Anthropic's website for using Claude in a web browser. You sign in with your Anthropic account.

- It is a chat interface to Claude, the same model family that powers Claude Code.
- It includes projects, file uploads, artifacts (web pages Claude builds), and **Connectors**, which are MCP servers that give Claude extra tools such as Google Drive, GitHub or Slack.
- claude.ai runs in Anthropic's cloud. The browser only displays the conversation. When Claude calls a connector's tool, the request comes from Anthropic's servers, not your PC.
- Claude Code is a program running on your PC, so it can reach local servers like member-mcp.
- Both use the same account, which is why claude.ai connectors can appear in Claude Code sessions.

| Product | Runs where | Can reach a localhost MCP server? |
|---|---|---|
| claude.ai (web) | Browser + Anthropic cloud | No |
| Claude desktop app | Your PC (Windows/Mac) | Only via local config (stdio) |
| Claude mobile app | Phone + Anthropic cloud | No |
| Claude Code CLI | Your PC terminal | Yes |
| Claude API | Your own code calls Anthropic's API | Yes, if your code calls the MCP server itself (like the `agent/` console) |
