"""Tests for the MCP tools via the in-memory FastMCP client."""
# pylint: disable=missing-function-docstring,redefined-outer-name

import pytest
from fastmcp import Client

from member_mcp.data import MEMBERS
from member_mcp.server import mcp


@pytest.fixture
async def client():
    async with Client(mcp) as c:
        yield c


async def test_lists_expected_tools(client):
    tools = await client.list_tools()
    assert {t.name for t in tools} == {"get_all_users", "get_user_by_name", "get_user_by_email"}


async def test_get_all_users(client):
    result = await client.call_tool("get_all_users")
    assert result.structured_content["result"] == [m.model_dump() for m in MEMBERS]


@pytest.mark.parametrize("name", ["Fiona Johnson", "fiona johnson", "FIONA JOHNSON"])
async def test_get_user_by_name_found(client, name):
    result = await client.call_tool("get_user_by_name", {"name": name})
    assert result.structured_content["result"] == MEMBERS[0].model_dump()


async def test_get_user_by_name_not_found(client):
    result = await client.call_tool("get_user_by_name", {"name": "Nobody"})
    assert result.structured_content["result"] is None


@pytest.mark.parametrize("email", ["felix.smith@example.com", "FELIX.Smith@Example.com"])
async def test_get_user_by_email_found(client, email):
    result = await client.call_tool("get_user_by_email", {"email": email})
    assert result.structured_content["result"] == MEMBERS[1].model_dump()


async def test_get_user_by_email_not_found(client):
    result = await client.call_tool("get_user_by_email", {"email": "nobody@example.com"})
    assert result.structured_content["result"] is None
