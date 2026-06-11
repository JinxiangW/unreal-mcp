"""Domain-scoped FastMCP entry point for material graph tools."""

from __future__ import annotations

from unreal_harness_runtime.editor_guard import make_guarded_tool

from .tools import (
    analyze_material_graph,
    connect_material_nodes,
    create_material_graph_recipe,
    get_material_graph,
    get_material_graph_harness_info,
    patch_material_graph,
    set_material_graph_property_connections,
)

TOOLS = [
    get_material_graph_harness_info,
    get_material_graph,
    make_guarded_tool("material_graph.analyze_material_graph", analyze_material_graph),
    make_guarded_tool("material_graph.create_material_graph_recipe", create_material_graph_recipe),
    make_guarded_tool("material_graph.connect_material_nodes", connect_material_nodes),
    make_guarded_tool("material_graph.set_material_graph_property_connections", set_material_graph_property_connections),
    make_guarded_tool("material_graph.patch_material_graph", patch_material_graph),
]

if __name__ == "__main__":
    from contextlib import asynccontextmanager
    from typing import Any, AsyncIterator, Dict
    from fastmcp import FastMCP

    @asynccontextmanager
    async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
        yield {}

    mcp = FastMCP("UnrealMaterialGraphHarness", lifespan=server_lifespan)
    for tool in TOOLS:
        mcp.tool()(tool)
    mcp.run()
