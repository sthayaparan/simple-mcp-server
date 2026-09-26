"""Tests for the FastAPI app, including MCP over Streamable HTTP against a live server."""
# pylint: disable=missing-function-docstring,redefined-outer-name

import socket
import threading
import time

import pytest
import uvicorn
from fastapi.testclient import TestClient
from fastmcp import Client

from member_mcp.main import app


def test_health():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.fixture(scope="module")
def server_url():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}/mcp"
    server.should_exit = True
    thread.join()


async def test_mcp_over_streamable_http(server_url):
    async with Client(server_url) as client:
        tools = await client.list_tools()
        result = await client.call_tool("get_all_users")
    assert {t.name for t in tools} == {"get_all_users", "get_user_by_name", "get_user_by_email"}
    assert len(result.structured_content["result"]) == 10
