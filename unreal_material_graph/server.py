"""Domain-scoped FastMCP entry point for material graph tools."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict

from fastmcp import FastMCP

from .tools import (
    analyze_material_graph,
    connect_material_nodes,
    create_material_graph_recipe,
    get_material_graph_harness_info,
)


@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    yield {}


mcp = FastMCP("UnrealMaterialGraphHarness", lifespan=server_lifespan)

for tool in [
    get_material_graph_harness_info,
    analyze_material_graph,
    create_material_graph_recipe,
    connect_material_nodes,
]:
    mcp.tool()(tool)


if __name__ == "__main__":
    mcp.run()
