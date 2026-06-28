"""Domain-scoped FastMCP entry point for blueprint tools."""

from __future__ import annotations

from unreal_harness_runtime.editor_guard import make_guarded_tool

from .tools import (
    add_blueprint_node,
    add_point_light_component_node,
    analyze_blueprint_graph,
    connect_blueprint_nodes,
    find_blueprint_nodes,
    get_blueprint_components,
    get_blueprint_function_details,
    get_blueprint_harness_info,
    get_blueprint_variable_details,
    read_blueprint_content,
    set_blueprint_node_property,
)

TOOLS = [
    get_blueprint_harness_info,
    make_guarded_tool("blueprint.get_blueprint_components", get_blueprint_components),
    make_guarded_tool("blueprint.read_blueprint_content", read_blueprint_content),
    make_guarded_tool("blueprint.analyze_blueprint_graph", analyze_blueprint_graph),
    make_guarded_tool("blueprint.find_blueprint_nodes", find_blueprint_nodes),
    make_guarded_tool("blueprint.get_blueprint_variable_details", get_blueprint_variable_details),
    make_guarded_tool("blueprint.get_blueprint_function_details", get_blueprint_function_details),
    make_guarded_tool("blueprint.add_blueprint_node", add_blueprint_node),
    make_guarded_tool("blueprint.connect_blueprint_nodes", connect_blueprint_nodes),
    make_guarded_tool("blueprint.set_blueprint_node_property", set_blueprint_node_property),
    make_guarded_tool("blueprint.add_point_light_component_node", add_point_light_component_node),
]

if __name__ == "__main__":
    from contextlib import asynccontextmanager
    from typing import Any, AsyncIterator, Dict
    from fastmcp import FastMCP

    @asynccontextmanager
    async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
        yield {}

    mcp = FastMCP("UnrealBlueprintHarness", lifespan=server_lifespan)
    for tool in TOOLS:
        mcp.tool()(tool)
    mcp.run()
