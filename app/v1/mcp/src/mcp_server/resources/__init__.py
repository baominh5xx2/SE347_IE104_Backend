"""Resources package - Register all MCP resources"""
from fastmcp import FastMCP
from .falkordb import register_falkordb_resources


def register_all_resources(mcp: FastMCP):
    """
    Register all MCP resources
    
    Args:
        mcp: FastMCP server instance
    """
    register_falkordb_resources(mcp)

__all__ = ["register_all_resources", "register_falkordb_resources"]

