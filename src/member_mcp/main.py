"""FastAPI application serving the MCP server over Streamable HTTP at /mcp."""

from fastapi import FastAPI

from member_mcp.server import mcp

mcp_app = mcp.http_app(path="/mcp")

app = FastAPI(title="Member MCP Server", lifespan=mcp_app.lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness check."""
    return {"status": "ok"}


app.mount("/", mcp_app)
