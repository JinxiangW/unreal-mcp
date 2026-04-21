"""Domain-scoped FastMCP entry point for blueprint tools."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict

from fastmcp import FastMCP

from .tools import (
    add_blueprint_node,
    add_point_light_component_node,
    analyze_blueprint_graph,
    connect_blueprint_nodes,
    find_blueprint_nodes,
    get_blueprint_function_details,
    get_blueprint_harness_info,
    get_blueprint_variable_details,
    read_blueprint_content,
    set_blueprint_node_property,
)


@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    yield {}


mcp = FastMCP("UnrealBlueprintHarness", lifespan=server_lifespan)

for tool in [
    get_blueprint_harness_info,
    read_blueprint_content,
    analyze_blueprint_graph,
    find_blueprint_nodes,
    get_blueprint_variable_details,
    get_blueprint_function_details,
    add_blueprint_node,
    connect_blueprint_nodes,
    set_blueprint_node_property,
    add_point_light_component_node,
]:
    mcp.tool()(tool)


if __name__ == "__main__":
    mcp.run()
