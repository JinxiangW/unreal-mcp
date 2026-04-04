"""Domain-scoped FastMCP entry point for material tools."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict

from fastmcp import FastMCP

from .tools import (
    create_material_asset,
    create_material_instance_asset,
    get_material_harness_info,
    get_material_instance_parameter_names,
    set_material_instance_scalar_parameter,
    set_material_instance_texture_parameter,
    set_material_instance_vector_parameter,
    update_material_instance_parameters_and_verify,
    update_material_instance_properties,
)


@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    yield {}


mcp = FastMCP("UnrealMaterialHarness", lifespan=server_lifespan)

for tool in [
    get_material_harness_info,
    create_material_asset,
    create_material_instance_asset,
    update_material_instance_properties,
    update_material_instance_parameters_and_verify,
    get_material_instance_parameter_names,
    set_material_instance_scalar_parameter,
    set_material_instance_vector_parameter,
    set_material_instance_texture_parameter,
]:
    mcp.tool()(tool)


if __name__ == "__main__":
    mcp.run()
