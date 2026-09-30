# Converting FastAPI REST APIs to MCP Tools

You do not need to rewrite existing APIs. FastMCP (v4.0.10 in this project) can generate MCP tools from an existing FastAPI app using its OpenAPI schema. There are three approaches, from least to most effort.

## Option 1: Auto-convert the whole FastAPI app (fastest)

```python
from fastapi import FastAPI
from fastmcp import FastMCP

app = FastAPI(title="Orders API")

@app.get("/orders/{order_id}", operation_id="get_order")
def get_order(order_id: int) -> dict:
    """Return a single order by id."""
    ...

# Every route becomes an MCP tool
mcp = FastMCP.from_fastapi(app=app)
mcp_app = mcp.http_app(path="/mcp")

# Serve REST and MCP side by side from one process
api = FastAPI(lifespan=mcp_app.lifespan)
api.mount("/api", app)      # existing REST clients keep working
api.mount("/", mcp_app)     # agents use http://host:8000/mcp
```

- Each route turns into a tool. The tool name comes from the `operation_id`, the description from the docstring or `summary`, and the input schema from your Pydantic models and parameters.
- The generated tools call the FastAPI app in-process, so there is no extra network hop and existing validation and business logic still apply.
- If the app already has its own `lifespan`, merge the two with `fastmcp.utilities.lifespan.combine_lifespans(app_lifespan, mcp_app.lifespan)`.

## Option 2: Auto-convert, but choose what is exposed (recommended)

Exposing every endpoint is usually a bad idea. Too many tools confuse the LLM, and agents should not call delete or admin routes. Use `RouteMap` to filter:

```python
from fastmcp import FastMCP
from fastmcp.server.providers.openapi import MCPType, RouteMap

mcp = FastMCP.from_fastapi(
    app=app,
    name="Orders MCP",
    route_maps=[
        RouteMap(pattern=r"^/admin/.*", mcp_type=MCPType.EXCLUDE),
        RouteMap(methods=["DELETE"], mcp_type=MCPType.EXCLUDE),
        RouteMap(tags={"internal"}, mcp_type=MCPType.EXCLUDE),
        RouteMap(mcp_type=MCPType.TOOL),  # everything else becomes a tool
    ],
    mcp_names={"get_order_orders__order_id__get": "get_order"},  # rename ugly auto ids
)
```

The first matching rule wins. You can also match on FastAPI `tags`. Tagging routes in FastAPI (e.g. `tags=["mcp"]`) is a clean way to opt endpoints in.

## Option 3: Write MCP tools by hand (best quality)

For the endpoints agents use most, write explicit tools like the ones in `src/member_mcp/server.py`. Call the existing service or business functions directly, not the HTTP routes:

```python
@mcp.tool
def find_orders_for_customer(email: str) -> list[Order]:
    """Return all orders placed by the customer with this email."""
    return order_service.find_by_email(email)
```

REST APIs are designed for programs. Agents do better with fewer, task-shaped tools, e.g. one `find_orders_for_customer` tool instead of `get_customer` followed by `list_orders?customer_id=`.

**A common path is to start with Option 2 to get coverage quickly, then replace the most-used tools with hand-written ones (Option 3).** Both can be mixed on the same server.

## If the REST APIs are separate services

If the APIs run as separate deployed services, wrap them from their OpenAPI spec and call them over HTTP:

```python
import httpx2
from fastmcp import FastMCP

spec = httpx2.get("https://orders.internal/openapi.json").json()
mcp = FastMCP.from_openapi(
    openapi_spec=spec,
    client=httpx2.AsyncClient(base_url="https://orders.internal"),
)
```

## Tips for good results

1. **Set `operation_id` on every route.** Otherwise tool names come out like `get_order_orders__order_id__get`.
2. **Write docstrings for the LLM.** The description is how the model decides which tool to call. Say what the tool does and when to use it.
3. **Use typed Pydantic request and response models.** They become precise JSON schemas for the tool.
4. **Keep the tool count small.** Aim for a focused set per server. Split large APIs into several MCP servers by domain.
5. **Plan for auth.** REST auth (API keys, JWT) does not automatically carry over. Configure it on the MCP server, which supports bearer and OAuth. For in-process calls, forward headers with `httpx_client_kwargs`.
6. **Test with a real agent.** Point Claude Code (`claude mcp add --transport http ...`) or the `agent/` console at the server and check that the model picks the right tools.
