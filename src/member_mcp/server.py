"""FastMCP server exposing member lookup tools."""

from fastmcp import FastMCP

from member_mcp.data import MEMBERS, Member

mcp = FastMCP("Member MCP Server")


@mcp.tool
def get_all_users() -> list[Member]:
    """Return all members."""
    return MEMBERS


@mcp.tool
def get_user_by_name(name: str) -> Member | None:
    """Return the member with the given full name (case-insensitive), or null if not found."""
    return next((m for m in MEMBERS if m.name.lower() == name.lower()), None)


@mcp.tool
def get_user_by_email(email: str) -> Member | None:
    """Return the member with the given email (case-insensitive), or null if not found."""
    return next((m for m in MEMBERS if m.email.lower() == email.lower()), None)
