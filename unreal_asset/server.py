"""Domain-scoped FastMCP entry point for asset tools."""

from __future__ import annotations

from unreal_harness_runtime.editor_guard import make_guarded_tool

from .tools import (
    create_asset_with_properties,
    duplicate_asset_with_overrides,
    ensure_asset_with_properties,
    ensure_folder,
    find_asset,
    get_asset_properties,
    get_asset_harness_info,
    get_object_properties,
    import_fbx_asset,
    import_texture_asset,
    inspect_cascade_emitter,
    inspect_particle_system,
    load_asset,
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

TOOLS = [
    get_asset_harness_info,
    # Filesystem / commandlet tools — no editor guard needed
    update_texture_group_config,
    import_texture_asset,
    import_fbx_asset,
    # Live-editor tools with guard
    make_guarded_tool("asset.find_asset", find_asset),
    make_guarded_tool("asset.load_asset", load_asset),
    make_guarded_tool("asset.query_assets_summary", query_assets_summary),
    make_guarded_tool("asset.query_textures", query_textures),
    make_guarded_tool("asset.get_asset_properties", get_asset_properties),
    make_guarded_tool("asset.get_object_properties", get_object_properties),
    make_guarded_tool("asset.set_asset_properties", set_asset_properties),
    make_guarded_tool("asset.ensure_folder", ensure_folder),
    make_guarded_tool("asset.ensure_asset_with_properties", ensure_asset_with_properties),
    make_guarded_tool("asset.duplicate_asset_with_overrides", duplicate_asset_with_overrides),
    make_guarded_tool("asset.move_asset_batch", move_asset_batch),
    make_guarded_tool("asset.create_asset_with_properties", create_asset_with_properties),
    make_guarded_tool("asset.update_asset_properties", update_asset_properties),
    make_guarded_tool("asset.update_asset_properties_batch", update_asset_properties_batch),
    make_guarded_tool("asset.set_texture_compression_settings", set_texture_compression_settings),
    make_guarded_tool("asset.set_texture_srgb", set_texture_srgb),
    make_guarded_tool("asset.inspect_particle_system", inspect_particle_system),
    make_guarded_tool("asset.inspect_cascade_emitter", inspect_cascade_emitter),
]

if __name__ == "__main__":
    from contextlib import asynccontextmanager
    from typing import Any, AsyncIterator, Dict
    from fastmcp import FastMCP

    @asynccontextmanager
    async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
        yield {}

    mcp = FastMCP("UnrealAssetHarness", lifespan=server_lifespan)
    for tool in TOOLS:
        mcp.tool()(tool)
    mcp.run()
