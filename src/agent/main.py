"""Console agent that answers member questions via an OpenRouter LLM and the Member MCP server."""

import json
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from fastmcp import Client
from mcp.types import Tool
from openai import AsyncOpenAI

OPENROUTER_URL = "https://openrouter.ai/api/v1"
MODEL = "openai/gpt-oss-120b"
MCP_URL = "http://127.0.0.1:8000/mcp"
HISTORY_FILE = Path(__file__).parents[2] / "context_history.txt"
SYSTEM_PROMPT = "You answer questions about members. Use the provided tools to look up member data."


def to_openai_tools(tools: list[Tool]) -> list[dict]:
    """Convert MCP tool definitions to OpenAI function tools."""
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description or "",
                "parameters": t.input_schema,
            },
        }
        for t in tools
    ]


async def ask(llm: AsyncOpenAI, mcp: Client, tools: list[dict], messages: list[dict]) -> str:
    """Run the LLM/tool loop until the LLM answers without tool calls.

    Every assistant and tool message is appended to messages.
    """
    while True:
        response = await llm.chat.completions.create(model=MODEL, messages=messages, tools=tools)
        message = response.choices[0].message
        messages.append(message.model_dump(exclude_none=True))
        if not message.tool_calls:
            return message.content or ""
        for call in message.tool_calls:
            print(f"[tool] {call.function.name} {call.function.arguments}")
            arguments = json.loads(call.function.arguments or "{}")
            result = await mcp.call_tool(call.function.name, arguments, raise_on_error=False)
            content = "\n".join(c.text for c in result.content) or "null"
            messages.append({"role": "tool", "tool_call_id": call.id, "content": content})


def append_history(path: Path, messages: list[dict]) -> None:
    """Append messages to the history file, one JSON object per line."""
    with path.open("a", encoding="utf-8") as f:
        for message in messages:
            f.write(json.dumps(message) + "\n")


async def main() -> None:
    """Read prompts from the console and print the agent's answers."""
    load_dotenv()
    llm = AsyncOpenAI(base_url=OPENROUTER_URL, api_key=os.environ["OPENROUTER_API_KEY"])
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    with HISTORY_FILE.open("a", encoding="utf-8") as f:
        f.write(f"=== Session {datetime.now().isoformat(timespec='seconds')} ===\n")
    append_history(HISTORY_FILE, messages)

    async with Client(MCP_URL) as mcp:
        tools = to_openai_tools(await mcp.list_tools())
        print("Member agent. Type 'exit' to quit.")
        while True:
            try:
                prompt = input("> ").strip()
            except EOFError:
                break
            if prompt.lower() in ("exit", "quit"):
                break
            if not prompt:
                continue
            start = len(messages)
            messages.append({"role": "user", "content": prompt})
            print(await ask(llm, mcp, tools, messages))
            append_history(HISTORY_FILE, messages[start:])
