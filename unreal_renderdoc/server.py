"""Domain-scoped FastMCP entry point for UE-side RenderDoc tools."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict

from fastmcp import FastMCP

from .tools import (
    capture_current_selection,
    capture_current_viewport_issue,
    capture_renderdoc_diff_pair,
    get_renderdoc_capture_context,
    get_renderdoc_harness_info,
    get_renderdoc_runtime_status,
    get_renderdoc_selection_context,
    map_material_to_renderdoc_context,
    normalize_renderdoc_debug_labels,
    reverse_lookup_renderdoc_symbols,
    request_renderdoc_capture,
    set_renderdoc_debug_workflow,
)


@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    yield {}


mcp = FastMCP("UnrealRenderDocHarness", lifespan=server_lifespan)

for tool in [
    get_renderdoc_harness_info,
    get_renderdoc_runtime_status,
    get_renderdoc_capture_context,
    get_renderdoc_selection_context,
    map_material_to_renderdoc_context,
    normalize_renderdoc_debug_labels,
    reverse_lookup_renderdoc_symbols,
    set_renderdoc_debug_workflow,
    request_renderdoc_capture,
    capture_current_selection,
    capture_current_viewport_issue,
    capture_renderdoc_diff_pair,
]:
    mcp.tool()(tool)


if __name__ == "__main__":
    mcp.run()
