"""Explicit internal/raw FastMCP entry point for editor-content tools."""

from .server import mcp


if __name__ == "__main__":
    mcp.run()
