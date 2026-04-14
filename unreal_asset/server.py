"""Domain-scoped FastMCP entry point for asset tools."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict

from fastmcp import FastMCP

from .tools import (
    create_asset_with_properties,
    duplicate_asset_with_overrides,
    ensure_asset_with_properties,
    ensure_folder,
    get_asset_properties,
    get_asset_harness_info,
    import_fbx_asset,
    import_texture_asset,
    inspect_cascade_emitter,
    inspect_particle_system,
    move_asset_batch,
    query_assets_summary,
    query_textures,
    set_asset_properties,
    set_texture_compression_settings,
    set_texture_srgb,
    update_texture_group_config,
    update_asset_properties_batch,
    update_asset_properties,
)


@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    yield {}


mcp = FastMCP("UnrealAssetHarness", lifespan=server_lifespan)

for tool in [
    get_asset_harness_info,
    query_assets_summary,
    query_textures,
    get_asset_properties,
    ensure_folder,
    ensure_asset_with_properties,
    duplicate_asset_with_overrides,
    move_asset_batch,
    set_asset_properties,
    create_asset_with_properties,
    update_texture_group_config,
    update_asset_properties_batch,
    update_asset_properties,
    set_texture_compression_settings,
    set_texture_srgb,
    inspect_particle_system,
    inspect_cascade_emitter,
    import_texture_asset,
    import_fbx_asset,
]:
    mcp.tool()(tool)


if __name__ == "__main__":
    mcp.run()
