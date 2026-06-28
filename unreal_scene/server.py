"""Domain-scoped FastMCP entry point for scene tools."""

from __future__ import annotations

from unreal_harness_runtime.editor_guard import make_guarded_tool

from .tools import (
    apply_scene_actor_batch,
    aim_actor_at,
    create_spot_light_ring,
    delete_scene_actors_batch,
    find_actors_by_class_or_asset,
    get_actor_components,
    get_component_materials,
    get_scene_backend_status,
    get_scene_harness_info,
    query_scene_actors,
    query_scene_lights,
    set_actor_component_material,
    set_post_process_overrides,
    set_scene_light_intensity,
    spawn_actor_with_defaults,
)

TOOLS = [
    get_scene_harness_info,
    get_scene_backend_status,
    make_guarded_tool("scene.apply_scene_actor_batch", apply_scene_actor_batch),
    make_guarded_tool("scene.delete_scene_actors_batch", delete_scene_actors_batch),
    make_guarded_tool("scene.query_scene_actors", query_scene_actors),
    make_guarded_tool("scene.find_actors_by_class_or_asset", find_actors_by_class_or_asset),
    make_guarded_tool("scene.get_actor_components", get_actor_components),
    make_guarded_tool("scene.get_component_materials", get_component_materials),
    make_guarded_tool("scene.query_scene_lights", query_scene_lights),
    make_guarded_tool("scene.set_scene_light_intensity", set_scene_light_intensity),
    make_guarded_tool("scene.set_actor_component_material", set_actor_component_material),
    make_guarded_tool("scene.create_spot_light_ring", create_spot_light_ring),
    make_guarded_tool("scene.aim_actor_at", aim_actor_at),
    make_guarded_tool("scene.set_post_process_overrides", set_post_process_overrides),
    make_guarded_tool("scene.spawn_actor_with_defaults", spawn_actor_with_defaults),
]

if __name__ == "__main__":
    from contextlib import asynccontextmanager
    from typing import Any, AsyncIterator, Dict
    from fastmcp import FastMCP

    @asynccontextmanager
    async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
        yield {}

    mcp = FastMCP("UnrealSceneHarness", lifespan=server_lifespan)
    for tool in TOOLS:
        mcp.tool()(tool)
    mcp.run()
