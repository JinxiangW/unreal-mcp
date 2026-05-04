"""Domain-scoped FastMCP entry point for material tools."""

from __future__ import annotations

from unreal_harness_runtime.editor_guard import make_guarded_tool

from .tools import (
    create_material_asset,
    create_material_function_asset,
    create_material_instance_asset,
    get_material_harness_info,
    get_material_instance_parameter_names,
    set_material_instance_scalar_parameter,
    set_material_instance_texture_parameter,
    set_material_instance_vector_parameter,
    update_material_instance_parameters_and_verify,
    update_material_instance_properties,
)

TOOLS = [
    get_material_harness_info,
    make_guarded_tool("material.create_material_asset", create_material_asset),
    make_guarded_tool("material.create_material_function_asset", create_material_function_asset),
    make_guarded_tool("material.create_material_instance_asset", create_material_instance_asset),
    make_guarded_tool("material.update_material_instance_properties", update_material_instance_properties),
    make_guarded_tool("material.update_material_instance_parameters_and_verify", update_material_instance_parameters_and_verify),
    make_guarded_tool("material.get_material_instance_parameter_names", get_material_instance_parameter_names),
    make_guarded_tool("material.set_material_instance_scalar_parameter", set_material_instance_scalar_parameter),
    make_guarded_tool("material.set_material_instance_vector_parameter", set_material_instance_vector_parameter),
    make_guarded_tool("material.set_material_instance_texture_parameter", set_material_instance_texture_parameter),
]

if __name__ == "__main__":
    from contextlib import asynccontextmanager
    from typing import Any, AsyncIterator, Dict
    from fastmcp import FastMCP

    @asynccontextmanager
    async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
        yield {}

    mcp = FastMCP("UnrealMaterialHarness", lifespan=server_lifespan)
    for tool in TOOLS:
        mcp.tool()(tool)
    mcp.run()
