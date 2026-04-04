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
    get_asset_harness_info,
    import_fbx_asset,
    import_texture_asset,
    move_asset_batch,
    query_assets_summary,
    update_asset_properties,
)


@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    yield {}


mcp = FastMCP("UnrealAssetHarness", lifespan=server_lifespan)

for tool in [
    get_asset_harness_info,
    query_assets_summary,
    ensure_folder,
    ensure_asset_with_properties,
    duplicate_asset_with_overrides,
    move_asset_batch,
    create_asset_with_properties,
    update_asset_properties,
    import_texture_asset,
    import_fbx_asset,
]:
    mcp.tool()(tool)


if __name__ == "__main__":
    mcp.run()
