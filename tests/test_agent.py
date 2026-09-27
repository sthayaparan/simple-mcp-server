"""Tests for the console agent with a scripted fake LLM and the in-memory MCP client."""
# pylint: disable=missing-function-docstring,redefined-outer-name,too-few-public-methods

import copy
import json
from types import SimpleNamespace

import pytest
from fastmcp import Client
from openai.types.chat import ChatCompletion

from agent.main import append_history, ask, to_openai_tools
from member_mcp.data import MEMBERS
from member_mcp.server import mcp


class FakeLLM:
    """Stands in for AsyncOpenAI: returns scripted replies and records the messages it was sent."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    async def create(self, **kwargs):
        self.calls.append(copy.deepcopy(kwargs["messages"]))
        return self.replies.pop(0)


def reply(content=None, tool_calls=()):
    calls = [
        {
            "id": f"call_{i}",
            "type": "function",
            "function": {"name": name, "arguments": json.dumps(args)},
        }
        for i, (name, args) in enumerate(tool_calls)
    ]
    message = {"role": "assistant", "content": content, "tool_calls": calls or None}
    return ChatCompletion.model_validate({
        "id": "x", "object": "chat.completion", "created": 0, "model": "m",
        "choices": [{"index": 0, "finish_reason": "stop", "message": message}],
    })


@pytest.fixture
async def client():
    async with Client(mcp) as c:
        yield c


@pytest.fixture
async def tools(client):
    return to_openai_tools(await client.list_tools())


def user(prompt):
    return [{"role": "user", "content": prompt}]


async def test_to_openai_tools(tools):
    by_name = {t["function"]["name"]: t for t in tools}
    assert set(by_name) == {"get_all_users", "get_user_by_name", "get_user_by_email"}
    assert all(t["type"] == "function" and t["function"]["description"] for t in tools)
    params = by_name["get_user_by_email"]["function"]["parameters"]
    assert params["properties"]["email"]["type"] == "string"
    assert params["required"] == ["email"]


async def test_direct_answer_makes_no_tool_calls(client, tools):
    llm = FakeLLM([reply("Hello")])
    messages = user("Hi")
    assert await ask(llm, client, tools, messages) == "Hello"
    assert len(llm.calls) == 1
    assert [m["role"] for m in messages] == ["user", "assistant"]


async def test_tool_call_result_sent_back(client, tools):
    llm = FakeLLM([
        reply(tool_calls=[("get_user_by_email", {"email": "felix.smith@example.com"})]),
        reply("Felix Smith"),
    ])
    messages = user("Who owns felix.smith@example.com?")
    assert await ask(llm, client, tools, messages) == "Felix Smith"
    tool_message = llm.calls[1][-1]
    assert tool_message["role"] == "tool"
    assert json.loads(tool_message["content"]) == MEMBERS[1].model_dump()


async def test_unknown_member_returns_null(client, tools):
    llm = FakeLLM([
        reply(tool_calls=[("get_user_by_name", {"name": "Nobody"})]),
        reply("Not found"),
    ])
    messages = user("Find Nobody")
    await ask(llm, client, tools, messages)
    assert messages[-2]["content"] == "null"


async def test_multiple_and_consecutive_tool_calls(client, tools):
    llm = FakeLLM([
        reply(tool_calls=[("get_user_by_name", {"name": "Fiona Johnson"}), ("get_all_users", {})]),
        reply(tool_calls=[("get_user_by_email", {"email": "finn.brown@example.com"})]),
        reply("Done"),
    ])
    messages = user("Many lookups")
    assert await ask(llm, client, tools, messages) == "Done"
    assert len(llm.calls) == 3
    tool_results = [json.loads(m["content"]) for m in messages if m["role"] == "tool"]
    assert tool_results == [
        MEMBERS[0].model_dump(),
        [m.model_dump() for m in MEMBERS],
        MEMBERS[3].model_dump(),
    ]


async def test_history_order_and_tool_call_ids(client, tools):
    llm = FakeLLM([
        reply(tool_calls=[("get_user_by_name", {"name": "Finn Brown"})]),
        reply("Found"),
    ])
    messages = user("Find Finn Brown")
    await ask(llm, client, tools, messages)
    assert [m["role"] for m in messages] == ["user", "assistant", "tool", "assistant"]
    assert messages[2]["tool_call_id"] == messages[1]["tool_calls"][0]["id"]
    assert messages[3]["content"] == "Found"


async def test_second_prompt_sends_full_history(client, tools):
    llm = FakeLLM([
        reply(tool_calls=[("get_user_by_name", {"name": "Finn Brown"})]),
        reply("finn.brown@example.com"),
        reply("+1-555-0104"),
    ])
    messages = user("Email of Finn Brown?")
    await ask(llm, client, tools, messages)
    first_turn = copy.deepcopy(messages)
    messages.append({"role": "user", "content": "And their mobile?"})
    assert await ask(llm, client, tools, messages) == "+1-555-0104"
    assert llm.calls[2] == first_turn + [{"role": "user", "content": "And their mobile?"}]


def test_append_history(tmp_path):
    path = tmp_path / "context_history.txt"
    append_history(path, [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}])
    append_history(path, [{"role": "user", "content": "c"}])
    lines = path.read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["content"] for line in lines] == ["a", "b", "c"]
