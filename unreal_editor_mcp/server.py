"""
Unreal Editor MCP server entry point.

This server exposes stable editor-content workflows on top of the existing
Unreal TCP plugin backend.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict

from fastmcp import FastMCP
from unreal_diagnostics.tools import get_token_usage_summary


_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

from .connection import reset_unreal_connection
from .tools import (
    analyze_blueprint_graph,
    batch_create_assets,
    batch_delete_actors,
    batch_set_actors_properties,
    batch_set_assets_properties,
    batch_spawn_actors,
    blueprint_graph_command,
    build_material_graph,
    create_asset,
    create_level,
    delete_actor,
    delete_asset,
    get_actor_properties,
    get_actors,
    get_asset_properties,
    get_assets,
    get_blueprint_info,
    get_current_level,
    get_material_graph,
    get_niagara_compiled_code,
    get_niagara_emitter,
    get_niagara_graph,
    get_niagara_particle_attributes,
    get_viewport_camera,
    get_viewport_screenshot,
    import_fbx,
    import_texture,
    load_level,
    read_blueprint_content,
    read_result_handle,
    release_result_handle,
    save_current_level,
    set_actor_properties,
    set_asset_properties,
    set_viewport_camera,
    spawn_actor,
    update_blueprint,
    update_niagara_emitter,
    update_niagara_graph,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(_CURRENT_DIR, "unreal_editor_mcp.log")),
    ],
)
logger = logging.getLogger("UnrealEditorMCP")


@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    logger.info("Unreal Editor MCP server starting up")
    try:
        yield {}
    finally:
        reset_unreal_connection()
        logger.info("Unreal Editor MCP server shut down")


mcp = FastMCP("UnrealEditorMCP", lifespan=server_lifespan)


for tool in [
    get_assets,
    get_asset_properties,
    create_asset,
    set_asset_properties,
    delete_asset,
    batch_create_assets,
    batch_set_assets_properties,
    get_current_level,
    create_level,
    load_level,
    save_current_level,
    get_viewport_camera,
    set_viewport_camera,
    get_viewport_screenshot,
    get_actors,
    get_actor_properties,
    spawn_actor,
    set_actor_properties,
    delete_actor,
    batch_spawn_actors,
    batch_delete_actors,
    batch_set_actors_properties,
    import_texture,
    import_fbx,
    build_material_graph,
    get_material_graph,
    get_niagara_graph,
    update_niagara_graph,
    get_niagara_emitter,
    update_niagara_emitter,
    get_niagara_compiled_code,
    get_niagara_particle_attributes,
    get_blueprint_info,
    update_blueprint,
    read_blueprint_content,
    analyze_blueprint_graph,
    blueprint_graph_command,
    get_token_usage_summary,
    read_result_handle,
    release_result_handle,
]:
    mcp.tool()(tool)


if __name__ == "__main__":
    mcp.run()
